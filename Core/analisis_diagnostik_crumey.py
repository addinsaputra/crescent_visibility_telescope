#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════════════
ANALISIS DIAGNOSTIK MODEL CRUMEY (2014)
Tahap 4a-4d & 5c: Sensitivitas RH, Dekomposisi Error, Korelasi k_V
══════════════════════════════════════════════════════════════════════

Script ini membaca output dari batch_validation_crumey.py, kemudian
melakukan analisis diagnostik LOKAL (tanpa API call) untuk menentukan
penyebab utama error prediksi.

TAHAP YANG DICAKUP:
  4a. Korelasi k_V dengan akurasi prediksi
  4b. Sensitivitas Δm terhadap variasi RH
  4c. Dekomposisi rantai error (sky brightness vs luminansi)
  4d. Perbandingan antar lokasi per event
  5c. Estimasi error bar Δm dari ketidakpastian RH

INPUT: Validasi_Crumey_29obs_era5_optimal.xlsx (dari batch run)
OUTPUT: Analisis_Diagnostik_Crumey.xlsx + plot

CARA PAKAI:
  1. Letakkan di direktori Core/
  2. Pastikan file Excel input ada di Core/output/
  3. Jalankan: python analisis_diagnostik_crumey.py
══════════════════════════════════════════════════════════════════════
"""

import math
import os
import sys
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple

# Pastikan Core/ di PATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from visual_limit_schaefer import hitung_sky_brightness
from visual_limit_kastner import hitung_luminansi_kastner
from full_rumus_crumey import (
    nL_to_cdm2, cdm2_to_nL, arcmin2_to_sr,
    contrast_threshold, crescent_area_arcmin2,
)


# ═══════════════════════════════════════════════════════════════════
# KONFIGURASI
# ═══════════════════════════════════════════════════════════════════

INPUT_XLSX = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'output',
    'Validasi_Crumey_29obs_era5_optimal.xlsx'
)

# RH variations (percentage points, added to baseline)
RH_DELTAS = [-30, -25, -20, -15, -10, -5, 0, +5, +10]

# Telescope parameters (harus sama dengan batch run)
TEL_APERTURE = 66.0     # mm
TEL_MAG = 50.0
TEL_TRANS = 0.95
TEL_NSURFACES = 6
TEL_OBSTRUCTION = 0.0
TEL_AGE = 30.0

# Field factors
F_NAKED = 2.0
F_TEL = 2.0  # phi = sqrt(2) * 1.0 * F_TEL

# Moon semidiameter (default, ~0.26°)
MOON_SD_DEG = 0.26


# ═══════════════════════════════════════════════════════════════════
# FUNGSI UTILITAS
# ═══════════════════════════════════════════════════════════════════

def estimate_sun_alt_at_optimal(sunset_str: str, optimal_str: str) -> float:
    """Estimasi sun altitude di waktu optimal.
    Matahari turun ~1°/4 menit setelah sunset di tropis."""
    try:
        from datetime import datetime
        # Parse (handle timezone info)
        sunset_clean = sunset_str.split('+')[0].split('.')[0]
        optimal_clean = optimal_str.split('+')[0].split('.')[0]
        fmt = '%Y-%m-%d %H:%M:%S'
        dt_sunset = datetime.strptime(sunset_clean, fmt)
        dt_optimal = datetime.strptime(optimal_clean, fmt)
        delta_min = (dt_optimal - dt_sunset).total_seconds() / 60.0
    except Exception:
        delta_min = 7.0  # default: 7 menit setelah sunset

    # Sun descent rate: ~0.25°/menit di tropis saat sunset
    return -0.833 - 0.25 * max(delta_min, 0)


def estimate_azimuth_diff(elongation: float, sun_alt: float, moon_alt: float) -> float:
    """Hitung selisih azimuth Sun-Moon dari elongasi via spherical trig."""
    rd = math.pi / 180.0
    cos_elong = math.cos(elongation * rd)
    sin_sun = math.sin(sun_alt * rd)
    sin_moon = math.sin(moon_alt * rd)
    cos_sun = math.cos(sun_alt * rd)
    cos_moon = math.cos(moon_alt * rd)

    denom = cos_sun * cos_moon
    if abs(denom) < 1e-10:
        return elongation  # fallback

    cos_daz = (cos_elong - sin_sun * sin_moon) / denom
    cos_daz = max(-1.0, min(1.0, cos_daz))
    return math.degrees(math.acos(cos_daz))


def compute_telescope_Ba(B_sky_nL: float) -> float:
    """Hitung apparent background melalui teleskop (Crumey Eq. 66)."""
    d_exit = TEL_APERTURE / TEL_MAG  # exit pupil [mm]
    De = 7.0 * math.exp(-0.5 * (TEL_AGE / 100.0) ** 2)  # pupil mata [mm]
    Ft = 1.0 / (TEL_TRANS ** TEL_NSURFACES * (1.0 - (TEL_OBSTRUCTION / TEL_APERTURE) ** 2
                 if TEL_OBSTRUCTION > 0 else 1.0))

    delta_min = min(d_exit, De)
    Ba_factor = (delta_min / De) ** 2 / Ft
    return B_sky_nL * Ba_factor


def compute_delta_m(L_nL: float, B_nL: float, phase_angle: float,
                    mode: str = 'naked_eye') -> Dict[str, float]:
    """Hitung Δm (naked eye atau teleskop) dari luminansi dan sky brightness."""
    B_cd = nL_to_cdm2(B_nL)
    L_cd = nL_to_cdm2(L_nL)

    if B_cd <= 0 or L_cd <= 0:
        return {'delta_m': -99.0, 'C_obj': 0, 'C_th': 0, 'k_ratio': 0}

    C_obj = (L_cd - B_cd) / B_cd
    A_arcmin2 = crescent_area_arcmin2(phase_angle, MOON_SD_DEG)
    A_sr = arcmin2_to_sr(A_arcmin2)
    if A_sr <= 0:
        A_sr = 1e-12

    if mode == 'naked_eye':
        C_th = contrast_threshold(A_sr, B_cd, F=F_NAKED, mode='auto')
    else:  # telescope
        B_tel_nL = compute_telescope_Ba(B_nL)
        B_tel_cd = nL_to_cdm2(B_tel_nL)
        if B_tel_cd <= 0:
            B_tel_cd = 1e-10
        A_eff = A_sr * (TEL_MAG ** 2)
        phi = math.sqrt(2) * 1.0 * F_TEL
        C_th = contrast_threshold(A_eff, B_tel_cd, F=phi, mode='auto')

    if C_obj > 0 and C_th > 0:
        delta_m = 2.5 * math.log10(C_obj / C_th)
    elif C_th > 0:
        L_over_B = max(1.0 + C_obj, 1e-15)
        delta_m = 2.5 * (math.log10(L_over_B) - math.log10(C_th))
    else:
        delta_m = -99.0

    return {'delta_m': delta_m, 'C_obj': C_obj, 'C_th': C_th}


def compute_full_chain(row: pd.Series, rh_override: float) -> Dict[str, float]:
    """Jalankan rantai fisika lengkap untuk satu observasi dengan RH tertentu.

    Returns dict dengan: k_V, B_sky_nL, L_hilal_nL, dm_ne, dm_tel, dll.
    """
    # Parameter astronomi (tetap)
    moon_alt = row['Moon Alt (°)']
    phase_angle = row['Phase Angle (°)']
    elongation = row['Elongasi (°)']
    temperature = row['T (°C)']
    lat = row['Lat']
    elv = row['Elv']

    # Parse tanggal
    tgl = pd.to_datetime(row['Tanggal'])
    month = tgl.month
    year = tgl.year

    # Estimasi sun_alt dan azimuth_diff
    sun_alt = estimate_sun_alt_at_optimal(
        str(row.get('Sunset Lokal', '')),
        str(row.get('Waktu Optimal Tel', ''))
    )
    azisun = estimate_azimuth_diff(elongation, sun_alt, moon_alt)

    # Clamp RH
    rh_used = max(5.0, min(100.0, rh_override))

    # ── RANTAI 1: Sky Brightness (Schaefer) ──
    try:
        result_sky = hitung_sky_brightness(
            month=month, year=year,
            altsun=sun_alt, azisun=azisun,
            humidity=rh_used, temperature=temperature,
            latitude=lat, elevation=elv,
            alt_objek=max(moon_alt, 0.01),
        )
        B_sky_nL = float(result_sky.get('sky_brightness', 0))
        K_list = result_sky.get('K', [])
        k_v = float(K_list[2]) if len(K_list) > 2 else 0.3
    except Exception:
        B_sky_nL = 1e9
        k_v = 0.5

    if B_sky_nL <= 0:
        B_sky_nL = 1.0

    # ── RANTAI 2: Luminansi Hilal (Kastner) ──
    z = 90.0 - moon_alt
    try:
        L_hilal_nL = hitung_luminansi_kastner(
            alpha=phase_angle, r=MOON_SD_DEG, z=z, k=k_v
        )
    except Exception:
        L_hilal_nL = 0.0

    # ── RANTAI 3: Visibilitas (Crumey) ──
    result_ne = compute_delta_m(L_hilal_nL, B_sky_nL, phase_angle, 'naked_eye')
    result_tel = compute_delta_m(L_hilal_nL, B_sky_nL, phase_angle, 'telescope')

    return {
        'rh_used': rh_used,
        'k_v': k_v,
        'B_sky_nL': B_sky_nL,
        'L_hilal_nL': L_hilal_nL,
        'C_obj': result_ne['C_obj'],
        'C_th_ne': result_ne['C_th'],
        'C_th_tel': result_tel['C_th'],
        'dm_ne': result_ne['delta_m'],
        'dm_tel': result_tel['delta_m'],
        'sun_alt_est': sun_alt,
    }


# ═══════════════════════════════════════════════════════════════════
# TAHAP 4a: KORELASI k_V
# ═══════════════════════════════════════════════════════════════════

def analyze_kv_correlation(df: pd.DataFrame) -> pd.DataFrame:
    """Analisis korelasi k_V dengan akurasi prediksi."""
    print("\n" + "═" * 70)
    print("TAHAP 4a: KORELASI k_V DENGAN AKURASI PREDIKSI")
    print("═" * 70)

    df['correct'] = df['Cocok?'] == '✓'
    df['is_Y'] = df['Obs (Y/N)'] == 'Y'

    # Statistik per kelompok
    groups = {
        'TN (benar N)': df[(~df['is_Y']) & (df['correct'])],
        'FN (salah N)': df[(df['is_Y']) & (~df['correct'])],
    }

    rows = []
    for label, sub in groups.items():
        if len(sub) == 0:
            continue
        rows.append({
            'Kelompok': label,
            'N': len(sub),
            'k_V mean': sub['k_V'].mean(),
            'k_V std': sub['k_V'].std(),
            'k_V min': sub['k_V'].min(),
            'k_V max': sub['k_V'].max(),
            'RH mean': sub['RH (%)'].mean(),
            'RH std': sub['RH (%)'].std(),
            'Δm Tel Opt mean': sub['Δm Tel Opt'].mean(),
        })

    result_df = pd.DataFrame(rows)
    print(result_df.to_string(index=False))

    # Per-event comparison
    print("\n  Per-Event k_V Comparison (Y vs N):")
    for tgl in df['Tanggal'].unique():
        sub = df[df['Tanggal'] == tgl]
        y_sub = sub[sub['is_Y']]
        n_sub = sub[~sub['is_Y']]
        if len(y_sub) == 0:
            continue
        print(f"\n  {tgl}: Y(n={len(y_sub)}) k_V={y_sub['k_V'].mean():.4f} ± {y_sub['k_V'].std():.4f} | "
              f"RH={y_sub['RH (%)'].mean():.1f}%")
        print(f"  {' '*11}N(n={len(n_sub)}) k_V={n_sub['k_V'].mean():.4f} ± {n_sub['k_V'].std():.4f} | "
              f"RH={n_sub['RH (%)'].mean():.1f}%")

    return result_df


# ═══════════════════════════════════════════════════════════════════
# TAHAP 4b: SENSITIVITAS RH
# ═══════════════════════════════════════════════════════════════════

def analyze_rh_sensitivity(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Variasikan RH dan ukur dampak pada Δm untuk semua observasi."""
    print("\n" + "═" * 70)
    print("TAHAP 4b: SENSITIVITAS Δm TERHADAP VARIASI RH")
    print("═" * 70)

    all_rows = []
    critical_rows = []

    for idx, row in df.iterrows():
        obs_no = int(row['No'])
        rh_baseline = row['RH (%)']
        obs_yn = row['Obs (Y/N)']
        is_FN = (obs_yn == 'Y') and (row['Cocok?'] == '✗')

        print(f"\n  Obs #{obs_no:2d} {row['Lokasi'][:30]:30s} "
              f"({'FN' if is_FN else 'TN' if obs_yn == 'N' else 'TP'}) "
              f"RH_base={rh_baseline:.1f}%")

        dm_at_deltas = {}
        kv_at_deltas = {}

        for delta_rh in RH_DELTAS:
            rh_test = rh_baseline + delta_rh
            if rh_test < 5 or rh_test > 100:
                continue

            result = compute_full_chain(row, rh_test)

            label = f"ΔRH={delta_rh:+d}"
            dm_at_deltas[delta_rh] = result['dm_tel']
            kv_at_deltas[delta_rh] = result['k_v']

            entry = {
                'No': obs_no,
                'Lokasi': row['Lokasi'],
                'Obs': obs_yn,
                'Tipe': 'FN' if is_FN else ('TN' if obs_yn == 'N' else 'TP'),
                'RH_baseline': rh_baseline,
                'ΔRH': delta_rh,
                'RH_test': rh_test,
                'k_V': result['k_v'],
                'B_sky_nL': result['B_sky_nL'],
                'L_hilal_nL': result['L_hilal_nL'],
                'Δm_NE': result['dm_ne'],
                'Δm_Tel': result['dm_tel'],
                'C_obj': result['C_obj'],
            }
            all_rows.append(entry)

        # Cari critical RH (Δm_tel = 0) via interpolasi
        deltas_sorted = sorted(dm_at_deltas.keys())
        critical_rh = None
        for i in range(len(deltas_sorted) - 1):
            d1, d2 = deltas_sorted[i], deltas_sorted[i+1]
            dm1, dm2 = dm_at_deltas[d1], dm_at_deltas[d2]
            if dm1 <= -90 or dm2 <= -90:
                continue
            if (dm1 <= 0 <= dm2) or (dm2 <= 0 <= dm1):
                # Linear interpolation
                frac = -dm1 / (dm2 - dm1) if (dm2 - dm1) != 0 else 0
                critical_delta = d1 + frac * (d2 - d1)
                critical_rh = rh_baseline + critical_delta
                break

        # Δm improvement from -20% RH
        dm_base = dm_at_deltas.get(0, -99)
        dm_minus20 = dm_at_deltas.get(-20, dm_at_deltas.get(-25, -99))
        improvement = dm_minus20 - dm_base if dm_base > -90 and dm_minus20 > -90 else 0

        critical_rows.append({
            'No': obs_no,
            'Lokasi': row['Lokasi'],
            'Obs': obs_yn,
            'Tipe': 'FN' if is_FN else ('TN' if obs_yn == 'N' else 'TP'),
            'RH_baseline': rh_baseline,
            'k_V_baseline': kv_at_deltas.get(0, 0),
            'Δm_Tel_baseline': dm_base,
            'Δm_Tel_RH-20': dm_minus20,
            'Improvement_20': improvement,
            'RH_kritis': critical_rh if critical_rh else 'N/A',
            'Butuh_ΔRH': (critical_rh - rh_baseline) if critical_rh else 'N/A',
        })

        # Print ringkasan
        status = f"RH_kritis={critical_rh:.1f}%" if critical_rh else "di luar range"
        print(f"    Δm(base)={dm_base:+.2f}  Δm(RH-20)={dm_minus20:+.2f}  "
              f"gain={improvement:+.2f}  {status}")

    return pd.DataFrame(all_rows), pd.DataFrame(critical_rows)


