"""Lab Q1 #1 AC CLEAN rerun (threshold=5) — 5-batch aggregation + 4-gate verdict."""
import sys
import statistics
import json

sys.path.insert(0, "/root/.openclaw/lab-q1-1-AC-clean-7f62f006/memoria-nox-fresh")
from eval.lib.aggregate_5batch import aggregate_5batch, gate_5batch


PER_BATCH = {
    "004": {"overall": 50.64, "F_SH": 85.71, "F_MH": 10.00, "F_TP": 10.00, "F_HL": 21.79,
            "MA_C": 78.00, "MA_P": 63.00, "MA_U": 58.62,
            "P_Skill": 53.33, "P_Style": 40.54, "P_Title": 67.35},
    "005": {"overall": 53.44, "F_SH": 78.00, "F_MH":  2.00, "F_TP": 20.00, "F_HL": 21.33,
            "MA_C": 87.00, "MA_P": 68.00, "MA_U": 83.64,
            "P_Skill": 44.19, "P_Style": 42.86, "P_Title": 53.06},
    "010": {"overall": 50.88, "F_SH": 76.00, "F_MH":  6.00, "F_TP": 10.00, "F_HL": 25.64,
            "MA_C": 79.00, "MA_P": 66.00, "MA_U": 58.62,
            "P_Skill": 54.35, "P_Style": 54.84, "P_Title": 58.00},
    "011": {"overall": 51.50, "F_SH": 90.00, "F_MH":  2.00, "F_TP": 11.67, "F_HL": 17.95,
            "MA_C": 79.00, "MA_P": 73.00, "MA_U": 68.52,
            "P_Skill": 53.49, "P_Style": 37.50, "P_Title": 58.00},
    "016": {"overall": 49.60, "F_SH": 75.00, "F_MH":  6.12, "F_TP": 16.67, "F_HL": 25.32,
            "MA_C": 81.00, "MA_P": 63.00, "MA_U": 69.35,
            "P_Skill": 40.91, "P_Style": 40.54, "P_Title": 46.00},
}

ACTIVATION = {"004": 43.9, "005": 48.2, "010": 44.8, "011": 43.0, "016": 41.3}

# Baselines (Phase H v2 5-batch; MA values from contaminated phaseAC report MA_C 84.60 / MA_P 65.40 / MA_U 70.03)
BASELINES_PHASEHV2 = {
    "overall": 51.68, "F_SH": 80.97, "F_MH":  3.21, "F_TP": 15.00, "F_HL": 22.68,
    "MA_C": 84.60, "MA_P": 65.40, "MA_U": 70.03,
    "P_Skill": 49.77, "P_Style": 39.78, "P_Title": 56.05,
}
BASELINES_PHASEG_5BATCH = {"overall": 61.26, "F_MH": 6.83}  # Phase G always-rerank
BASELINES_PHASEAC_CONTAMINATED = {"overall": 41.93, "F_MH": 3.62}  # threshold=4 contaminated
BASELINES_MEMOS_GPT41MINI = {"overall": 42.55, "F_MH": 18.88}


agg = aggregate_5batch(PER_BATCH)
gates = gate_5batch(agg, BASELINES_PHASEHV2)

act_mean = statistics.mean(ACTIVATION.values())
act_stdev = statistics.stdev(ACTIVATION.values())

ma_mean = (agg["MA_C"]["mean"] + agg["MA_P"]["mean"] + agg["MA_U"]["mean"]) / 3
ma_baseline = (BASELINES_PHASEHV2["MA_C"] + BASELINES_PHASEHV2["MA_P"] + BASELINES_PHASEHV2["MA_U"]) / 3

print("=== 5-BATCH AGGREGATE (CLEAN, threshold=5) ===")
ovr = agg["overall"]
print(f"Overall: mean={ovr['mean']:.2f}%, stdev={ovr['stdev']:.2f}pp, "
      f"95% CI [{ovr['ci_lower_95']:.2f}-{ovr['ci_upper_95']:.2f}]")
