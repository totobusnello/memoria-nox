# Reviews of B-v2-rc16 … rc21 (2026-10-05/06): verdict record

Receipts are versioned (host and home path redacted) in `_sprint-2026-10-04/receipts/`. Fable ran as the
`critic` agent on model fable (no receipt file exists for those runs). Findings as transcribed into each
`APPLY-B-rcN.md`, where each was verified before it was applied.

| text | voice | receipt | verdict | findings (applied in) |
|---|---|---|---|---|
| rc16 | Fable | (agent) | GO | 3 LOW (rc17) |
| rc16 | Codex | `adversary-receipt-codex-2026-10-05T221948-70096.txt` | NO-GO | M1: fixed 19-item designation adopted after v1.12, not deposited; 2 LOW (rc17) |
| rc17 | Fable | (agent) | NO-GO | M-1 changelog said title unchanged; M-2 §8.3 framing; M-3 deposited DECISION file; 4 LOW (rc18) |
| rc18 | Fable | (agent) | GO | 6 LOW (rc19) |
| rc19 | Codex | `adversary-receipt-codex-2026-10-06T095645-63516.txt` | NO-GO | MEDIUM: trial ended before the deposited horizon, expiry not a deposited stopping condition; 2 LOW (rc20) |
| rc20 | Fable | (agent) | NO-GO | M-1 §3.0.1 "left the design decision open"; M-2 Abstract "Three commitments"; 6 LOW (rc21) |
| rc21 | Codex | `adversary-receipt-codex-2026-10-06T133927-60502.txt` | **GO** | no MEDIUM/HIGH; 3 LOW (rc22) |

Codex rc21 (final read), verbatim summary: rc19 findings resolved; closure chronology correct (decision
2026-09-09 §10.14/§10.22, spec 2026-09-10, expiry 2026-09-20 22:51:23Z, switch-off 2026-09-21 09:43:05Z;
PREREG l.795–801 horizon 234 epochs or amended 323-day cap, neither reached; expiry not a deposited stopping
condition); H1-family, H2, multiplicity and expiry-cut figures agree with `ITT-REGISTRADO-v4-2026-10-05.json`;
provenance hashes match; rc21 parity passes. LOW: unknown share 1.02% → 1.00% (v4 0.009998); working-list item 4
dates; Appendix A to name §10.14 and §10.22. GO.

rc22 applies those three LOWs and is the text frozen until the whole-window sham is integrated.
