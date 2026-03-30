#!/usr/bin/env python3
"""
EVALUASI KOMPREHENSIF MODEL VISIBILITAS HILAL
Implementasi Prosedur Evaluasi v2 — Tahap 1–4 & 6
"""
s
import math
import numpy as np
import pandas as pd
from scipy import stats
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import os, warnings
warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════════
# LOAD DATA
# ═══════════════════════════════════════════════════════════════

INPUT = '/mnt/user-data/uploads/Validasi_Crumey_era5_optimal_NoBias.xlsx'
df = pd.read_excel(INPUT, sheet_name='Hasil Observasi')

# Standardize columns
df['obs_binary'] = (df['Obs Tel (Y/N)'] == 'Y').astype(int)
df['pred_binary'] = (df['Pred Tel'] == 'Y').astype(int)
df['dm_tel'] = df['Δm Tel Opt'].astype(float)
df['dm_ne'] = df['Δm NE Opt'].astype(float)
df['event'] = df['Tanggal'].astype(str)

F_REF = 1.5
N_TOTAL = len(df)
N_Y = df['obs_binary'].sum()
N_N = N_TOTAL - N_Y
EVENTS = df['event'].unique()

OUT_DIR = '/home/claude/output'
os.makedirs(OUT_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def confusion_metrics(obs, pred):
    tp = sum((o == 1 and p == 1) for o, p in zip(obs, pred))
    tn = sum((o == 0 and p == 0) for o, p in zip(obs, pred))
    fp = sum((o == 0 and p == 1) for o, p in zip(obs, pred))
    fn = sum((o == 1 and p == 0) for o, p in zip(obs, pred))
    n = tp + tn + fp + fn
    acc = (tp + tn) / n if n > 0 else 0
    sens = tp / (tp + fn) if (tp + fn) > 0 else 0
    spec = tn / (tn + fp) if (tn + fp) > 0 else 0
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0
    f1 = 2 * prec * sens / (prec + sens) if (prec + sens) > 0 else 0
    denom = math.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
    mcc = (tp*tn - fp*fn) / denom if denom > 0 else 0
    bal_acc = (sens + spec) / 2
    return {'TP': tp, 'TN': tn, 'FP': fp, 'FN': fn, 'n': n,
            'Accuracy': acc, 'Sensitivity': sens, 'Specificity': spec,
            'Precision': prec, 'F1': f1, 'MCC': mcc, 'Balanced_Acc': bal_acc}

def delta_m_at_F(dm_ref, F_ref, F):
    if dm_ref <= -90: return dm_ref
    if F <= 0: return dm_ref
    return dm_ref + 2.5 * math.log10(F_ref / F)

def compute_auc(labels, scores):
    """Manual ROC-AUC computation."""
    pairs = sorted(zip(scores, labels), reverse=True)
    tp, fp, tp_prev, fp_prev = 0, 0, 0, 0
    auc = 0.0
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0: return 0.5
    prev_score = None
    for score, label in pairs:
        if score != prev_score and prev_score is not None:
            auc += (fp - fp_prev) * (tp + tp_prev) / 2.0
            tp_prev, fp_prev = tp, fp
        if label == 1: tp += 1
        else: fp += 1
        prev_score = score
    auc += (fp - fp_prev) * (tp + tp_prev) / 2.0
    return auc / (n_pos * n_neg)

def compute_roc_curve(labels, scores):
    thresholds = sorted(set(scores), reverse=True)
    tpr_list, fpr_list = [0.0], [0.0]
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos
    for th in thresholds:
        pred = [1 if s >= th else 0 for s in scores]
        tp = sum(1 for o, p in zip(labels, pred) if o == 1 and p == 1)
        fp = sum(1 for o, p in zip(labels, pred) if o == 0 and p == 1)
        tpr_list.append(tp / n_pos if n_pos > 0 else 0)
        fpr_list.append(fp / n_neg if n_neg > 0 else 0)
    tpr_list.append(1.0); fpr_list.append(1.0)
    return fpr_list, tpr_list

def bootstrap_auc_ci(labels, scores, n_boot=2000, ci=0.95):
    rng = np.random.RandomState(42)
    aucs = []
    for _ in range(n_boot):
        idx = rng.choice(len(labels), len(labels), replace=True)
        if sum(labels[i] for i in idx) == 0 or sum(1 - labels[i] for i in idx) == 0:
            continue
        aucs.append(compute_auc([labels[i] for i in idx], [scores[i] for i in idx]))
    aucs = sorted(aucs)
    lo = aucs[int((1 - ci) / 2 * len(aucs))]
    hi = aucs[int((1 + ci) / 2 * len(aucs))]
    return lo, hi


# ═══════════════════════════════════════════════════════════════
# TAHAP 1: KARAKTERISASI DATASET
# ═══════════════════════════════════════════════════════════════

print("=" * 70)
print("TAHAP 1: KARAKTERISASI DATASET")
print("=" * 70)

# 1.1 Class distribution
print(f"\n1.1 Distribusi Kelas:")
print(f"  Total observasi : {N_TOTAL}")
print(f"  Terlihat (Y)    : {N_Y} ({N_Y/N_TOTAL*100:.1f}%)")
print(f"  Tidak (N)       : {N_N} ({N_N/N_TOTAL*100:.1f}%)")
print(f"  Imbalance ratio : {N_N/N_Y:.2f}")
print(f"  Baseline naive  : {N_N/N_TOTAL*100:.1f}%")

# 1.2 Block design verification
print(f"\n1.2 Verifikasi Block Design:")
t1_block = []
for ev in EVENTS:
    sub = df[df['event'] == ev]
    elong_range = sub['Elongasi (°)'].max() - sub['Elongasi (°)'].min()
    pa_range = sub['Phase Angle (°)'].max() - sub['Phase Angle (°)'].min()
    rh_range = sub['RH (%)'].max() - sub['RH (%)'].min()
    kv_range = sub['k_V'].max() - sub['k_V'].min()
    elong_cv = sub['Elongasi (°)'].std() / sub['Elongasi (°)'].mean() * 100
    rh_cv = sub['RH (%)'].std() / sub['RH (%)'].mean() * 100
    row = {'Event': ev, 'n': len(sub), 'Y': sub['obs_binary'].sum(),
           'Elong_range': elong_range, 'PA_range': pa_range,
           'Elong_CV%': elong_cv, 'RH_range': rh_range, 'RH_CV%': rh_cv,
           'kV_range': kv_range}
    t1_block.append(row)
    print(f"  {ev}: n={len(sub)}, Y={sub['obs_binary'].sum()}")
    print(f"    Geometri: Elong CV={elong_cv:.2f}%, range={elong_range:.4f}°")
    print(f"    Atmosfer: RH CV={rh_cv:.1f}%, range={rh_range:.1f}pp, k_V range={kv_range:.4f}")
df_block = pd.DataFrame(t1_block)

# 1.3 Seasonal coverage (RH/T per event)
print(f"\n1.3 Variasi Musiman:")
t1_season = []
for ev in EVENTS:
    sub = df[df['event'] == ev]
    t1_season.append({'Event': ev,
        'RH_mean': sub['RH (%)'].mean(), 'RH_std': sub['RH (%)'].std(),
        'T_mean': sub['T (°C)'].mean(), 'T_std': sub['T (°C)'].std(),
        'kV_mean': sub['k_V'].mean(), 'kV_std': sub['k_V'].std()})
    print(f"  {ev}: RH={sub['RH (%)'].mean():.1f}±{sub['RH (%)'].std():.1f}%, "
          f"T={sub['T (°C)'].mean():.1f}±{sub['T (°C)'].std():.1f}°C")
df_season = pd.DataFrame(t1_season)

# 1.4 Descriptive stats Δm
print(f"\n1.4 Statistik Deskriptif Δm Tel Opt:")
dm_Y = df[df['obs_binary'] == 1]['dm_tel'].values
dm_N = df[df['obs_binary'] == 0]['dm_tel'].values
print(f"  Kelompok Y: mean={dm_Y.mean():.3f}, std={dm_Y.std():.3f}, "
      f"min={dm_Y.min():.3f}, max={dm_Y.max():.3f}")
print(f"  Kelompok N: mean={dm_N.mean():.3f}, std={dm_N.std():.3f}, "
      f"min={dm_N.min():.3f}, max={dm_N.max():.3f}")

# Shapiro-Wilk
if len(dm_Y) >= 3:
    sw_Y = stats.shapiro(dm_Y)
    print(f"  Shapiro-Wilk (Y): W={sw_Y.statistic:.4f}, p={sw_Y.pvalue:.4f}")
sw_N = stats.shapiro(dm_N)
print(f"  Shapiro-Wilk (N): W={sw_N.statistic:.4f}, p={sw_N.pvalue:.4f}")


# ═══════════════════════════════════════════════════════════════
# TAHAP 2: EVALUASI PERFORMA KLASIFIKASI
# ═══════════════════════════════════════════════════════════════

print(f"\n{'=' * 70}")
print("TAHAP 2: EVALUASI PERFORMA KLASIFIKASI")
print("=" * 70)

# 2.1 Confusion matrix at F_ref
cm_base = confusion_metrics(df['obs_binary'].tolist(), df['pred_binary'].tolist())
print(f"\n2.1 Confusion Matrix (F={F_REF}):")
print(f"              Obs:Y  Obs:N  Total")
print(f"  Pred:Y      {cm_base['TP']:>5}  {cm_base['FP']:>5}  {cm_base['TP']+cm_base['FP']:>5}")
print(f"  Pred:N      {cm_base['FN']:>5}  {cm_base['TN']:>5}  {cm_base['FN']+cm_base['TN']:>5}")
print(f"  Total       {N_Y:>5}  {N_N:>5}  {N_TOTAL:>5}")
print(f"\n  Accuracy      : {cm_base['Accuracy']:.1%}")
print(f"  Sensitivity   : {cm_base['Sensitivity']:.1%}")
print(f"  Specificity   : {cm_base['Specificity']:.1%}")
print(f"  MCC           : {cm_base['MCC']:.4f}")
print(f"  Balanced Acc  : {cm_base['Balanced_Acc']:.1%}")
print(f"  Naive baseline: {N_N/N_TOTAL:.1%}")

# 2.2 Mann-Whitney U
print(f"\n2.2 Mann-Whitney U Test:")
u_stat, p_mw = stats.mannwhitneyu(dm_Y, dm_N, alternative='greater')
r_rb = 1 - 2 * u_stat / (len(dm_Y) * len(dm_N))
pooled_std = np.sqrt(((len(dm_Y)-1)*dm_Y.std(ddof=1)**2 + (len(dm_N)-1)*dm_N.std(ddof=1)**2) /
                     (len(dm_Y) + len(dm_N) - 2))
cohens_d = (dm_Y.mean() - dm_N.mean()) / pooled_std if pooled_std > 0 else 0
print(f"  U statistic     : {u_stat:.1f}")
print(f"  p-value (1-tail): {p_mw:.6f}")
print(f"  Signifikan (α=0.05): {'YA' if p_mw < 0.05 else 'TIDAK'}")
print(f"  Rank-biserial r : {r_rb:.4f} ({'besar' if abs(r_rb) > 0.5 else 'sedang' if abs(r_rb) > 0.3 else 'kecil'})")
print(f"  Cohen's d       : {cohens_d:.3f} ({'besar' if abs(cohens_d) > 0.8 else 'sedang' if abs(cohens_d) > 0.5 else 'kecil'})")

# 2.3 ROC-AUC
print(f"\n2.3 ROC Curve & AUC:")
labels_list = df['obs_binary'].tolist()
scores_list = df['dm_tel'].tolist()
auc_val = compute_auc(labels_list, scores_list)
auc_lo, auc_hi = bootstrap_auc_ci(labels_list, scores_list)
print(f"  AUC             : {auc_val:.4f}")
print(f"  95% CI (boot)   : [{auc_lo:.4f}, {auc_hi:.4f}]")
interp = ('sangat baik' if auc_val > 0.9 else 'baik' if auc_val > 0.8 else
          'acceptable' if auc_val > 0.7 else 'lemah')
print(f"  Interpretasi    : {interp}")

# 2.4 Calibration
print(f"\n2.4 Kalibrasi Skor:")
bins_edges = [-20, -8, -4, -2, 0, 2]
cal_rows = []
for i in range(len(bins_edges) - 1):
    lo, hi = bins_edges[i], bins_edges[i + 1]
    mask = (df['dm_tel'] >= lo) & (df['dm_tel'] < hi)
    n_bin = mask.sum()
    n_y_bin = df.loc[mask, 'obs_binary'].sum() if n_bin > 0 else 0
    frac = n_y_bin / n_bin if n_bin > 0 else 0
    cal_rows.append({'Bin': f'[{lo}, {hi})', 'N': n_bin, 'N_Y': n_y_bin, 'Frac_Y': frac})
    print(f"  Δm ∈ [{lo:+.0f}, {hi:+.0f}): n={n_bin:>3}, Y={n_y_bin:>2}, frac={frac:.2f}")
df_cal = pd.DataFrame(cal_rows)
monotonic = all(cal_rows[i]['Frac_Y'] <= cal_rows[i+1]['Frac_Y']
                for i in range(len(cal_rows)-1) if cal_rows[i]['N'] > 0 and cal_rows[i+1]['N'] > 0)
print(f"  Monoton? {'YA' if monotonic else 'TIDAK'}")


# ═══════════════════════════════════════════════════════════════
# TAHAP 3: KALIBRASI F DAN VALIDASI
# ═══════════════════════════════════════════════════════════════

print(f"\n{'=' * 70}")
print("TAHAP 3: KALIBRASI F DAN VALIDASI")
print("=" * 70)

# 3.1 Grid search
print(f"\n3.1 Grid Search F (F_ref={F_REF}):")
f_grid = np.arange(0.5, 5.05, 0.1)
scan_rows = []
for F_val in f_grid:
    preds = [(delta_m_at_F(dm, F_REF, F_val) > 0) for dm in df['dm_tel']]
    preds_int = [int(p) for p in preds]
    cm = confusion_metrics(df['obs_binary'].tolist(), preds_int)
    cm['F'] = round(F_val, 2)
    scan_rows.append(cm)
df_scan = pd.DataFrame(scan_rows)

# Find optimal by MCC, then by balanced_acc as tiebreaker
best_idx = df_scan['MCC'].idxmax()
best_F = df_scan.loc[best_idx, 'F']
best_row = df_scan.loc[best_idx]
print(f"  F optimal (MCC maks): {best_F:.1f}")
print(f"  MCC={best_row['MCC']:.4f}, Acc={best_row['Accuracy']:.1%}, "
      f"Sens={best_row['Sensitivity']:.1%}, Spec={best_row['Specificity']:.1%}")

# Show key F values
print(f"\n  {'F':>5} {'Acc':>7} {'Sens':>7} {'Spec':>7} {'MCC':>7} {'BalAcc':>7} "
      f"{'TP':>3} {'TN':>3} {'FP':>3} {'FN':>3}")
for _, r in df_scan.iterrows():
    if r['F'] in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, best_F]:
        mark = " ◄" if r['F'] == best_F else ""
        print(f"  {r['F']:>5.1f} {r['Accuracy']:>7.1%} {r['Sensitivity']:>7.1%} "
              f"{r['Specificity']:>7.1%} {r['MCC']:>7.4f} {r['Balanced_Acc']:>7.1%} "
              f"{r['TP']:>3.0f} {r['TN']:>3.0f} {r['FP']:>3.0f} {r['FN']:>3.0f}{mark}")

