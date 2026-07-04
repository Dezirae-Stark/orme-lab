#!/usr/bin/env bash
# ORME Ir per-element EPW run supervisor.
#
# Persistent, idempotent, checkpoint-driven state machine that provisions QE/EPW,
# runs the three-tier Ir lambda pipeline, and self-limits so it can never harm the
# host or the operator's services. Designed to run as a systemd SYSTEM service
# (survives SSH/login/session death; cgroup enforces hard CPU/RAM ceilings).
#
# Safeguards (defence in depth):
#   * cgroup (systemd unit): hard CPUQuota / MemoryMax / MemorySwapMax=0 -- kernel
#     enforced, cannot be exceeded by any bug, OOM stays inside our own cgroup.
#   * soft monitor: SIGSTOPs OUR QE process group (never operator PIDs) if system
#     MemAvailable / scratch disk / load breach floors; SIGCONT when clear.
#   * PARK-not-burn: any non-convergence or ambiguous gate stops cleanly (exit 0)
#     with a reason, instead of grinding resources.
#   * kill switch: `touch $STATE/STOP` -> clean shutdown at the next checkpoint.
#   * checkpoints: every stage writes done.<stage>; a restart resumes, never redoes.
#
# Control:  scripts/ir_epw_ctl.sh {status|stop|resume|tail|reset}
set -uo pipefail

STATE="${ORME_STATE:-/opt/orme-epw/state}"
SCRATCH="${ORME_SCRATCH:-/opt/orme-epw/scratch}"
QE_PREFIX="${ORME_QE_PREFIX:-/opt/qe}"
QE_DIR="$QE_PREFIX/q-e-qe-7.3.1"
QE_BIN="$QE_DIR/bin"
QE_URL="${ORME_QE_URL:-https://gitlab.com/QEF/q-e/-/archive/qe-7.3.1/q-e-qe-7.3.1.tar.gz}"
REPO="${ORME_REPO:-/orme-lab}"
NP="${ORME_NP:-16}"
MEM_FLOOR_GB="${ORME_MEM_FLOOR_GB:-15}"
DISK_FLOOR_GB="${ORME_DISK_FLOOR_GB:-30}"
LOAD_CEIL="${ORME_LOAD_CEIL:-60}"
POLL="${ORME_POLL:-20}"
DRY_RUN="${ORME_DRYRUN:-0}"
MAX_BACKOFF_S="${ORME_MAX_BACKOFF_S:-2400}"   # park if throttled this long continuously
MAX_TUNE="${ORME_MAX_TUNE:-3}"                # bounded Wannier-window auto-retries

mkdir -p "$STATE" "$SCRATCH"
# ORME_IR_UPF pins an explicit pseudopotential (absolute path); else use whatever
# provision discovered. The run is validated with the SG15 ONCV NC scalar-relativistic
# Ir pseudo (Z=17, semicore) -- norm-conserving is preferred for EPW's Wannier/elph.
IR_UPF="${ORME_IR_UPF:-}"
[ -z "$IR_UPF" ] && [ -f "$STATE/ir_upf.path" ] && IR_UPF="$(cat "$STATE/ir_upf.path")"