# ═══════════════════════════════════════════════════════════════════
# TAHAP 4c: DEKOMPOSISI RANTAI ERROR
# ═══════════════════════════════════════════════════════════════════

def analyze_error_decomposition(df: pd.DataFrame) -> pd.DataFrame:
    """Dekomposisi: seberapa besar kontribusi sky brightness vs luminansi."""
    print("\n" + "═" * 70)
    print("TAHAP 4c: DEKOMPOSISI RANTAI ERROR")
    print("═" * 70)

    fn_obs = df[(df['Obs (Y/N)'] == 'Y') & (df['Cocok?'] == '✗')]
    decomp_rows = []

    for _, row in fn_obs.iterrows():
        obs_no = int(row['No'])
        rh_base = row['RH (%)']

        print(f"\n  Obs #{obs_no}: {row['Lokasi']}")

        # Baseline
        res_base = compute_full_chain(row, rh_base)

        # Skenario 1: Kurangi RH 20pp → dampak penuh
        rh_low = max(rh_base - 20, 5.0)
        res_low = compute_full_chain(row, rh_low)

        # Skenario 2: Gunakan k_V rendah tapi B_sky dari baseline RH
        # (isolasi efek k_V pada luminansi saja)
        z = 90.0 - row['Moon Alt (°)']
        L_with_low_kv = hitung_luminansi_kastner(
            alpha=row['Phase Angle (°)'], r=MOON_SD_DEG, z=z, k=res_low['k_v']
        )
        res_only_L = compute_delta_m(
            L_with_low_kv, res_base['B_sky_nL'], row['Phase Angle (°)'], 'telescope'
        )

        # Skenario 3: Gunakan B_sky rendah tapi L_hilal dari baseline k_V
        res_only_B = compute_delta_m(
            res_base['L_hilal_nL'], res_low['B_sky_nL'], row['Phase Angle (°)'], 'telescope'
        )

        # Hitung kontribusi
        dm_full_change = res_low['dm_tel'] - res_base['dm_tel']
        dm_L_only = res_only_L['delta_m'] - res_base['dm_tel']
        dm_B_only = res_only_B['delta_m'] - res_base['dm_tel']
        dm_interaction = dm_full_change - dm_L_only - dm_B_only

        decomp_rows.append({
            'No': obs_no,
            'Lokasi': row['Lokasi'],
            'RH_base': rh_base,
            'RH_low': rh_low,
            'k_V_base': res_base['k_v'],
            'k_V_low': res_low['k_v'],
            'Δk_V': res_low['k_v'] - res_base['k_v'],
            'B_sky_base': res_base['B_sky_nL'],
            'B_sky_low': res_low['B_sky_nL'],
            'L_hilal_base': res_base['L_hilal_nL'],
            'L_hilal_low': res_low['L_hilal_nL'],
            'L_ratio': res_low['L_hilal_nL'] / res_base['L_hilal_nL']
                       if res_base['L_hilal_nL'] > 0 else 0,
            'Δm_base': res_base['dm_tel'],
            'Δm_full_change': dm_full_change,
            'Δm_dari_L (k_V→Kastner)': dm_L_only,
            'Δm_dari_B (k_V→Schaefer)': dm_B_only,
            'Δm_interaksi': dm_interaction,
            'Kontribusi_L (%)': abs(dm_L_only) / abs(dm_full_change) * 100
                                if abs(dm_full_change) > 0.001 else 0,
            'Kontribusi_B (%)': abs(dm_B_only) / abs(dm_full_change) * 100
                                if abs(dm_full_change) > 0.001 else 0,
        })

        print(f"    k_V: {res_base['k_v']:.4f} → {res_low['k_v']:.4f} (Δ={res_low['k_v']-res_base['k_v']:+.4f})")
        print(f"    Δm_tel: {res_base['dm_tel']:+.3f} → {res_low['dm_tel']:+.3f} (gain={dm_full_change:+.3f})")
        print(f"    Kontribusi: L(Kastner)={dm_L_only:+.3f} | B(Schaefer)={dm_B_only:+.3f} | interaksi={dm_interaction:+.3f}")

    return pd.DataFrame(decomp_rows)