# 3.2 LOOCV
print(f"\n3.2 Leave-One-Out Cross-Validation:")
loocv_preds = []
loocv_F_opts = []
for i in range(N_TOTAL):
    train_obs = [df['obs_binary'].iloc[j] for j in range(N_TOTAL) if j != i]
    train_dm = [df['dm_tel'].iloc[j] for j in range(N_TOTAL) if j != i]
    # Find F_opt on training set (maximize MCC)
    best_mcc_train = -2
    best_f_train = F_REF
    for F_val in f_grid:
        tr_preds = [int(delta_m_at_F(dm, F_REF, F_val) > 0) for dm in train_dm]
        cm_tr = confusion_metrics(train_obs, tr_preds)
        if cm_tr['MCC'] > best_mcc_train:
            best_mcc_train = cm_tr['MCC']
            best_f_train = round(F_val, 2)
    # Predict test observation
    dm_test = delta_m_at_F(df['dm_tel'].iloc[i], F_REF, best_f_train)
    loocv_preds.append(int(dm_test > 0))
    loocv_F_opts.append(best_f_train)

cm_loocv = confusion_metrics(df['obs_binary'].tolist(), loocv_preds)
f_opts_arr = np.array(loocv_F_opts)
print(f"  F_opt distribution: mean={f_opts_arr.mean():.2f}, std={f_opts_arr.std():.2f}, "
      f"min={f_opts_arr.min():.1f}, max={f_opts_arr.max():.1f}")
