# Benchmark History — Timeseries

_Updated: 2026-05-22 | Rolling 30-day window_

| Date | Overall | Pass | Fail | A2.encryption_overhead.kdf_ms | A2.export.encrypted.500chunks_3072d.archive_mb | A2.export.encrypted.500chunks_3072d.duration_ms | A2.export.plain.500chunks_3072d.archive_mb | A2.export.plain.500chunks_3072d.compression_ratio_pct | A2.export.plain.500chunks_3072d.duration_ms | A2.import.encrypted.500chunks_3072d.duration_ms | A2.import.plain.500chunks_3072d.duration_ms | A3.provider_overhead.embed.p95_abs_ms | A3.provider_overhead.llm.p95_abs_ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-05-19 | FAIL | 3 | 8 | 289 | 6.3035430908203125 | 460 | 5.357944488525391 | 88.51062623079953 | 182 | 1819 | 47 | -0.12024500000000415 | 0.006441999999999837 |
| 2026-05-20 | FAIL | 3 | 8 | 295 | 6.303556442260742 | 468 | 5.357964515686035 | 88.51095706971248 | 188 | 1831 | 39 | -0.055241999999992686 | 0.00425700000000262 |
| 2026-05-21 | FAIL | 3 | 8 | 291 | 6.303554534912109 | 462 | 5.357965469360352 | 88.51097282394643 | 178 | 1814 | 37 | -0.12925099999999645 | 0.00660299999999836 |
| 2026-05-22 | FAIL | 3 | 8 | 304 | 6.303540229797363 | 475 | 5.357962608337402 | 88.51092556124458 | 178 | 1816 | 37 | -0.13324099999999817 | 0.005579999999994811 |

> Full metric details in per-day `.json` files. Chart data in `timeseries.json`.