# ═══════════════════════════════════════════════════════════════════
# TAHAP 4d: PERBANDINGAN ANTAR LOKASI PER EVENT
# ═══════════════════════════════════════════════════════════════════

def analyze_inter_location(df: pd.DataFrame) -> pd.DataFrame:
    """Perbandingan statistik antar lokasi pada event yang sama."""
    print("\n" + "═" * 70)
    print("TAHAP 4d: PERBANDINGAN ANTAR LOKASI PER EVENT")
    print("═" * 70)

    event_rows = []
    for tgl in sorted(df['Tanggal'].unique()):
        sub = df[df['Tanggal'] == tgl]
        y_sub = sub[sub['Obs (Y/N)'] == 'Y']
        n_sub = sub[sub['Obs (Y/N)'] == 'N']

        event_rows.append({
            'Event': str(tgl),
            'N_total': len(sub),
            'N_Y': len(y_sub),
            'N_N': len(n_sub),
            'RH_Y_mean': y_sub['RH (%)'].mean() if len(y_sub) > 0 else None,
            'RH_N_mean': n_sub['RH (%)'].mean() if len(n_sub) > 0 else None,
            'RH_diff': (y_sub['RH (%)'].mean() - n_sub['RH (%)'].mean())
                       if len(y_sub) > 0 and len(n_sub) > 0 else None,
            'k_V_Y_mean': y_sub['k_V'].mean() if len(y_sub) > 0 else None,
            'k_V_N_mean': n_sub['k_V'].mean() if len(n_sub) > 0 else None,
            'k_V_diff': (y_sub['k_V'].mean() - n_sub['k_V'].mean())
                        if len(y_sub) > 0 and len(n_sub) > 0 else None,
            'Δm_Y_mean': y_sub['Δm Tel Opt'].mean() if len(y_sub) > 0 else None,
            'Δm_N_mean': n_sub['Δm Tel Opt'].mean() if len(n_sub) > 0 else None,
            'Elong_range': f"{sub['Elongasi (°)'].min():.2f}-{sub['Elongasi (°)'].max():.2f}",
        })

        if len(y_sub) > 0:
            print(f"\n  {tgl}:")
            print(f"    Y obs: RH_mean={y_sub['RH (%)'].mean():.1f}%, k_V_mean={y_sub['k_V'].mean():.4f}")
            print(f"    N obs: RH_mean={n_sub['RH (%)'].mean():.1f}%, k_V_mean={n_sub['k_V'].mean():.4f}")
            rh_diff = y_sub['RH (%)'].mean() - n_sub['RH (%)'].mean()
            print(f"    ΔRH(Y-N) = {rh_diff:+.1f}pp → {'Y lebih lembab' if rh_diff > 0 else 'Y lebih kering'}")

    return pd.DataFrame(event_rows)