print(f"  Stabil? {'YA (std < 0.5)' if f_opts_arr.std() < 0.5 else 'TIDAK (std >= 0.5)'}")
print(f"\n  LOOCV Confusion Matrix:")
print(f"  Acc={cm_loocv['Accuracy']:.1%}, Sens={cm_loocv['Sensitivity']:.1%}, "
      f"Spec={cm_loocv['Specificity']:.1%}, MCC={cm_loocv['MCC']:.4f}")
print(f"  TP={cm_loocv['TP']}, TN={cm_loocv['TN']}, FP={cm_loocv['FP']}, FN={cm_loocv['FN']}")

# 3.3 McNemar's test (baseline vs optimal)
print(f"\n3.3 McNemar's Test (F={F_REF} vs F={best_F}):")
preds_opt = [int(delta_m_at_F(dm, F_REF, best_F) > 0) for dm in df['dm_tel']]
# Discordant pairs
b = sum(1 for i in range(N_TOTAL) if df['pred_binary'].iloc[i] == df['obs_binary'].iloc[i]
        and preds_opt[i] != df['obs_binary'].iloc[i])
c = sum(1 for i in range(N_TOTAL) if df['pred_binary'].iloc[i] != df['obs_binary'].iloc[i]
        and preds_opt[i] == df['obs_binary'].iloc[i])
