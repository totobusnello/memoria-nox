
## Aggregate (n=100)

| Config | nDCG@10 | MRR | R@10 | P@5 | Δ%nDCG vs A8' | Δ%MRR vs A8' | Δ%R@10 vs A8' |
|---|---:|---:|---:|---:|---:|---:|---:|
| A8' (G10 baseline) | 0.5502 | 0.5992 | 0.6183 | 0.1780 | +0.00% | +0.00% | +0.00% |
| A8d-1 (threshold=1) | 0.5467 | 0.5856 | 0.6333 | 0.1820 | -0.64% | -2.27% | +2.43% |
| A8d-2 (threshold=2) | 0.5577 | 0.6074 | 0.6233 | 0.1840 | +1.35% | +1.37% | +0.81% |
| A8' off (control) | 0.5438 | 0.5806 | 0.6333 | 0.1820 | -1.17% | -3.10% | +2.43% |

## Per-Category nDCG@10

| Category | A8' | A8d-1 | A8d-2 | A8 off | Δ%(d1−A8') | Δ%(d2−A8') | Δ%(off−A8') |
|---|---:|---:|---:|---:|---:|---:|---:|
| single-hop | 0.5655 | 0.5509 | 0.5470 | 0.5562 | -2.58% | -3.26% | -1.63% |
| multi-hop | 0.6786 | 0.6894 | 0.6894 | 0.6760 | +1.58% | +1.58% | -0.39% |
| temporal | 0.0000 | 0.0000 | 0.0000 | 0.0000 | +0.00% | +0.00% | +0.00% |
| open-domain | 0.7633 | 0.7487 | 0.7856 | 0.7422 | -1.91% | +2.92% | -2.77% |
| adversarial | 0.7438 | 0.7446 | 0.7664 | 0.7446 | +0.11% | +3.04% | +0.11% |

## Per-Category MRR

| Category | A8' | A8d-1 | A8d-2 | A8 off | Δ%(d1−A8') | Δ%(d2−A8') | Δ%(off−A8') |
|---|---:|---:|---:|---:|---:|---:|---:|
| single-hop | 0.4833 | 0.4479 | 0.4619 | 0.4562 | -7.33% | -4.43% | -5.60% |
| multi-hop | 0.9250 | 0.9250 | 0.9250 | 0.9000 | +0.00% | +0.00% | -2.70% |
| temporal | 0.0000 | 0.0000 | 0.0000 | 0.0000 | +0.00% | +0.00% | +0.00% |
| open-domain | 0.7875 | 0.7500 | 0.8000 | 0.7417 | -4.76% | +1.59% | -5.82% |
| adversarial | 0.8000 | 0.8050 | 0.8500 | 0.8050 | +0.63% | +6.25% | +0.63% |

## Per-Category R@10

| Category | A8' | A8d-1 | A8d-2 | A8 off | Δ%(d1−A8') | Δ%(d2−A8') | Δ%(off−A8') |
|---|---:|---:|---:|---:|---:|---:|---:|
| single-hop | 0.8000 | 0.8500 | 0.8000 | 0.8500 | +6.25% | +0.00% | +6.25% |
| multi-hop | 0.6667 | 0.6917 | 0.6917 | 0.6917 | +3.75% | +3.75% | +3.75% |
| temporal | 0.0000 | 0.0000 | 0.0000 | 0.0000 | +0.00% | +0.00% | +0.00% |
| open-domain | 0.8500 | 0.8500 | 0.8500 | 0.8500 | +0.00% | +0.00% | +0.00% |
| adversarial | 0.7750 | 0.7750 | 0.7750 | 0.7750 | +0.00% | +0.00% | +0.00% |

## Per-Style nDCG@10

| Style | A8' | A8d-1 | A8d-2 | A8 off | Δ%(d1−A8') | Δ%(d2−A8') | Δ%(off−A8') |
|---|---:|---:|---:|---:|---:|---:|---:|
| natural-language | 0.5561 | 0.5591 | 0.5575 | 0.5612 | +0.53% | +0.25% | +0.91% |
| keyword | 0.5444 | 0.5344 | 0.5578 | 0.5264 | -1.84% | +2.48% | -3.30% |

