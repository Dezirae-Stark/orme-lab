// web/ledger.js — Hudson Claim Ledger dashboard (Phase A). Parity-locked to hudson_ledger.py.
export function renderLedger(el) {
  el.textContent = "";
  const p = document.createElement("p");
  p.className = "reg-sub";
  p.textContent = "Ledger dashboard loading…";
  el.appendChild(p);
}