if b + c > 0:
    p_mcnemar = stats.binomtest(min(b, c), b + c, 0.5).pvalue
else:
    p_mcnemar = 1.0
print(f"  Diskordansi: b={b} (baseline benar, optimal salah), c={c} (sebaliknya)")
print(f"  p-value (exact): {p_mcnemar:.4f}")
print(f"  Signifikan? {'YA' if p_mcnemar < 0.05 else 'TIDAK'}")


# ═══════════════════════════════════════════════════════════════
# TAHAP 4: PEMBUKTIAN HIPOTESIS — PERAN ATMOSFER
# ═══════════════════════════════════════════════════════════════

print(f"\n{'=' * 70}")
print("TAHAP 4: PEMBUKTIAN HIPOTESIS — PERAN ATMOSFER LOKAL")
print("=" * 70)

# 4.1 Benchmarking vs Yallop & Odeh
print(f"\n4.1 Benchmarking vs Kriteria Yallop (1997) & Odeh (2004):")

# Compute ARCV and W for each observation
# ARCV = Moon Alt at sunset - Sun Alt at sunset ≈ Moon Alt + 0.83° (sun at horizon)
# W = SD × (1 - cos(elongation)), SD ≈ 0.26° = 15.6 arcmin

SD_ARCMIN = 15.6  # approximate moon semidiameter
yallop_rows = []
for _, row in df.iterrows():
    moon_alt = row['Moon Alt Sunset (°)']
    elong = row['Elongasi (°)']
    ARCV = moon_alt + 0.83  # sun at ~-0.83° at sunset
    W = SD_ARCMIN / 60.0 * (1 - math.cos(math.radians(elong)))  # degrees
    W_arcmin = W * 60  # arcminutes for Yallop

    # Yallop q-value
    q_yallop = ARCV - (11.8371 - 6.3226*W_arcmin + 0.7319*W_arcmin**2 - 0.1018*W_arcmin**3)

    # Yallop zones
    if q_yallop >= 0.216: yallop_zone = 'A'
    elif q_yallop >= -0.014: yallop_zone = 'B'
    elif q_yallop >= -0.160: yallop_zone = 'C'
    elif q_yallop >= -0.232: yallop_zone = 'D'
    elif q_yallop >= -0.293: yallop_zone = 'E'
    else: yallop_zone = 'F'

    # Yallop prediction (A/B → visible, C and below → not visible with naked eye)
    # For telescope: A/B/C → visible, D/E/F → not visible
    yallop_pred_tel = 1 if yallop_zone in ['A', 'B', 'C'] else 0
    yallop_pred_ne = 1 if yallop_zone in ['A', 'B'] else 0

    # Odeh V-value
    V_odeh = ARCV - (7.1651 - 6.3226*W_arcmin + 0.7319*W_arcmin**2 - 0.1018*W_arcmin**3)
    if V_odeh >= 5.65: odeh_zone = 'V(FV)'  # easily visible
    elif V_odeh >= 2.00: odeh_zone = 'V(V)'
    elif V_odeh >= -0.96: odeh_zone = 'V(N)'  # needs optical aid
    else: odeh_zone = 'I'  # invisible
    odeh_pred_tel = 1 if odeh_zone in ['V(FV)', 'V(V)', 'V(N)'] else 0

    yallop_rows.append({
        'No': row['No'], 'Lokasi': row['Lokasi'], 'Event': row['event'],
        'ARCV': ARCV, 'W_arcmin': W_arcmin,
        'q_Yallop': q_yallop, 'Yallop_Zone': yallop_zone,
        'Yallop_Pred': yallop_pred_tel,
        'V_Odeh': V_odeh, 'Odeh_Zone': odeh_zone,
        'Odeh_Pred': odeh_pred_tel,
        'Obs': row['obs_binary'],
        'Crumey_Pred': row['pred_binary'],
        'Crumey_dm': row['dm_tel'],
    })