## Style × Category nDCG@10 (Δ% vs A8')

| Style | Category | n | A8' | A8d-1 | A8d-2 | A8 off | Δ%(d1) | Δ%(d2) | Δ%(off) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| natural-language | single-hop | 10 | 0.7024 | 0.6732 | 0.6655 | 0.6839 | -4.15% | -5.25% | -2.63% |
| natural-language | multi-hop | 10 | 0.6842 | 0.7120 | 0.7120 | 0.7120 | +4.07% | +4.07% | +4.07% |
| natural-language | temporal | 10 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | +0.00% | +0.00% | +0.00% |
| natural-language | open-domain | 10 | 0.7066 | 0.7226 | 0.7226 | 0.7226 | +2.27% | +2.27% | +2.27% |
| natural-language | adversarial | 10 | 0.6875 | 0.6875 | 0.6875 | 0.6875 | +0.00% | +0.00% | +0.00% |
| keyword | single-hop | 10 | 0.4286 | 0.4286 | 0.4286 | 0.4286 | +0.00% | +0.00% | +0.00% |
| keyword | multi-hop | 10 | 0.6731 | 0.6667 | 0.6667 | 0.6400 | -0.94% | -0.94% | -4.91% |
| keyword | temporal | 10 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | +0.00% | +0.00% | +0.00% |
| keyword | open-domain | 10 | 0.8201 | 0.7748 | 0.8486 | 0.7617 | -5.52% | +3.48% | -7.12% |
| keyword | adversarial | 10 | 0.8000 | 0.8017 | 0.8453 | 0.8017 | +0.21% | +5.66% | +0.21% |

## Latency (mean / p95)

| Config | Mean (ms) | P95 (ms) |
|---|---:|---:|
| A8' (G10 baseline) | 1603 | 2573 |
| A8d-1 (threshold=1) | 1629 | 2570 |
| A8d-2 (threshold=2) | 1558 | 2558 |
| A8' off (control) | 1533 | 2559 |

## D51 GO/NO-GO threshold check (best conditional config vs A8' baseline)

Note: Δ%s below are relative to A8' (G10 baseline) **in this run**.
Earlier G10b/G10c gave us absolute % deltas vs pre-mutex; those
provide the original numbers (e.g., single-hop +8.22% etc).

| Metric | A8' (baseline) | A8d-1 | Δ% | A8d-2 | Δ% | GO threshold | A8d-1 verdict | A8d-2 verdict |
|---|---:|---:|---:|---:|---:|---|---|---|
| Aggregate nDCG@10 | 0.5502 | 0.5467 | -0.64% | 0.5577 | +1.35% | ≥ baseline | MARGINAL | PASS |
| Aggregate MRR | 0.5992 | 0.5856 | -2.27% | 0.6074 | +1.37% | ≥ baseline | FAIL | PASS |
| Single-hop nDCG@10 | 0.5655 | 0.5509 | -2.58% | 0.5470 | -3.26% | ≥ baseline (preserve) | FAIL | FAIL |
| Single-hop MRR | 0.4833 | 0.4479 | -7.33% | 0.4619 | -4.43% | ≥ baseline (preserve) | FAIL | FAIL |
| Multi-hop nDCG@10 | 0.6786 | 0.6894 | +1.58% | 0.6894 | +1.58% | ≥ +2% (recover regression) | PASS | PASS |
| Multi-hop R@10 | 0.6667 | 0.6917 | +3.75% | 0.6917 | +3.75% | ≥ +3% (recover regression) | PASS | PASS |
| Open-domain nDCG@10 | 0.7633 | 0.7487 | -1.91% | 0.7856 | +2.92% | ≥ baseline | FAIL | PASS |
| Adversarial nDCG@10 | 0.7438 | 0.7446 | +0.11% | 0.7664 | +3.04% | bonus if ≥ baseline | PASS | PASS |
