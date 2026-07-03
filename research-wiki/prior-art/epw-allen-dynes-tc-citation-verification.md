# Prior Art / Citation Verification: EPW backend — Allen-Dynes Tc formula, moment definitions, EPW code + .a2f format

Scope: verify every numeric constant and functional form drafted for
`src/orme_lab/epw/allen_dynes.py` and `spectral.py` against primary sources
(Allen & Dynes 1975; McMillan 1968), confirm the EPW code reference
(Poncé, Margine, Verdi & Giustino 2016), and confirm the real EPW `.a2f`
output format. Task type: citation-auditor / constant-verification, filed
under prior-art per repo convention (research-wiki/prior-art/).

## Searched
- 2026-07-03 | WebSearch | "Allen Dynes 1975 Physical Review B 12 905 transition temperature strong-coupled superconductors" | confirmed bibliographic record (APS DOI page, OSTI.GOV, SciRP reference index)
- 2026-07-03 | WebSearch | "McMillan 1968 Physical Review 167 331 transition temperature strong-coupled superconductors" | confirmed bibliographic record (APS DOI page, OSTI.GOV)
- 2026-07-03 | WebSearch | "Poncé Margine Verdi Giustino EPW Computer Physics Communications 2016 electron-phonon Wannier" | confirmed CPC 209, 116 (2016), DOI 10.1016/j.cpc.2016.07.028, arXiv:1604.03525 (ADS record cross-checked)
- 2026-07-03 | WebFetch | OSTI.GOV Allen-Dynes biblio page | bibliographic metadata only, no free full text (paywalled at APS)
- 2026-07-03 | WebFetch | arXiv:2106.09879 (PDF), arXiv:1603.06965 (Giustino RMP review, ar5iv) | fetch tools could not extract equations from binary/long-doc PDFs; used as secondary corroboration attempts, inconclusive
- 2026-07-03 | WebFetch | ar5iv.labs.arxiv.org/html/1905.06780 | **quoted verbatim**: "Tc = f1f2 ωlog/1.20 exp[-1.04(1+λ)/(λ - μ*(1+0.62λ))]", cited to Allen & Dynes 1975 PRB 12, 905
- 2026-07-03 | WebSearch | Λ1/Λ2 constants "2.46" "3.8" "1.82" "6.3" | confirmed Λ1=2.46(1+3.8μ*), Λ2=1.82(1+6.3μ*), f1=[1+(λ/Λ1)^1.5]^(1/3), f2=1+(ω̄2/ωlog−1)λ²/(λ²+Λ2²)
- 2026-07-03 | WebSearch | ω_log integral definition | confirmed ω_log = exp[(2/λ)∫α²F(ω)ln(ω)/ω dω]
- 2026-07-03 | WebSearch | ω̄2 / second moment integral definition | confirmed ω̄2² = (2/λ)∫ω α²F(ω) dω
- 2026-07-03 | WebSearch | λ integral definition | confirmed λ = 2∫α²F(ω)/ω dω (EPW theory docs + independent review corroboration)
- 2026-07-03 | WebSearch | BCS gap ratio 1.764 | confirmed Δ(0)/kBTc ≈ 1.76 (BCS 1957 weak-coupling result), consistent with drafted 1.764
- 2026-07-03 | WebFetch | docs.epw-code.org tutorial_04 (Superconducting properties) | quoted verbatim EPW-reference-code output for fcc Pb (coarse 8×8×8/6×6×6 grid): λ=1.1583616, ω_log=4.3952 meV, μ*=0.1000, Tc(McMillan)=4.3678 K, Tc(Allen-Dynes)=4.7481 K
- 2026-07-03 | WebFetch | forum.epw-code.org t=459, t=1164 | confirmed real `.a2f` file column structure: 11 columns (1 frequency + 10 α²F(ω) values swept over degaussq smearing 0.05→0.50 meV in 0.05 meV steps); distinguished from the 3-column summary (ω, α²F(ω), cumulative λ(ω)) printed in `PREFIX.a2f`/tutorial output
- 2026-07-03 | WebFetch | arXiv:1211.3345 (Margine & Giustino, PRB 87, 024505, 2013), via ar5iv | Pb full-anisotropic-Eliashberg benchmark: λ=1.24, μ*=0.10, Tc(calc)=6.8 K vs Tc(exp)=7.2 K — NOT a clean Allen-Dynes-formula oracle (full anisotropic solve, not the algebraic Tc formula), noted but not used as the oracle

## Found