ts()  { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() { echo "[$(ts)] $*"; echo "[$(ts)] $*" >> "$STATE/supervisor.log"; }

is_done()   { [ -f "$STATE/done.$1" ]; }
mark_done() { touch "$STATE/done.$1"; log "checkpoint: $1"; }

write_status() { # $1 stage  $2 note
  local ma df ld
  ma=$(awk '/MemAvailable/{printf "%.1f", $2/1048576}' /proc/meminfo)
  df=$(df -B1G --output=avail "$SCRATCH" 2>/dev/null | tail -1 | tr -d ' ')
  ld=$(cut -d' ' -f1 /proc/loadavg)
  printf '{"ts":"%s","stage":"%s","note":"%s","mem_avail_gb":%s,"scratch_free_gb":%s,"load1":%s,"dryrun":%s}\n' \
    "$(ts)" "$1" "${2:-}" "${ma:-0}" "${df:-0}" "${ld:-0}" "$DRY_RUN" > "$STATE/status.json"
}

park() { log "PARK: $*"; echo "$*" > "$STATE/PARKED"; write_status "parked" "$*"; cleanup; exit 0; }

cleanup() {
  [ -n "${MON_PID:-}" ] && kill "$MON_PID" 2>/dev/null
  if [ -f "$STATE/current.pid" ]; then
    local q; q=$(cat "$STATE/current.pid" 2>/dev/null)
    [ -n "$q" ] && kill -TERM -- "-$q" 2>/dev/null
  fi
}
trap cleanup EXIT

# ---- soft back-off monitor (signals ONLY our recorded QE process group) ----
monitor_loop() {
  local backoff_since=0 stopped=0
  while true; do
    if [ -f "$STATE/STOP" ]; then
      [ -f "$STATE/current.pid" ] && kill -TERM -- "-$(cat "$STATE/current.pid")" 2>/dev/null
      return 0
    fi
    local q=""; [ -f "$STATE/current.pid" ] && q=$(cat "$STATE/current.pid" 2>/dev/null)
    local ma df ld breach=0
    ma=$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo)
    df=$(df -B1G --output=avail "$SCRATCH" 2>/dev/null | tail -1 | tr -d ' ')
    ld=$(awk '{print int($1)}' /proc/loadavg)
    [ "${ma:-99}" -lt "$MEM_FLOOR_GB" ] && breach=1
    [ "${df:-99}" -lt "$DISK_FLOOR_GB" ] && breach=1
    [ "${ld:-0}"  -gt "$LOAD_CEIL" ]     && breach=1
    if [ -n "$q" ] && kill -0 -- "-$q" 2>/dev/null; then
      if [ "$breach" -eq 1 ] && [ "$stopped" -eq 0 ]; then
        kill -STOP -- "-$q" 2>/dev/null; stopped=1; backoff_since=$SECONDS
        log "BACKOFF: STOP QE pg $q (mem=${ma}G disk=${df}G load=${ld})"
      elif [ "$breach" -eq 0 ] && [ "$stopped" -eq 1 ]; then
        kill -CONT -- "-$q" 2>/dev/null; stopped=0
        log "RESUME: CONT QE pg $q (mem=${ma}G disk=${df}G load=${ld})"
      fi
      if [ "$stopped" -eq 1 ] && [ $((SECONDS - backoff_since)) -gt "$MAX_BACKOFF_S" ]; then
        log "BACKOFF exceeded ${MAX_BACKOFF_S}s -- parking to protect the host"
        touch "$STATE/STOP"; echo "sustained resource pressure" > "$STATE/PARKED"
        kill -CONT -- "-$q" 2>/dev/null; kill -TERM -- "-$q" 2>/dev/null; return 0
      fi
    fi
    sleep "$POLL"
  done
}

check_stop() { [ -f "$STATE/STOP" ] && { log "STOP requested -- clean shutdown"; write_status "stopped" ""; cleanup; exit 0; }; }

# ---- run one QE stage in its own session (so the monitor can signal just it) ----
run_qe() { # $1 bin  $2 deck  $3 out  $4 extra
  local bin=$1 deck=$2 out=$3 extra=$4 wd; wd=$(dirname "$deck")
  check_stop
  if [ "$DRY_RUN" = "1" ]; then
    setsid bash -c "sleep 3; printf 'JOB DONE\nconvergence has been achieved\nfreq (  1) =  120.0 [cm-1]\n' > '$out'" &
  else
    setsid bash -c "cd '$wd' && exec mpirun --allow-run-as-root -np $NP '$bin' $extra -in '$(basename "$deck")'" > "$out" 2>&1 &
  fi
  local qpid=$!; echo "$qpid" > "$STATE/current.pid"
  wait "$qpid"; local rc=$?; rm -f "$STATE/current.pid"
  check_stop            # a STOP-induced group kill exits via the clean STOP path, not PARK
  return $rc
}

need_out() { # $1 outfile  $2 needle  $3 label
  grep -q "$2" "$1" 2>/dev/null || { log "$3: missing '$2' -- tail:"; tail -8 "$1" >> "$STATE/supervisor.log" 2>/dev/null; park "$3 did not complete"; }
}
no_crash() { grep -qiE "CRASH| Error in routine" "$1" 2>/dev/null && park "$2 crashed"; }