fmh = agg["F_MH"]
print(f"F_MH:    mean={fmh['mean']:.2f}%, stdev={fmh['stdev']:.2f}pp, "
      f"95% CI [{fmh['ci_lower_95']:.2f}-{fmh['ci_upper_95']:.2f}]")
print(f"MA_C: mean={agg['MA_C']['mean']:.2f}, stdev={agg['MA_C']['stdev']:.2f}")
print(f"MA_P: mean={agg['MA_P']['mean']:.2f}, stdev={agg['MA_P']['stdev']:.2f}")
print(f"MA_U: mean={agg['MA_U']['mean']:.2f}, stdev={agg['MA_U']['stdev']:.2f}")
print(f"MA_C/P/U mean: {ma_mean:.2f}% (baseline {ma_baseline:.2f}%)")
print(f"Activation: mean={act_mean:.1f}%, stdev={act_stdev:.1f}pp")
print()

print("=== 4-GATE VERDICT (vs Phase H v2 5-batch baselines) ===")
g_a = gates["overall"]
print(f"Gate A (Overall >= Phase H v2 51.68%): {g_a['verdict']}")
print(f"  mean={g_a['mean']:.2f} delta={g_a['mean_delta']:+.2f}pp, CI lower {g_a['ci_lower_95']:.2f}")

g_b = gates["F_MH"]
print(f"Gate B (F_MH >= Phase H v2 3.21%): {g_b['verdict']}")
print(f"  mean={g_b['mean']:.2f} delta={g_b['mean_delta']:+.2f}pp, CI lower {g_b['ci_lower_95']:.2f}")

g_c_pass = ma_mean >= (ma_baseline - 0.5)
g_c_delta = ma_mean - ma_baseline
verdict_c = "PASS" if g_c_pass else "FAIL"
print(f"Gate C (MA_C/P/U mean within 0.5pp of {ma_baseline:.2f}%): {verdict_c}")
print(f"  mean={ma_mean:.2f}, delta={g_c_delta:+.2f}pp (threshold lower {ma_baseline - 0.5:.2f})")

g_d_pass = 30.0 <= act_mean <= 60.0
verdict_d = "PASS" if g_d_pass else "FAIL"
print(f"Gate D (Activation in 30-60%): {verdict_d}")
print(f"  mean={act_mean:.1f}%, distribution {sorted(ACTIVATION.values())}")

n_pass = sum([
    g_a["verdict"] == "SHIP",
    g_b["verdict"] == "SHIP",
    g_c_pass,
    g_d_pass,
])
print()
print(f"VERDICT: {n_pass}/4 gates passed")
print()

print("=== COMPARISON vs OTHER BASELINES ===")
print(f"vs Phase H v2 (no classifier rerank OFF):       overall {ovr['mean']:.2f}% vs 51.68% = {ovr['mean']-51.68:+.2f}pp")
print(f"vs Phase G (always rerank Gemini):              overall {ovr['mean']:.2f}% vs 61.26% = {ovr['mean']-61.26:+.2f}pp")
print(f"vs Phase AC v1 contaminated (threshold=4):      overall {ovr['mean']:.2f}% vs 41.93% = {ovr['mean']-41.93:+.2f}pp")
print(f"vs MemOS GPT-4.1-mini Table 4:                  overall {ovr['mean']:.2f}% vs 42.55% = {ovr['mean']-42.55:+.2f}pp")
print()
print(f"F_MH vs Phase H v2:        {fmh['mean']:.2f} vs 3.21 = {fmh['mean']-3.21:+.2f}pp")
print(f"F_MH vs Phase G Gemini:    {fmh['mean']:.2f} vs 6.83 = {fmh['mean']-6.83:+.2f}pp")
print(f"F_MH vs Phase AC v1:       {fmh['mean']:.2f} vs 3.62 = {fmh['mean']-3.62:+.2f}pp")