df_bench = pd.DataFrame(yallop_rows)

# Compute metrics for each model
cm_yallop = confusion_metrics(df_bench['Obs'].tolist(), df_bench['Yallop_Pred'].tolist())
cm_odeh = confusion_metrics(df_bench['Obs'].tolist(), df_bench['Odeh_Pred'].tolist())
cm_crumey = cm_base  # already computed

print(f"\n  {'Model':<20} {'Acc':>7} {'Sens':>7} {'Spec':>7} {'MCC':>7} {'BalAcc':>7}")
print(f"  {'-'*55}")
for label, cm in [('Naive (semua N)', {'Accuracy': N_N/N_TOTAL, 'Sensitivity': 0,
                   'Specificity': 1, 'MCC': 0, 'Balanced_Acc': 0.5}),
                  ('Yallop (1997)', cm_yallop), ('Odeh (2004)', cm_odeh),
                  (f'Crumey F={F_REF}', cm_crumey),
                  (f'Crumey F={best_F}', confusion_metrics(df['obs_binary'].tolist(), preds_opt))]:
    print(f"  {label:<20} {cm['Accuracy']:>7.1%} {cm['Sensitivity']:>7.1%} "
          f"{cm['Specificity']:>7.1%} {cm['MCC']:>7.4f} {cm['Balanced_Acc']:>7.1%}")

# Per-event homogeneity test
print(f"\n  Analisis per-event — Apakah model geometris membedakan Y dan N?")
for ev in EVENTS:
    sub = df_bench[df_bench['Event'] == ev]
    if sub['Obs'].sum() == 0: continue
    y_preds = sub[sub['Obs'] == 1]['Yallop_Pred'].values
    n_preds = sub[sub['Obs'] == 0]['Yallop_Pred'].values
    print(f"\n  Event {ev}:")
    print(f"    Yallop: prediksi Y-obs={y_preds}, prediksi N-obs={n_preds}")
    print(f"    → {'HOMOGEN (semua sama)' if len(set(y_preds)) == 1 and len(set(n_preds)) == 1 and set(y_preds) == set(n_preds) else 'HETEROGEN'}")
    c_y = sub[sub['Obs'] == 1]['Crumey_dm'].values
    c_n = sub[sub['Obs'] == 0]['Crumey_dm'].values
    print(f"    Crumey Δm: Y-obs mean={c_y.mean():.2f}, N-obs mean={c_n.mean():.2f}")

# 4.2 Intra-event analysis
print(f"\n4.2 Analisis Intra-Event — Atmosfer sebagai Pembeda:")
sign_diffs = []
t4_intra = []
for ev in EVENTS:
    sub = df[df['event'] == ev]
    y_sub = sub[sub['obs_binary'] == 1]
    n_sub = sub[sub['obs_binary'] == 0]
    if len(y_sub) == 0: continue

    rh_diff = y_sub['RH (%)'].mean() - n_sub['RH (%)'].mean()
    kv_diff = y_sub['k_V'].mean() - n_sub['k_V'].mean()
    t_diff = y_sub['T (°C)'].mean() - n_sub['T (°C)'].mean()
    sign_diffs.append(1 if rh_diff < 0 else 0)  # Y has lower RH?

    row = {'Event': ev, 'n_Y': len(y_sub), 'n_N': len(n_sub),
           'RH_Y': y_sub['RH (%)'].mean(), 'RH_N': n_sub['RH (%)'].mean(),
           'RH_diff': rh_diff,
           'kV_Y': y_sub['k_V'].mean(), 'kV_N': n_sub['k_V'].mean(),
           'kV_diff': kv_diff,
           'T_Y': y_sub['T (°C)'].mean(), 'T_N': n_sub['T (°C)'].mean(),
           'dm_Y': y_sub['dm_tel'].mean(), 'dm_N': n_sub['dm_tel'].mean()}
    t4_intra.append(row)

    print(f"\n  Event {ev} (Y={len(y_sub)}, N={len(n_sub)}):")
    print(f"    RH: Y={y_sub['RH (%)'].mean():.1f}% vs N={n_sub['RH (%)'].mean():.1f}% "
          f"(diff={rh_diff:+.1f}pp) → {'Y lebih KERING' if rh_diff < 0 else 'Y lebih LEMBAB'}")
    print(f"    k_V: Y={y_sub['k_V'].mean():.4f} vs N={n_sub['k_V'].mean():.4f} "
          f"(diff={kv_diff:+.4f})")