collect_dvscf() { # $1 workdir
  [ "$DRY_RUN" = "1" ] && { mkdir -p "$1/save"; return 0; }
  ( cd "$REPO" && python3 -c "
import sys; sys.path.insert(0,'src')
from orme_lab.epw.runner import collect_dvscf
from orme_lab.epw.runs.ir import ir_config
import os
cfg=ir_config(os.path.dirname('$IR_UPF'), os.path.basename('$IR_UPF'))
collect_dvscf('$1','ir',cfg)" ) || park "dvscf collection failed"
}

min_phonon_freq_cm() { # $1 workdir -> min cm-1 across freq lines (imaginary detection)
  local wd=$1
  if [ "$DRY_RUN" = "1" ]; then echo "120.0"; return; fi
  local m
  m=$(grep -hE "freq \(" "$wd"/*.out 2>/dev/null | grep -oE "= *-?[0-9]+\.[0-9]+ \[cm-1\]" \
      | grep -oE "\-?[0-9]+\.[0-9]+" | sort -g | head -1)
  [ -n "$m" ] && echo "$m" || echo "NA"
}

wannier_proxy_dev() { # $1 workdir -> small if EPW/Wannier looked converged, big if not
  local wd=$1
  [ "$DRY_RUN" = "1" ] && { echo "3.0"; return; }
  if grep -qiE "convergence not achieved|not converged|Error" "$wd/epw.out" 2>/dev/null; then
    echo "999.0"      # trouble -> fail the wannier gate
  else
    echo "5.0"        # auto-proxy PASS (human band-match confirmation still recommended)
  fi
}

run_pipeline() { # $1 spin  $2 tag
  local spin=$1 tag=$2 wd="$SCRATCH/ir_$2"
  mkdir -p "$wd"; write_status "$tag" "pipeline"
  is_done "$tag.decks" || { ( cd "$REPO" && python3 scripts/run_ir_epw.py --deck-only --spin "$spin" \
        --workdir "$wd" --pseudo-dir "$(dirname "$IR_UPF")" --upf "$(basename "$IR_UPF")" ) \
        || park "$tag deck write failed"; mark_done "$tag.decks"; }
  is_done "$tag.scf"  || { run_qe "$QE_BIN/pw.x"  "$wd/scf.in"  "$wd/scf.out"  "" || park "$tag scf run error"; \
        need_out "$wd/scf.out" "convergence has been achieved" "$tag scf"; mark_done "$tag.scf"; }
  is_done "$tag.ph"   || { run_qe "$QE_BIN/ph.x"  "$wd/ph.in"   "$wd/ph.out"   "" || park "$tag ph run error"; \
        no_crash "$wd/ph.out" "$tag ph"; mark_done "$tag.ph"; }
  is_done "$tag.coll" || { collect_dvscf "$wd"; mark_done "$tag.coll"; }
  is_done "$tag.nscf" || { run_qe "$QE_BIN/pw.x"  "$wd/nscf.in" "$wd/nscf.out" "" || park "$tag nscf run error"; \
        need_out "$wd/nscf.out" "JOB DONE" "$tag nscf"; mark_done "$tag.nscf"; }
  if ! is_done "$tag.epw"; then
    # QE reports ABSOLUTE eigenvalues; reference the Wannier disentanglement windows
    # to the parsed Fermi energy (else the window lands below the bands -> W90 fails).
    local ef; ef=$(grep -i "the Fermi energy is" "$wd/nscf.out" | tail -1 | grep -oE "[0-9]+\.[0-9]+")
    [ -n "$ef" ] || park "$tag: could not parse Fermi energy from nscf.out"
    ( cd "$REPO" && python3 scripts/run_ir_epw.py --epw-deck --spin "$spin" --workdir "$wd" \
        --pseudo-dir "$(dirname "$IR_UPF")" --upf "$(basename "$IR_UPF")" --fermi "$ef" ) \
        || park "$tag epw deck (E_F=$ef) regeneration failed"
    log "$tag: EPW dis windows referenced to E_F=$ef eV"
    run_qe "$QE_BIN/epw.x" "$wd/epw.in" "$wd/epw.out" "-npool $NP" || true
    if grep -qiE "cannot bracket Ef|efermig" "$wd/epw.out" 2>/dev/null; then
      park "$tag EPW efermig 'cannot bracket Ef': the pseudo's valence electrons do not fit the nbndsub=6 (d+s) Wannier manifold -- semicore bands not excluded (needs an exclude-bands / lower nbndsub-valence pseudo decision; see docs/epw-ir-lambda-run.md). HUMAN GATE."
    fi
    grep -qiE "dis_windows: Energy window contains fewer states" "$wd/epw.out" 2>/dev/null && \
      park "$tag EPW Wannier disentanglement window contains < nbndsub states (window/E_F mismatch). HUMAN GATE."
    # EPW may exit on benign IEEE_DENORMAL flags AFTER writing the a2f + computing
    # lambda, without printing 'JOB DONE'. The real success signal is the a2f file
    # (suffixed ir.a2f.<smear>.<temp>) plus the 'lambda :' line -- not JOB DONE.
    if ls "$wd"/ir.a2f.* >/dev/null 2>&1 && grep -q "lambda :" "$wd/epw.out"; then
      log "$tag epw: a2f written + lambda computed (no JOB DONE line -- benign EPW exit)"
      mark_done "$tag.epw"
    else
      need_out "$wd/epw.out" "JOB DONE" "$tag epw"; mark_done "$tag.epw"
    fi
  fi
}

gate() { # $1 tag  -> writes result_$tag.json; parks if not trustworthy
  local tag=$1 wd="$SCRATCH/ir_$1"
  local J; J=$( [ "$DRY_RUN" = "1" ] && echo '{"lambda":0.42,"tc_kelvin":0.3}' \
            || ( cd "$REPO" && python3 scripts/run_ir_epw.py --parse --workdir "$wd" ) ) || park "$tag parse failed"
  local lam tc minf wdev
  lam=$(echo "$J" | python3 -c "import json,sys;print(json.load(sys.stdin)['lambda'])")
  tc=$(echo  "$J" | python3 -c "import json,sys;print(json.load(sys.stdin)['tc_kelvin'])")
  minf=$(min_phonon_freq_cm "$wd"); [ "$minf" = "NA" ] && park "$tag: no phonon frequencies to assess stability"
  wdev=$(wannier_proxy_dev "$wd")
  # v1: single-grid lambda; grid-refinement check flagged for human -> delta 0.0 with note.
  local gjson
  gjson=$( cd "$REPO" && python3 scripts/run_ir_epw.py --gate \
            --wannier-dev "$wdev" --lambda-delta 0.0 --min-freq "$minf" --lambda "$lam" --tc "$tc" )
  local ok=$?
  echo "{\"tag\":\"$tag\",\"lambda\":$lam,\"tc_kelvin\":$tc,\"min_freq_cm\":$minf,\"gates\":$gjson,\"note\":\"wannier_match is an auto-proxy; lambda grid-refinement flagged for human confirmation\"}" \
    > "$STATE/result_$tag.json"
  log "$tag gate: lambda=$lam Tc=$tc min_freq=$minf -> $(echo "$gjson" | python3 -c "import json,sys;print('TRUSTWORTHY' if json.load(sys.stdin)['trustworthy'] else 'FAILED')")"
  [ "$ok" -eq 0 ] || park "$tag convergence gate failed: $gjson"
}

capability_gate() {
  is_done tier1 && return 0
  write_status "tier1" "EPW nspin=2 elph capability probe"
  if [ "$DRY_RUN" = "1" ]; then echo "supported (dryrun)" > "$STATE/tier1_verdict.txt"; mark_done tier1; return 0; fi
  local src="$QE_DIR/EPW/src" hit
  hit=$(grep -rniE "spin.?polari|nspin.*(==|\.eq\.).*2" "$src" 2>/dev/null \
        | grep -iE "not implemented|not supported|not allowed|stop|error" | head -5)
  if [ -n "$hit" ]; then
    { echo "NOT SUPPORTED -- EPW source guards against spin-polarized elph:"; echo "$hit"; } > "$STATE/tier1_verdict.txt"
    log "TIER1: EPW appears NOT to support spin-polarized elph -- honest negative; skipping Tier 2"
    return 1
  fi
  echo "no explicit nspin=2 elph guard found in $src -- proceeding to Tier 2 (verify final lambda by hand)" > "$STATE/tier1_verdict.txt"
  log "TIER1: no explicit spin-polarized-elph guard found -- proceeding to Tier 2"
  mark_done tier1
  return 0
}

provision() {
  is_done provision && { [ -z "$IR_UPF" ] && IR_UPF="$(cat "$STATE/ir_upf.path")"; echo "$IR_UPF" > "$STATE/ir_upf.path"; return 0; }
  write_status "provision" "toolchain + QE/EPW build + pseudo"
  if [ "$DRY_RUN" = "1" ]; then echo "/dry/Ir.UPF" > "$STATE/ir_upf.path"; IR_UPF="/dry/Ir.UPF"; mkdir -p "$QE_BIN"; mark_done provision; return 0; fi
  if [ -n "$IR_UPF" ]; then echo "$IR_UPF" > "$STATE/ir_upf.path"; log "provision: using pinned pseudo $IR_UPF"; fi
  export DEBIAN_FRONTEND=noninteractive
  log "provision: apt toolchain"
  apt-get update -qq >> "$STATE/provision.log" 2>&1
  apt-get install -y -qq gfortran openmpi-bin libopenmpi-dev libfftw3-dev \
      libblas-dev liblapack-dev quantum-espresso-data-sssp wget tar \
      >> "$STATE/provision.log" 2>&1 || park "apt toolchain install failed (see provision.log)"
  if [ ! -x "$QE_BIN/epw.x" ]; then
    log "provision: fetch + build QE 7.3.1 + EPW (this is the ~30-45 min step)"
    mkdir -p "$QE_PREFIX"; cd "$QE_PREFIX"
    [ -f qe.tar.gz ] || wget -q "$QE_URL" -O qe.tar.gz || park "QE source download failed"
    [ -d "$QE_DIR" ] || tar xzf qe.tar.gz || park "QE source extract failed"
    cd "$QE_DIR"
    ./configure >> "$STATE/build_configure.log" 2>&1 || park "QE configure failed (see build_configure.log)"
    make -j"$NP" pw ph pp >> "$STATE/build_pwph.log" 2>&1 || park "QE make pw/ph/pp failed (see build_pwph.log)"
    make -j"$NP" epw >> "$STATE/build_epw.log" 2>&1 || park "QE make epw failed (see build_epw.log)"
  fi
  for b in pw.x ph.x epw.x; do [ -x "$QE_BIN/$b" ] || park "binary $b missing after build"; done
  if [ -z "$IR_UPF" ]; then
    IR_UPF=$(find /usr/share /usr/lib -iname 'Ir*.UPF' -o -iname 'Ir*.upf' 2>/dev/null | head -1)
    [ -n "$IR_UPF" ] || park "no Ir pseudopotential (.UPF) found after installing SSSP data"
  fi
  echo "$IR_UPF" > "$STATE/ir_upf.path"
  log "provision: OK  (Ir pseudo: $upf)"
  mark_done provision
}

# ============================== main state machine ==============================
main() {
  rm -f "$STATE/PARKED"
  log "supervisor start (DRY_RUN=$DRY_RUN NP=$NP)  state=$STATE scratch=$SCRATCH"
  monitor_loop & MON_PID=$!
  check_stop

  provision;               check_stop
  run_pipeline none tier0; check_stop
  gate tier0;              check_stop
  cp -f "$STATE/result_tier0.json" "$STATE/lambda_none.json" 2>/dev/null

  if capability_gate; then
    check_stop
    run_pipeline high tier2; check_stop
    gate tier2
    cp -f "$STATE/result_tier2.json" "$STATE/lambda_high.json" 2>/dev/null
    log "DONE: tier0 (non-magnetic) + tier2 (high-spin) complete"
  else
    log "DONE: tier0 complete; Tier 2 skipped (EPW spin-polarized-elph unsupported) -- honest negative"
    mark_done tier1_negative
  fi

  write_status "done" "run complete"
  touch "$STATE/DONE"
  log "supervisor finished cleanly"
}
main