# ═══════════════════════════════════════════════════════════════════
# TAHAP 5c: ESTIMASI ERROR BAR
# ═══════════════════════════════════════════════════════════════════

def analyze_error_bars(sensitivity_df: pd.DataFrame, critical_df: pd.DataFrame) -> pd.DataFrame:
    """Estimasi error bar Δm berdasarkan ketidakpastian RH ERA5."""
    print("\n" + "═" * 70)
    print("TAHAP 5c: ESTIMASI ERROR BAR Δm")
    print("═" * 70)

    # ERA5 RH uncertainty di tropis: ~5-15% (literatur)
    RH_UNCERTAINTY = [5, 10, 15]

    rows = []
    for _, cr in critical_df.iterrows():
        obs_no = cr['No']
        dm_base = cr['Δm_Tel_baseline']

        # Cari sensitivity data
        obs_sens = sensitivity_df[sensitivity_df['No'] == obs_no]

        for unc in RH_UNCERTAINTY:
            # Δm at RH-uncertainty
            dm_low = obs_sens[obs_sens['ΔRH'] == -unc]
            dm_high = obs_sens[obs_sens['ΔRH'] == unc]

            dm_low_val = dm_low['Δm_Tel'].values[0] if len(dm_low) > 0 else dm_base
            dm_high_val = dm_high['Δm_Tel'].values[0] if len(dm_high) > 0 else dm_base

            error_bar = (dm_low_val - dm_high_val) / 2.0
            covers_zero = (dm_low_val >= 0) or (dm_high_val >= 0)

            rows.append({
                'No': obs_no,
                'Lokasi': cr['Lokasi'],
                'Obs': cr['Obs'],
                'Tipe': cr['Tipe'],
                'Δm_baseline': dm_base,
                'RH_uncertainty (±pp)': unc,
                'Δm_low_RH': dm_low_val,
                'Δm_high_RH': dm_high_val,
                'Error_bar (±mag)': abs(error_bar),
                'Mencakup_Δm=0': 'Ya' if covers_zero else 'Tidak',
            })

    result = pd.DataFrame(rows)

    # Print ringkasan
    for unc in RH_UNCERTAINTY:
        sub = result[result['RH_uncertainty (±pp)'] == unc]
        fn_sub = sub[sub['Tipe'] == 'FN']
        n_covers = sum(fn_sub['Mencakup_Δm=0'] == 'Ya')
        print(f"\n  Ketidakpastian RH ±{unc}pp:")
        print(f"    FN yang error bar mencakup Δm=0: {n_covers}/{len(fn_sub)}")
        print(f"    → {n_covers/len(fn_sub)*100:.0f}% FN konsisten dengan observasi "
              f"dalam batas ketidakpastian" if len(fn_sub) > 0 else "")

    return result