df_intra = pd.DataFrame(t4_intra)

# Sign test
n_consistent = sum(sign_diffs)
n_events_mixed = len(sign_diffs)
if n_events_mixed > 0:
    p_sign = stats.binomtest(n_consistent, n_events_mixed, 0.5).pvalue
    print(f"\n  Sign test (Y memiliki RH lebih rendah):")
    print(f"    Konsisten: {n_consistent}/{n_events_mixed} event")
    print(f"    p-value: {p_sign:.4f}")

# 4.3 Correlation
print(f"\n4.3 Korelasi Spearman:")
corr_vars = ['RH (%)', 'T (°C)', 'k_V', 'Moon Alt Sunset (°)', 'Elongasi (°)']
corr_rows = []
for var in corr_vars:
    rho, p = stats.spearmanr(df[var], df['dm_tel'])
    corr_rows.append({'Variable': var, 'Spearman_rho': rho, 'p_value': p})
    print(f"  Δm vs {var:<22s}: ρ={rho:+.4f}, p={p:.4f} {'*' if p < 0.05 else ''}")
df_corr = pd.DataFrame(corr_rows).sort_values('p_value')


# ═══════════════════════════════════════════════════════════════
# TAHAP 6: ANALISIS RESIDUAL
# ═══════════════════════════════════════════════════════════════

print(f"\n{'=' * 70}")
print("TAHAP 6: ANALISIS RESIDUAL & POLA ERROR")
print("=" * 70)

# Categorize errors
error_rows = []
for _, row in df.iterrows():
    obs = row['obs_binary']
    pred = row['pred_binary']
    dm = row['dm_tel']
    if obs == 1 and pred == 0:
        cat = 'FN'
        if dm > -1: severity = 'Near-miss'
        elif dm > -3: severity = 'Moderate'
        else: severity = 'Severe'
    elif obs == 0 and pred == 1:
        cat = 'FP'; severity = 'FP'
    elif obs == 1 and pred == 1:
        cat = 'TP'; severity = 'TP'
    else:
        cat = 'TN'; severity = 'TN'
    error_rows.append({'No': row['No'], 'Lokasi': row['Lokasi'],
                       'Event': row['event'], 'Obs': row['Obs Tel (Y/N)'],
                       'Pred': row['Pred Tel'], 'Category': cat,
                       'Severity': severity, 'Δm_Tel': dm,
                       'RH': row['RH (%)'], 'kV': row['k_V'],
                       'Moon_Alt': row['Moon Alt Sunset (°)'],
                       'Elongasi': row['Elongasi (°)']})
df_errors = pd.DataFrame(error_rows)

print(f"\n  Kategorisasi Error:")
for cat in ['TP', 'TN', 'FP', 'FN']:
    sub = df_errors[df_errors['Category'] == cat]
    print(f"    {cat}: {len(sub)} observasi")
    if cat in ['FN', 'FP']:
        for _, r in sub.iterrows():
            print(f"      #{r['No']:2d} {r['Lokasi']:<40s} Δm={r['Δm_Tel']:+.3f} "
                  f"RH={r['RH']:.1f}% k_V={r['kV']:.4f} [{r['Severity']}]")


# ═══════════════════════════════════════════════════════════════
# TABEL RINGKASAN (TAHAP 7)
# ═══════════════════════════════════════════════════════════════

print(f"\n{'=' * 70}")
print("TAHAP 7: TABEL RINGKASAN PERFORMA")
print("=" * 70)

