#!/usr/bin/env bash
# Control + observe the persistent Ir EPW run.
#   status  -- current stage, resources, checkpoints, any results / park reason
#   stop    -- graceful: kill switch + stop the service (checkpointed; resumable)
#   resume  -- clear the kill switch and restart from the last checkpoint
#   tail    -- follow the live journal
#   reset   -- wipe ALL state (only when stopped; asks nothing -- destructive)
set -uo pipefail
STATE="${ORME_STATE:-/opt/orme-epw/state}"
UNIT="orme-ir-epw.service"

case "${1:-status}" in
  status)
    echo "== service =="; systemctl is-active "$UNIT" 2>/dev/null; systemctl is-enabled "$UNIT" 2>/dev/null
    echo "== status.json =="; cat "$STATE/status.json" 2>/dev/null || echo "(none yet)"
    echo "== checkpoints =="; ls -1 "$STATE"/done.* 2>/dev/null | sed 's|.*/done\.|  |' || echo "  (none)"
    [ -f "$STATE/PARKED" ] && { echo "== PARKED =="; cat "$STATE/PARKED"; }
    [ -f "$STATE/DONE" ]   && echo "== DONE =="
    for r in "$STATE"/result_*.json; do [ -f "$r" ] && { echo "== $(basename "$r") =="; cat "$r"; echo; }; done
    [ -f "$STATE/tier1_verdict.txt" ] && { echo "== tier1 capability verdict =="; cat "$STATE/tier1_verdict.txt"; }
    ;;
  stop)    touch "$STATE/STOP"; systemctl stop "$UNIT" 2>/dev/null; echo "stop requested (state preserved; 'resume' to continue)";;
  resume)  rm -f "$STATE/STOP" "$STATE/PARKED"; systemctl start "$UNIT"; echo "resumed";;
  tail)    journalctl -u "$UNIT" -f -n 100;;
  reset)   systemctl stop "$UNIT" 2>/dev/null; rm -rf "$STATE"/done.* "$STATE"/*.json "$STATE"/STOP "$STATE"/PARKED "$STATE"/DONE "$STATE"/*.log; echo "state wiped";;
  *) echo "usage: $0 {status|stop|resume|tail|reset}"; exit 2;;
esac