# ═══════════════════════════════════════════════════════════════════
# OUTPUT: EXCEL
# ═══════════════════════════════════════════════════════════════════

def save_results(kv_df, sensitivity_df, critical_df, decomp_df,
                 event_df, error_bar_df, filepath):
    """Simpan semua hasil ke Excel."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    sty = {
        'hdr_font': Font(name='Arial', bold=True, size=10, color='FFFFFF'),
        'hdr_fill': PatternFill('solid', fgColor='1F4E79'),
        'data_font': Font(name='Arial', size=10),
        'center': Alignment(horizontal='center', vertical='center'),
        'left': Alignment(horizontal='left', vertical='center'),
        'border': Border(
            left=Side('thin', 'B0B0B0'), right=Side('thin', 'B0B0B0'),
            top=Side('thin', 'B0B0B0'), bottom=Side('thin', 'B0B0B0')),
        'fn_fill': PatternFill('solid', fgColor='FFC7CE'),
        'tn_fill': PatternFill('solid', fgColor='C6EFCE'),
        'highlight': PatternFill('solid', fgColor='FFEB9C'),
    }

    def write_df_to_sheet(ws, df, sheet_name, highlight_col=None, highlight_val=None):
        ws.title = sheet_name
        headers = list(df.columns)
        for ci, h in enumerate(headers, 1):
            c = ws.cell(row=1, column=ci, value=h)
            c.font = sty['hdr_font']
            c.fill = sty['hdr_fill']
            c.alignment = sty['center']
            c.border = sty['border']

        for ri, (_, row) in enumerate(df.iterrows(), 2):
            for ci, col in enumerate(headers, 1):
                val = row[col]
                if isinstance(val, float) and not math.isnan(val):
                    if abs(val) > 1e6:
                        val = f"{val:.4e}"
                    elif abs(val) < 0.001 and val != 0:
                        val = f"{val:.6f}"
                    else:
                        val = round(val, 4)
                c = ws.cell(row=ri, column=ci, value=val)
                c.font = sty['data_font']
                c.alignment = sty['center']
                c.border = sty['border']

                # Highlight FN rows
                if 'Tipe' in headers:
                    tipe_ci = headers.index('Tipe') + 1
                    tipe_val = ws.cell(row=ri, column=tipe_ci).value
                    if tipe_val == 'FN':
                        c.fill = sty['fn_fill']

        for ci in range(1, len(headers) + 1):
            max_len = max(len(str(headers[ci-1])),
                         max((len(str(ws.cell(row=r, column=ci).value or ''))
                              for r in range(2, min(len(df)+2, 50))), default=8))
            ws.column_dimensions[get_column_letter(ci)].width = min(max_len + 2, 25)
        ws.freeze_panes = 'A2'

    # Sheet 1: Korelasi k_V
    ws1 = wb.active
    write_df_to_sheet(ws1, kv_df, "4a Korelasi kV")

    # Sheet 2: Sensitivitas RH (pivot: satu baris per observasi)
    pivot_rows = []
    for obs_no in sorted(sensitivity_df['No'].unique()):
        obs_data = sensitivity_df[sensitivity_df['No'] == obs_no]
        base_row = obs_data[obs_data['ΔRH'] == 0]
        if len(base_row) == 0:
            continue
        base = base_row.iloc[0]
        prow = {
            'No': obs_no,
            'Lokasi': base['Lokasi'],
            'Obs': base['Obs'],
            'Tipe': base['Tipe'],
            'RH_base': base['RH_baseline'],
            'k_V_base': base['k_V'],
        }
        for delta in RH_DELTAS:
            d = obs_data[obs_data['ΔRH'] == delta]
            if len(d) > 0:
                prow[f'Δm_Tel(ΔRH={delta:+d})'] = round(d.iloc[0]['Δm_Tel'], 3)
                prow[f'k_V(ΔRH={delta:+d})'] = round(d.iloc[0]['k_V'], 4)
        pivot_rows.append(prow)

    ws2 = wb.create_sheet()
    write_df_to_sheet(ws2, pd.DataFrame(pivot_rows), "4b Sensitivitas RH")

    # Sheet 3: RH Kritis
    ws3 = wb.create_sheet()
    write_df_to_sheet(ws3, critical_df, "4b RH Kritis")

    # Sheet 4: Dekomposisi Error
    ws4 = wb.create_sheet()
    write_df_to_sheet(ws4, decomp_df, "4c Dekomposisi Error")

    # Sheet 5: Per-Event
    ws5 = wb.create_sheet()
    write_df_to_sheet(ws5, event_df, "4d Per-Event")

    # Sheet 6: Error Bar
    ws6 = wb.create_sheet()
    write_df_to_sheet(ws6, error_bar_df, "5c Error Bar")

    # Sheet 7: Sensitivitas Detail (raw data)
    ws7 = wb.create_sheet()
    write_df_to_sheet(ws7, sensitivity_df, "Data Detail Sensitivitas")

    # Save
    os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
    wb.save(filepath)
    print(f"\n  ✓ Excel disimpan: {filepath}")


# ═══════════════════════════════════════════════════════════════════
# OUTPUT: PLOT
# ═══════════════════════════════════════════════════════════════════

def plot_sensitivity(sensitivity_df: pd.DataFrame, critical_df: pd.DataFrame,
                     filepath: str):
    """Plot sensitivitas Δm vs ΔRH untuk observasi FN."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker
    except ImportError:
        print("  [!] matplotlib tidak tersedia.")
        return

    fn_data = sensitivity_df[sensitivity_df['Tipe'] == 'FN']
    if len(fn_data) == 0:
        print("  [!] Tidak ada data FN untuk diplot.")
        return

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    # ── Plot 1: Δm_Tel vs ΔRH untuk setiap FN ──
    ax1 = axes[0]
    fn_obs = sorted(fn_data['No'].unique())
    colors = plt.cm.tab10(range(len(fn_obs)))

    for i, obs_no in enumerate(fn_obs):
        obs_data = fn_data[fn_data['No'] == obs_no].sort_values('ΔRH')
        label = f"#{obs_no} {obs_data.iloc[0]['Lokasi'][:20]}"
        ax1.plot(obs_data['ΔRH'], obs_data['Δm_Tel'],
                 marker='o', markersize=5, color=colors[i],
                 linewidth=2, label=label)

    ax1.axhline(y=0, color='green', linewidth=2, linestyle='--',
                label='Threshold (Δm=0)', alpha=0.8)
    ax1.axvline(x=0, color='gray', linewidth=1, linestyle=':', alpha=0.5)

    ax1.set_xlabel('Perubahan RH (pp)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Δm Teleskop (mag)', fontsize=12, fontweight='bold')
    ax1.set_title('Sensitivitas Δm terhadap Perubahan RH\n(Observasi False Negative)',
                  fontsize=13, fontweight='bold')
    ax1.legend(fontsize=8, loc='best')
    ax1.grid(True, alpha=0.3)

    # ── Plot 2: k_V vs Δm untuk semua observasi ──
    ax2 = axes[1]
    all_base = sensitivity_df[sensitivity_df['ΔRH'] == 0]
    tn = all_base[all_base['Tipe'] == 'TN']
    fn = all_base[all_base['Tipe'] == 'FN']

    ax2.scatter(tn['k_V'], tn['Δm_Tel'], c='blue', s=50, alpha=0.7,
                label=f'TN (n={len(tn)})', edgecolors='black', linewidths=0.5)
    ax2.scatter(fn['k_V'], fn['Δm_Tel'], c='red', s=80, alpha=0.9,
                label=f'FN (n={len(fn)})', edgecolors='black', linewidths=0.5,
                marker='*', zorder=5)

    ax2.axhline(y=0, color='green', linewidth=2, linestyle='--', alpha=0.8)
    ax2.set_xlabel('Koefisien Ekstingsi k_V', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Δm Teleskop (mag)', fontsize=12, fontweight='bold')
    ax2.set_title('Korelasi k_V dengan Δm\n(Semua Observasi)',
                  fontsize=13, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✓ Plot disimpan: {filepath}")


def plot_decomposition(decomp_df: pd.DataFrame, filepath: str):
    """Plot dekomposisi kontribusi error."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        return

    if len(decomp_df) == 0:
        return

    fig, ax = plt.subplots(figsize=(12, 6))

    labels = [f"#{int(r['No'])} {r['Lokasi'][:18]}" for _, r in decomp_df.iterrows()]
    x = range(len(labels))
    w = 0.25

    bars_L = [r['Δm_dari_L (k_V→Kastner)'] for _, r in decomp_df.iterrows()]
    bars_B = [r['Δm_dari_B (k_V→Schaefer)'] for _, r in decomp_df.iterrows()]
    bars_I = [r['Δm_interaksi'] for _, r in decomp_df.iterrows()]

    ax.bar([i - w for i in x], bars_L, w, label='Luminansi (k_V→Kastner)',
           color='#E74C3C', edgecolor='black', linewidth=0.5)
    ax.bar(x, bars_B, w, label='Sky Brightness (k_V→Schaefer)',
           color='#3498DB', edgecolor='black', linewidth=0.5)
    ax.bar([i + w for i in x], bars_I, w, label='Interaksi',
           color='#95A5A6', edgecolor='black', linewidth=0.5)

    ax.set_xlabel('Observasi False Negative', fontsize=12, fontweight='bold')
    ax.set_ylabel('Kontribusi ke Δ(Δm) [mag]', fontsize=12, fontweight='bold')
    ax.set_title('Dekomposisi Perubahan Δm saat RH Dikurangi 20pp\n'
                 'Kontribusi: Luminansi Hilal vs Sky Brightness vs Interaksi',
                 fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha='right', fontsize=9)
    ax.legend(fontsize=10)
    ax.grid(True, axis='y', alpha=0.3)
    ax.axhline(y=0, color='black', linewidth=0.5)

    plt.tight_layout()
    fig.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✓ Plot dekomposisi disimpan: {filepath}")


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    print("\n" + "█" * 70)
    print("  ANALISIS DIAGNOSTIK MODEL CRUMEY (2014)")
    print("  Tahap 4a-4d & 5c")
    print("█" * 70)

    # Baca input
    if not os.path.exists(INPUT_XLSX):
        print(f"\n  [!] File tidak ditemukan: {INPUT_XLSX}")
        print("  Jalankan batch_validation_crumey.py terlebih dahulu.")
        return

    print(f"\n  Membaca: {INPUT_XLSX}")
    df = pd.read_excel(INPUT_XLSX, sheet_name="Hasil Observasi")
    print(f"  {len(df)} observasi dimuat.\n")

    # ── Tahap 4a ──
    kv_df = analyze_kv_correlation(df)

    # ── Tahap 4b ──
    sensitivity_df, critical_df = analyze_rh_sensitivity(df)

    # ── Tahap 4c ──
    decomp_df = analyze_error_decomposition(df)

    # ── Tahap 4d ──
    event_df = analyze_inter_location(df)

    # ── Tahap 5c ──
    error_bar_df = analyze_error_bars(sensitivity_df, critical_df)

    # ── Ringkasan Akhir ──
    print("\n" + "█" * 70)
    print("  RINGKASAN TEMUAN DIAGNOSTIK")
    print("█" * 70)

    fn_critical = critical_df[critical_df['Tipe'] == 'FN']
    n_fn = len(fn_critical)
    n_reachable = sum(1 for _, r in fn_critical.iterrows()
                      if isinstance(r['Butuh_ΔRH'], (int, float)) and r['Butuh_ΔRH'] >= -30)

    print(f"\n  Total FN (False Negative)     : {n_fn}")
    print(f"  FN yg bisa diperbaiki ΔRH≤30pp: {n_reachable}/{n_fn}")

    if len(decomp_df) > 0:
        mean_L = decomp_df['Kontribusi_L (%)'].mean()
        mean_B = decomp_df['Kontribusi_B (%)'].mean()
        print(f"\n  Kontribusi rata-rata ke error (saat ΔRH=-20pp):")
        print(f"    Luminansi hilal (Kastner) : {mean_L:.1f}%")
        print(f"    Sky brightness (Schaefer) : {mean_B:.1f}%")
        dominant = "Luminansi (Kastner)" if mean_L > mean_B else "Sky Brightness (Schaefer)"
        print(f"    → Faktor dominan: {dominant}")

    # ── Simpan ──
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, 'output')

    excel_path = os.path.join(output_dir, "Analisis_Diagnostik_Crumey.xlsx")
    save_results(kv_df, sensitivity_df, critical_df, decomp_df,
                 event_df, error_bar_df, excel_path)

    plot_path = os.path.join(output_dir, "Sensitivitas_RH_dan_kV.png")
    plot_sensitivity(sensitivity_df, critical_df, plot_path)

    decomp_plot_path = os.path.join(output_dir, "Dekomposisi_Error.png")
    plot_decomposition(decomp_df, decomp_plot_path)

    print(f"\n{'█' * 70}")
    print("  ANALISIS SELESAI")
    print(f"{'█' * 70}")
    print(f"  Excel : {excel_path}")
    print(f"  Plot 1: {plot_path}")
    print(f"  Plot 2: {decomp_plot_path}")
    print(f"{'█' * 70}\n")


if __name__ == "__main__":
    main()