cm_opt = confusion_metrics(df['obs_binary'].tolist(), preds_opt)
summary_rows = [
    {'Model': 'Majority Classifier', 'Acc': N_N/N_TOTAL, 'Sens': 0, 'Spec': 1.0,
     'MCC': 0, 'Bal_Acc': 0.5, 'AUC': 0.5},
    {'Model': f'Crumey F={F_REF} (baseline)', 'Acc': cm_base['Accuracy'],
     'Sens': cm_base['Sensitivity'], 'Spec': cm_base['Specificity'],
     'MCC': cm_base['MCC'], 'Bal_Acc': cm_base['Balanced_Acc'], 'AUC': auc_val},
    {'Model': f'Crumey F={best_F} (optimal, in-sample)', 'Acc': cm_opt['Accuracy'],
     'Sens': cm_opt['Sensitivity'], 'Spec': cm_opt['Specificity'],
     'MCC': cm_opt['MCC'], 'Bal_Acc': cm_opt['Balanced_Acc'], 'AUC': auc_val},
    {'Model': f'Crumey LOOCV', 'Acc': cm_loocv['Accuracy'],
     'Sens': cm_loocv['Sensitivity'], 'Spec': cm_loocv['Specificity'],
     'MCC': cm_loocv['MCC'], 'Bal_Acc': cm_loocv['Balanced_Acc'], 'AUC': auc_val},
    {'Model': 'Yallop (1997)', 'Acc': cm_yallop['Accuracy'],
     'Sens': cm_yallop['Sensitivity'], 'Spec': cm_yallop['Specificity'],
     'MCC': cm_yallop['MCC'], 'Bal_Acc': cm_yallop['Balanced_Acc'], 'AUC': 'N/A'},
    {'Model': 'Odeh (2004)', 'Acc': cm_odeh['Accuracy'],
     'Sens': cm_odeh['Sensitivity'], 'Spec': cm_odeh['Specificity'],
     'MCC': cm_odeh['MCC'], 'Bal_Acc': cm_odeh['Balanced_Acc'], 'AUC': 'N/A'},
]
df_summary = pd.DataFrame(summary_rows)

print(f"\n  {'Model':<35} {'Acc':>7} {'Sens':>7} {'Spec':>7} {'MCC':>7} {'BalAcc':>7} {'AUC':>7}")
print(f"  {'-'*78}")
for _, r in df_summary.iterrows():
    auc_str = f"{r['AUC']:.4f}" if isinstance(r['AUC'], float) else r['AUC']
    print(f"  {r['Model']:<35} {r['Acc']:>7.1%} {r['Sens']:>7.1%} {r['Spec']:>7.1%} "
          f"{r['MCC']:>7.4f} {r['Bal_Acc']:>7.1%} {auc_str:>7}")


# ═══════════════════════════════════════════════════════════════
# VISUALISASI
# ═══════════════════════════════════════════════════════════════

# Plot 1: ROC Curve
fpr_list, tpr_list = compute_roc_curve(labels_list, scores_list)
fig, ax = plt.subplots(figsize=(7, 7))
ax.plot(fpr_list, tpr_list, 'b-', linewidth=2.5, label=f'Model Crumey (AUC={auc_val:.3f})')
ax.plot([0, 1], [0, 1], 'k--', linewidth=1, alpha=0.5, label='Random (AUC=0.500)')
ax.fill_between(fpr_list, tpr_list, alpha=0.1, color='blue')
ax.set_xlabel('False Positive Rate (1 − Specificity)', fontsize=12, fontweight='bold')
ax.set_ylabel('True Positive Rate (Sensitivity)', fontsize=12, fontweight='bold')
ax.set_title(f'ROC Curve — Model Visibilitas Hilal\nAUC = {auc_val:.3f} [95% CI: {auc_lo:.3f}–{auc_hi:.3f}]',
             fontsize=13, fontweight='bold')
ax.legend(fontsize=11, loc='lower right')
ax.set_xlim(-0.02, 1.02); ax.set_ylim(-0.02, 1.02)
ax.grid(True, alpha=0.3)
ax.set_aspect('equal')
fig.savefig(f'{OUT_DIR}/ROC_Curve.png', dpi=150, bbox_inches='tight')
plt.close()

# Plot 2: F-scan metrics
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(df_scan['F'], df_scan['Accuracy']*100, 'b-', lw=2.5, label='Accuracy')
ax.plot(df_scan['F'], df_scan['Sensitivity']*100, 'g--', lw=1.5, label='Sensitivity')
ax.plot(df_scan['F'], df_scan['Specificity']*100, 'r--', lw=1.5, label='Specificity')
ax.plot(df_scan['F'], df_scan['MCC']*100, 'm:', lw=2, label='MCC ×100')
ax.plot(df_scan['F'], df_scan['Balanced_Acc']*100, 'c-.', lw=1.5, label='Balanced Acc')
ax.axvline(x=best_F, color='orange', lw=1.5, ls='-.', label=f'F optimal={best_F:.1f}')
ax.axvline(x=F_REF, color='gray', lw=1, ls=':', alpha=0.5, label=f'F ref={F_REF}')
ax.set_xlabel('Field Factor (F)', fontsize=12, fontweight='bold')
ax.set_ylabel('Metrik (%)', fontsize=12, fontweight='bold')
ax.set_title('Performa Model vs Field Factor F\n(Grid Search, in-sample)', fontsize=13, fontweight='bold')
ax.legend(fontsize=9, loc='best')
ax.set_xlim(0.5, 5.0); ax.set_ylim(-5, 105)
ax.grid(True, alpha=0.3)
fig.savefig(f'{OUT_DIR}/F_Scan_Metrics.png', dpi=150, bbox_inches='tight')
plt.close()

# Plot 3: Box plot Δm by group
fig, ax = plt.subplots(figsize=(8, 6))
bp = ax.boxplot([dm_Y, dm_N], labels=['Terlihat (Y)', 'Tidak Terlihat (N)'],
                patch_artist=True, widths=0.5)