### DIRECT_PRECEDENT (source of the formula/constants — expected, this is a verification task not a novelty claim)
- Allen, P. B. & Dynes, R. C., "Transition Temperature of Strongly-Coupled Superconductors Reanalyzed," Phys. Rev. B 12, 905–922 (1975), DOI 10.1103/PhysRevB.12.905 — source of the modified McMillan Tc formula, f1/f2 correction factors, Λ1/Λ2, and the ω_log/ω̄2 moment definitions. | https://link.aps.org/doi/10.1103/PhysRevB.12.905
- McMillan, W. L., "Transition Temperature of Strong-Coupled Superconductors," Phys. Rev. 167, 331–344 (1968), DOI 10.1103/PhysRev.167.331 — source of the original (unmodified) McMillan formula that Allen-Dynes reanalyzed/extended. | https://link.aps.org/doi/10.1103/PhysRev.167.331
- Poncé, S., Margine, E. R., Verdi, C. & Giustino, F., "EPW: Electron-phonon coupling, transport and superconducting properties using maximally localized Wannier functions," Comput. Phys. Commun. 209, 116–133 (2016), DOI 10.1016/j.cpc.2016.07.028, arXiv:1604.03525 — the code being wrapped by the backend; confirms code identity and output conventions. | https://ui.adsabs.harvard.edu/abs/2016CoPhC.209..116P/abstract

### STRUCTURAL_PRECEDENT
- Margine, E. R. & Giustino, F., "Anisotropic Migdal-Eliashberg theory using Wannier functions," Phys. Rev. B 87, 024505 (2013), arXiv:1211.3345 — full anisotropic Eliashberg solve for Pb (λ=1.24, μ*=0.10, Tc=6.8 K vs exp 7.2 K). Structurally related (same code lineage, same material) but computes Tc via full numerical Eliashberg solution, not the closed-form Allen-Dynes algebraic formula — not usable as a formula-level oracle without re-deriving ω_log from their α²F(ω), which was not tabulated in the excerpt reached. | https://arxiv.org/abs/1211.3345
- EPW official documentation, Tutorial 4 ("Superconducting properties"), fcc Pb example, coarse 8×8×8/6×6×6 grid | https://docs.epw-code.org/tutorials/tutorial_04/index.html — real output of the reference EPW implementation applying exactly the Allen-Dynes formula under verification; not a converged/experimental physics result (λ=1.158 here vs. the well-known converged/experimental Pb λ≈1.5) but is a legitimate algorithmic oracle: given the same (λ, ω_log, μ*) inputs, a correct implementation of the drafted formula must reproduce Tc=4.7481 K.

### ADJACENT
- EPW forum threads on `.a2f` column structure and the two code paths (`eliashberg=.true.` vs `a2f=.true.`) that produce `PREFIX.a2f` vs `PREFIX.a2f.01` — operationally relevant to `parse.py` but not a constant/formula source. | https://forum.epw-code.org/viewtopic.php?t=459 , https://forum.epw-code.org/viewtopic.php?t=1164

## Negative result
- 2026-07-03 | Could not obtain full free-text/PDF access to Allen & Dynes 1975 (Phys. Rev. B 12, 905) or McMillan 1968 (Phys. Rev. 167, 331) themselves — both are paywalled at APS and no free preprint exists (pre-arXiv era). All constant confirmations are therefore via secondary sources (arXiv papers and EPW documentation/forum that quote/cite the primary papers with equation-level fidelity, cross-checked across ≥2 independent sources per constant) rather than the primary PRB text directly. This is a residual gap: **not fully exhausted** in the strict sense of primary-source-in-hand: state explicitly this is INSUFFICIENT for a "verified against primary source" claim if the operator's bar requires the actual PRB pages. What would resolve it: institutional APS access or a library scan of PRB 12, 905 and Phys. Rev. 167, 331.
- 2026-07-03 | No single primary "table" source found (in the sources reached) that tabulates a classic (material, λ, ω_log, μ*, Tc) tuple computed specifically via the closed-form Allen-Dynes algebraic formula (as opposed to a full anisotropic/isotropic numerical Eliashberg solve) for a well-known experimentally-converged material (Pb, Nb, Nb3Sn, Hg). The Margine & Giustino 2013 Pb result found (λ=1.24, Tc=6.8K) is a full-Eliashberg-solve output, not an Allen-Dynes-formula output, and does not report ω_log. The only formula-level oracle located is the EPW tutorial 4 coarse-grid Pb example (see STRUCTURAL_PRECEDENT above), which is real code output but not an experimentally-converged literature benchmark.