bp['boxes'][0].set_facecolor('#4CAF50'); bp['boxes'][1].set_facecolor('#F44336')
for i, (data, x) in enumerate(zip([dm_Y, dm_N], [1, 2])):
    ax.scatter([x]*len(data), data, c='black', s=30, zorder=5, alpha=0.7)
ax.axhline(y=0, color='green', ls='--', lw=1.5, alpha=0.7, label='Threshold Δm=0')
ax.set_ylabel('Δm Teleskop Optimal (mag)', fontsize=12, fontweight='bold')
ax.set_title(f'Distribusi Δm per Kelompok Observasi\n'
             f'Mann-Whitney U p={p_mw:.4f}, Cohen\'s d={cohens_d:.2f}',
             fontsize=13, fontweight='bold')
ax.legend(); ax.grid(True, axis='y', alpha=0.3)
fig.savefig(f'{OUT_DIR}/BoxPlot_DeltaM.png', dpi=150, bbox_inches='tight')
plt.close()

# Plot 4: Intra-event comparison
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
events_mixed = df_intra['Event'].values
x = np.arange(len(events_mixed))
w = 0.35
axes[0].bar(x - w/2, df_intra['RH_Y'], w, label='Lokasi Y', color='#4CAF50', edgecolor='black', lw=0.5)
axes[0].bar(x + w/2, df_intra['RH_N'], w, label='Lokasi N', color='#F44336', edgecolor='black', lw=0.5)
axes[0].set_ylabel('RH (%)', fontsize=12, fontweight='bold')
axes[0].set_title('RH: Lokasi Y vs N per Event', fontsize=13, fontweight='bold')
axes[0].set_xticks(x); axes[0].set_xticklabels([e[:10] for e in events_mixed], fontsize=9)
axes[0].legend(); axes[0].grid(True, axis='y', alpha=0.3)

axes[1].bar(x - w/2, df_intra['kV_Y'], w, label='Lokasi Y', color='#4CAF50', edgecolor='black', lw=0.5)
axes[1].bar(x + w/2, df_intra['kV_N'], w, label='Lokasi N', color='#F44336', edgecolor='black', lw=0.5)
axes[1].set_ylabel('k_V', fontsize=12, fontweight='bold')
axes[1].set_title('k_V: Lokasi Y vs N per Event', fontsize=13, fontweight='bold')
axes[1].set_xticks(x); axes[1].set_xticklabels([e[:10] for e in events_mixed], fontsize=9)
axes[1].legend(); axes[1].grid(True, axis='y', alpha=0.3)
plt.tight_layout()
fig.savefig(f'{OUT_DIR}/IntraEvent_Comparison.png', dpi=150, bbox_inches='tight')
plt.close()

print(f"\n  Plot disimpan di {OUT_DIR}/")


# ═══════════════════════════════════════════════════════════════
# SAVE TO EXCEL
# ═══════════════════════════════════════════════════════════════

EXCEL_OUT = f'{OUT_DIR}/Evaluasi_Komprehensif_Model.xlsx'
with pd.ExcelWriter(EXCEL_OUT, engine='openpyxl') as writer:
    # Sheet 1: Data lengkap + benchmark
    df_full = df.merge(df_bench[['No','ARCV','W_arcmin','q_Yallop','Yallop_Zone',
                                  'V_Odeh','Odeh_Zone','Yallop_Pred','Odeh_Pred']],
                       on='No', how='left')
    df_full.to_excel(writer, sheet_name='Data + Benchmark', index=False)

    # Sheet 2: F-Scan
    df_scan.to_excel(writer, sheet_name='F-Scan', index=False)

    # Sheet 3: LOOCV detail
    df_loocv = pd.DataFrame({
        'No': df['No'], 'Lokasi': df['Lokasi'], 'Event': df['event'],
        'Obs': df['Obs Tel (Y/N)'], 'Δm_Tel_Opt': df['dm_tel'],
        'F_opt_LOOCV': loocv_F_opts, 'Pred_LOOCV': ['Y' if p else 'N' for p in loocv_preds],
        'Correct': ['✓' if p == o else '✗' for p, o in zip(loocv_preds, df['obs_binary'])]
    })
    df_loocv.to_excel(writer, sheet_name='LOOCV Detail', index=False)

    # Sheet 4: Benchmark comparison
    df_bench.to_excel(writer, sheet_name='Benchmark Yallop Odeh', index=False)

    # Sheet 5: Intra-event
    df_intra.to_excel(writer, sheet_name='Intra-Event', index=False)

    # Sheet 6: Correlation
    df_corr.to_excel(writer, sheet_name='Korelasi', index=False)

    # Sheet 7: Error analysis
    df_errors.to_excel(writer, sheet_name='Analisis Error', index=False)

    # Sheet 8: Summary table
    df_summary.to_excel(writer, sheet_name='Ringkasan Performa', index=False)

    # Sheet 9: Calibration
    df_cal.to_excel(writer, sheet_name='Kalibrasi', index=False)

    # Sheet 10: Block design
    df_block.to_excel(writer, sheet_name='Block Design', index=False)

print(f"\n  Excel disimpan: {EXCEL_OUT}")
print(f"\n{'=' * 70}")
print("  EVALUASI SELESAI")
print(f"{'=' * 70}")
EOF