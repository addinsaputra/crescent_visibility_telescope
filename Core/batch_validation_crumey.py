#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════════════
VALIDASI MODEL CRUMEY (2014) vs DATA OBSERVASI HILAL INDONESIA
══════════════════════════════════════════════════════════════════════

Menjalankan model visibilitas hilal pada 29 data observasi rukyatul
hilal dari lokasi-lokasi BMKG Indonesia, lalu mengevaluasi performa
model sebagai binary classifier (terlihat / tidak terlihat).

Fitur:
  1. Batch processing 29 observasi dengan F referensi
  2. F-scan ANALITIK — hanya satu kali model run per observasi
     (delta_m(F) = delta_m(F_ref) + 2.5 × log₁₀(F_ref / F))
  3. Confusion matrix untuk setiap F
  4. Cari F optimal yang memaksimalkan akurasi
  5. Output Excel dengan format rapi + grafik opsional

CARA PAKAI:
  Letakkan script ini di direktori Core/ bersama modul-modul lainnya,
  lalu jalankan:
      python batch_validation_crumey.py

PRASYARAT:
  - Koneksi internet (untuk ERA5 API)
  - Semua modul Core/ sudah terinstall dan berfungsi
  - File de440s.bsp ada di direktori data-hisab/

Author: Pipeline validasi untuk skripsi hilal
Referensi: Crumey, A. (2014), MNRAS 442, 2600-2619
══════════════════════════════════════════════════════════════════════
"""

import math
import os
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple, Optional

# Pastikan Core/ di PATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core_crescent_visibility import (
    HilalVisibilityCalculator,
    tentukan_timezone_indonesia,
)


# ═══════════════════════════════════════════════════════════════════
# KONFIGURASI GLOBAL
# ═══════════════════════════════════════════════════════════════════

# --- Field factor referensi (untuk satu kali model run) ---
F_NAKED_REF = 2.0       # naked-eye reference
FIELD_FACTOR_REF = 2.0   # telescope reference

# --- Parameter teleskop default BMKG ---
TEL_PARAMS = dict(
    aperture=66.0,              # mm (refraktor BMKG tipikal)
    magnification=50.0,         # pembesaran
    transmission=0.95,          # transmisi per permukaan
    n_surfaces=6,               # jumlah permukaan optik
    central_obstruction=0.0,    # refraktor → 0
    observer_age=22.0,          # usia pengamat tipikal
    seeing=3.0,                 # arcsec
    field_factor=FIELD_FACTOR_REF,
)

# --- F-scan range ---
F_SCAN_MIN = 0.5
F_SCAN_MAX = 5.0
F_SCAN_STEP = 0.1

# --- Mode perhitungan ---
CALC_MODE = "optimal"       # "sunset" atau "optimal"
SUMBER_ATMOSFER = "era5"    # "era5", "merra2", "manual"

# --- Interval loop optimal ---
INTERVAL_MENIT = 1
MIN_MOON_ALT = 2.0
START_DELAY_MENIT = 1


# ═══════════════════════════════════════════════════════════════════
# DATA 29 OBSERVASI
# ═══════════════════════════════════════════════════════════════════
# Format per entry:
#   no, tanggal (YYYY-MM-DD), nama lokasi,
#   lat, lon, elv, adm4_code,
#   bulan_hijri, tahun_hijri,
#   bias_t, bias_rh,
#   observed (True=Y, False=N)

OBSERVATIONS = [
    # ── Muharram 1444 (29 Juli 2022) ─────────────────────────────
    ( 1, "2022-07-29", "Observatorium UIN Walisongo",
      -6.99167, 110.34806, 89.0,  "33.74.15.1010",
       1, 1444,  -1, 2,  False),
    ( 2, "2022-07-29", "Kebutuhjurang, Banjarnegara",
      -7.480125, 109.677931, 496.0, "33.04.20.2005",
       1, 1444,   0, 0,  False),
    ( 3, "2022-07-29", "Tower Hilal Sulamu, Kupang",
      -10.14333, 123.62667, 10.42, "53.01.07.2001",
       1, 1444,  -1, -2,  True),
    ( 4, "2022-07-29", "Mina Tanjung, Mataram",
      -8.346986, 116.149, 6.0, "52.08.01.2001",
       1, 1444,  -1, 2,  False),
    ( 5, "2022-07-29", "Tower Hilal Tgk.Chik, Aceh",
       5.46667, 95.24233, 11.65, "11.06.02.2001",
       1, 1444,  -1, 4,  False),
    ( 6, "2022-07-29", "Tower Hilal Marana, Donggala",
      -0.57861, 119.79070, 17.49, "72.03.10.2007",
       1, 1444,  -4, 10,  False),
    ( 7, "2022-07-29", "POB Condrodipo, Gresik",
      -7.16967, 112.61733, 61.0, "35.25.14.2002",
       1, 1444,   0, -4,  False),
    ( 8, "2022-07-29", "Tower Hilal Ternate",
      -0.79983, 127.29483, 33.61, "82.71.01.1005",
       1, 1444,  -1, 2,  False),

    # ── Ramadhan 1444 (22 Maret 2023) ────────────────────────────
    ( 9, "2023-03-22", "Observatorium UIN Walisongo",
      -6.99167, 110.34806, 89.0, "33.74.15.1010",
       9, 1444,  -1, 2,  False),
    (10, "2023-03-22", "POB Pedalen, Kebumen",
      -7.731322, 109.390878, 9.0, "33.05.01.2001",
       9, 1444,   0, 0,  False),
    (11, "2023-03-22", "Loang Baloq, Mataram",
      -8.60408, 116.07440, 5.0, "52.71.04.1002",
       9, 1444,  -1, 2,  True),
    (12, "2023-03-22", "Tower Hilal Marana, Donggala",
      -0.57861, 119.79070, 17.49, "72.03.10.2007",
       9, 1444,  -4, 10,  True),
    (13, "2023-03-22", "Tower Hilal Tgk.Chik, Aceh",
       5.46667, 95.24233, 11.65, "11.06.02.2001",
       9, 1444,  -1, 4,  True),
    (14, "2023-03-22", "Tower Hilal Meras, Manado",
       1.48033, 124.83367, 15.14, "71.71.06.1005",
       9, 1444,  -1, 4,  False),
    (15, "2023-03-22", "POB Cibeas, Sukabumi",
      -7.07400, 106.53133, 114.0, "32.02.02.2003",
       9, 1444,   0, -2,  False),
    (16, "2023-03-22", "Gedung BMKG Kupang",
      -10.15278, 123.60833, 40.0, "53.71.06.1007",
       9, 1444,  -1, -2,  False),

    # ── Syawal 1445 (9 April 2024) ───────────────────────────────
    (17, "2024-04-09", "Observatorium UIN Walisongo",
      -6.99167, 110.34806, 89.0, "33.74.15.1010",
      10, 1445,  -1, 2,  False),
    (18, "2024-04-09", "POB Pedalen, Kebumen",
      -7.731322, 109.390878, 9.0, "33.05.01.2001",
      10, 1445,   0, 0,  False),
    (19, "2024-04-09", "Tower Hilal Meras, Manado",
       1.48033, 124.83367, 15.14, "71.71.06.1005",
      10, 1445,  -1, 4,  True),
    (20, "2024-04-09", "Loang Baloq, Mataram",
      -8.60408, 116.07440, 5.0, "52.71.04.1002",
      10, 1445,  -1, 2,  False),
    (21, "2024-04-09", "Tower Hilal Tgk.Chik, Aceh",
       5.46667, 95.24233, 11.65, "11.06.02.2001",
      10, 1445,  -1, 4,  False),
    (22, "2024-04-09", "Gedung BMKG Kupang",
      -10.15278, 123.60833, 40.0, "53.71.06.1007",
      10, 1445,  -1, -2,  False),
    (23, "2024-04-09", "Tower Hilal Ternate",
      -0.79983, 127.29483, 33.61, "82.71.01.1005",
      10, 1445,  -1, 2,  False),

    # ── Rabiul Akhir 1446 (3 Oktober 2024) ───────────────────────
    (24, "2024-10-03", "Observatorium UIN Walisongo",
      -6.99167, 110.34806, 89.0, "33.74.15.1010",
       4, 1446,  -1, 2,  False),
    (25, "2024-10-03", "Kebutuhjurang, Banjarnegara",
      -7.480125, 109.677931, 496.0, "33.04.20.2005",
       4, 1446,   0, 0,  False),
    (26, "2024-10-03", "Tower Hilal Meras, Manado",
       1.48033, 124.83367, 15.14, "71.71.06.1005",
       4, 1446,  -1, 4,  True),
    (27, "2024-10-03", "Loang Baloq, Mataram",
      -8.60408, 116.07440, 5.0, "52.71.04.1002",
       4, 1446,  -1, 2,  False),
    (28, "2024-10-03", "Tower Hilal Marana, Donggala",
      -0.57861, 119.79070, 17.49, "72.03.10.2007",
       4, 1446,  -4, 10,  False),
    (29, "2024-10-03", "Tower Hilal Ternate",
      -0.79983, 127.29483, 33.61, "82.71.01.1005",
       4, 1446,  -1, 2,  False),
]


# ═══════════════════════════════════════════════════════════════════
# HELPER: PARSING & ANALISIS
# ═══════════════════════════════════════════════════════════════════

def parse_obs(entry: tuple) -> dict:
    """Parse satu entry tuple menjadi dictionary."""
    return {
        'no': entry[0],
        'tanggal': entry[1],
        'nama': entry[2],
        'lat': entry[3],
        'lon': entry[4],
        'elv': entry[5],
        'adm4': entry[6],
        'bulan_hijri': entry[7],
        'tahun_hijri': entry[8],
        'bias_t': entry[9],
        'bias_rh': entry[10],
        'observed': entry[11],  # True = Y, False = N
    }


def delta_m_at_F(delta_m_ref: float, F_ref: float, F: float) -> float:
    """Hitung delta_m pada field factor F dari delta_m referensi.

    Karena F hanya mengalikan threshold secara linier:
        C_th(F) = F × C_base
    maka:
        delta_m(F) = delta_m(F_ref) + 2.5 × log₁₀(F_ref / F)

    Berlaku untuk semua kasus termasuk fallback C_obj ≤ 0.
    """
    if delta_m_ref <= -90:  # sentinel value (-99)
        return delta_m_ref
    if F <= 0 or F_ref <= 0:
        return delta_m_ref
    return delta_m_ref + 2.5 * math.log10(F_ref / F)


def confusion_matrix(obs_list: List[bool], pred_list: List[bool]) -> dict:
    """Hitung confusion matrix dan metrik turunan."""
    n = len(obs_list)
    tp = sum(1 for o, p in zip(obs_list, pred_list) if o and p)
    tn = sum(1 for o, p in zip(obs_list, pred_list) if not o and not p)
    fp = sum(1 for o, p in zip(obs_list, pred_list) if not o and p)
    fn = sum(1 for o, p in zip(obs_list, pred_list) if o and not p)

    accuracy = (tp + tn) / n if n > 0 else 0
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0  # recall
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0

    # F1 score
    if precision + sensitivity > 0:
        f1 = 2 * precision * sensitivity / (precision + sensitivity)
    else:
        f1 = 0

    return {
        'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn,
        'n': n,
        'accuracy': accuracy,
        'sensitivity': sensitivity,
        'specificity': specificity,
        'precision': precision,
        'f1': f1,
    }


def f_scan(results: List[dict], F_ref: float,
           f_min: float = 0.5, f_max: float = 5.0, f_step: float = 0.1,
           key: str = 'delta_m_tel_opt') -> List[dict]:
    """Scan field factor dan hitung metrik klasifikasi pada setiap F.

    Parameters
    ----------
    results : list of dict
        Hasil batch processing, masing-masing berisi 'observed' dan key.
    F_ref : float
        Field factor referensi yang digunakan saat model run.
    key : str
        Key untuk delta_m yang akan di-scan.
        Gunakan 'delta_m_tel_opt' untuk telescope optimal,
        'delta_m_ne_opt' untuk naked-eye optimal,
        'delta_m_tel_sunset' untuk telescope at sunset.

    Returns
    -------
    list of dict
        Metrik klasifikasi untuk setiap F.
    """
    scan_results = []
    F_val = f_min
    while F_val <= f_max + 1e-9:
        obs_list = []
        pred_list = []
        for r in results:
            dm_ref = r.get(key, -99.0)
            dm = delta_m_at_F(dm_ref, F_ref, F_val)
            obs_list.append(r['observed'])
            pred_list.append(dm > 0)

        cm = confusion_matrix(obs_list, pred_list)
        cm['F'] = round(F_val, 2)
        scan_results.append(cm)
        F_val += f_step

    return scan_results


# ═══════════════════════════════════════════════════════════════════
# BATCH PROCESSING
# ═══════════════════════════════════════════════════════════════════

def run_single_observation(obs: dict, verbose: bool = True) -> dict:
    """Jalankan model untuk satu observasi.

    Returns
    -------
    dict : berisi semua hasil + metadata observasi
    """
    no = obs['no']
    nama = obs['nama']
    tanggal = obs['tanggal']
    tz = tentukan_timezone_indonesia(obs['lon'])

    if verbose:
        print(f"\n{'═' * 70}")
        print(f"[{no:2d}/29] {nama}")
        print(f"        Tanggal: {tanggal}  |  Hijri: {obs['bulan_hijri']}/{obs['tahun_hijri']}")
        print(f"        Lat={obs['lat']:.4f}  Lon={obs['lon']:.4f}  Elv={obs['elv']:.0f}m")
        print(f"        Observasi: {'TERLIHAT (Y)' if obs['observed'] else 'TIDAK TERLIHAT (N)'}")
        print(f"{'═' * 70}")

    try:
        calc = HilalVisibilityCalculator(
            nama_tempat=nama,
            lintang=obs['lat'],
            bujur=obs['lon'],
            elevasi=obs['elv'],
            timezone_str=tz,
            bulan_hijri=obs['bulan_hijri'],
            tahun_hijri=obs['tahun_hijri'],
            delta_day_offset=0,
            bias_t=obs['bias_t'],
            bias_rh=obs['bias_rh'],
            sumber_atmosfer=SUMBER_ATMOSFER,
            adm4_code=obs['adm4'],
        )

        hasil = calc.jalankan_perhitungan_lengkap(
            use_telescope=True,
            mode=CALC_MODE,
            F_naked=F_NAKED_REF,
            interval_menit=INTERVAL_MENIT,
            min_moon_alt=MIN_MOON_ALT,
            start_delay_menit=START_DELAY_MENIT,
            **TEL_PARAMS,
        )

        # Tanggal pengamatan yang dihitung model
        tgl_model = hasil.get('tanggal_pengamatan')
        if tgl_model:
            tgl_model_str = tgl_model.strftime('%Y-%m-%d')
        else:
            tgl_model_str = "?"

        # Verifikasi tanggal
        tgl_cocok = (tgl_model_str == tanggal)
        if not tgl_cocok and verbose:
            print(f"\n  ⚠ TANGGAL TIDAK COCOK: model={tgl_model_str}, "
                  f"observasi={tanggal}")

        # Kumpulkan hasil
        result = {
            # Metadata observasi
            'no': no,
            'nama': nama,
            'tanggal_obs': tanggal,
            'tanggal_model': tgl_model_str,
            'tanggal_cocok': tgl_cocok,
            'bulan_hijri': obs['bulan_hijri'],
            'tahun_hijri': obs['tahun_hijri'],
            'lat': obs['lat'],
            'lon': obs['lon'],
            'elv': obs['elv'],
            'observed': obs['observed'],
            'success': True,

            # Hasil saat sunset
            'sunset_local': str(hasil.get('sunset_local', '')),
            'moon_alt_sunset': hasil.get('moon_alt', 0),
            'sun_alt_sunset': hasil.get('sun_alt', 0),
            'elongation': hasil.get('elongation', 0),
            'phase_angle': hasil.get('phase_angle', 0),
            'sky_brightness_nl': hasil.get('sky_brightness_nl', 0),
            'luminansi_hilal_nl': hasil.get('luminansi_hilal_nl', 0),
            'k_v': hasil.get('k_v', 0),
            'rh': hasil.get('rh', 0),
            'temperature': hasil.get('temperature', 0),
            'delta_m_ne_sunset': hasil.get('delta_m_ne', -99.0),
            'delta_m_tel_sunset': hasil.get('delta_m_tel', -99.0),
            'telescope_gain_sunset': hasil.get('telescope_gain', 0),
        }

        # Hasil optimal (jika mode optimal)
        if CALC_MODE == "optimal":
            result.update({
                'delta_m_ne_opt': hasil.get('optimal_delta_m_ne', -99.0),
                'delta_m_tel_opt': hasil.get('optimal_delta_m_tel', -99.0),
                'optimal_time_ne': str(hasil.get('optimal_time_ne', '')),
                'optimal_time_tel': str(hasil.get('optimal_time_tel', '')),
                'optimal_moon_alt_ne': hasil.get('optimal_moon_alt_ne', 0),
                'optimal_moon_alt_tel': hasil.get('optimal_moon_alt_tel', 0),
                'telescope_gain_opt': hasil.get('optimal_telescope_gain', 0),
                'vis_duration_ne': hasil.get('visibility_duration_ne', 0),
                'vis_duration_tel': hasil.get('visibility_duration_tel', 0),
            })
        else:
            result.update({
                'delta_m_ne_opt': hasil.get('delta_m_ne', -99.0),
                'delta_m_tel_opt': hasil.get('delta_m_tel', -99.0),
                'optimal_time_ne': '',
                'optimal_time_tel': '',
                'optimal_moon_alt_ne': 0,
                'optimal_moon_alt_tel': 0,
                'telescope_gain_opt': 0,
                'vis_duration_ne': 0,
                'vis_duration_tel': 0,
            })

        # Ringkasan cepat
        dm_tel = result['delta_m_tel_opt']
        pred = "Y" if dm_tel > 0 else "N"
        obs_str = "Y" if obs['observed'] else "N"
        match = "✓" if (dm_tel > 0) == obs['observed'] else "✗"

        if verbose:
            print(f"\n  RINGKASAN: Δm_tel={dm_tel:+.3f}  "
                  f"Pred={pred}  Obs={obs_str}  {match}")

        return result

    except Exception as e:
        print(f"\n  ✗ ERROR pada obs #{no}: {e}")
        traceback.print_exc()
        return {
            'no': no,
            'nama': nama,
            'tanggal_obs': tanggal,
            'tanggal_model': '?',
            'tanggal_cocok': False,
            'bulan_hijri': obs['bulan_hijri'],
            'tahun_hijri': obs['tahun_hijri'],
            'lat': obs['lat'],
            'lon': obs['lon'],
            'elv': obs['elv'],
            'observed': obs['observed'],
            'success': False,
            'delta_m_ne_sunset': -99.0,
            'delta_m_tel_sunset': -99.0,
            'delta_m_ne_opt': -99.0,
            'delta_m_tel_opt': -99.0,
            'error': str(e),
        }


def run_batch() -> List[dict]:
    """Jalankan model untuk semua 29 observasi."""
    print("\n" + "█" * 70)
    print("  BATCH VALIDATION: Model Crumey (2014) vs Observasi Hilal")
    print("  29 data observasi × 4 event rukyat (2022–2024)")
    print(f"  Mode: {CALC_MODE}  |  Atmosfer: {SUMBER_ATMOSFER}")
    print(f"  F_naked_ref={F_NAKED_REF}  |  F_tel_ref={FIELD_FACTOR_REF}")
    print("█" * 70)

    results = []
    t_start = time.time()

    for entry in OBSERVATIONS:
        obs = parse_obs(entry)
        t_obs_start = time.time()
        result = run_single_observation(obs)
        elapsed = time.time() - t_obs_start
        result['elapsed_sec'] = elapsed
        results.append(result)
        print(f"  ⏱ Waktu: {elapsed:.1f} detik")

    total_time = time.time() - t_start
    n_success = sum(1 for r in results if r.get('success', False))
    print(f"\n{'═' * 70}")
    print(f"BATCH SELESAI: {n_success}/29 berhasil dalam {total_time:.0f} detik")
    print(f"{'═' * 70}")

    return results


# ═══════════════════════════════════════════════════════════════════
# ANALISIS DAN LAPORAN
# ═══════════════════════════════════════════════════════════════════

def print_results_table(results: List[dict]):
    """Cetak tabel ringkasan hasil."""
    print(f"\n{'═' * 100}")
    print("TABEL HASIL OBSERVASI (F_ref = {:.1f})".format(FIELD_FACTOR_REF))
    print(f"{'═' * 100}")
    hdr = (f"{'No':>3} {'Tanggal':>10} {'Lokasi':<35} "
           f"{'Obs':>3} {'Moon°':>6} {'Elong°':>6} "
           f"{'Δm_tel':>8} {'Pred':>4} {'Match':>5}")
    print(hdr)
    print("─" * 100)

    for r in results:
        if not r.get('success'):
            print(f"{r['no']:>3} {r['tanggal_obs']:>10} {r['nama']:<35} "
                  f"{'?' :>3} {'?':>6} {'?':>6} {'ERROR':>8} {'?':>4} {'?':>5}")
            continue

        obs_str = "Y" if r['observed'] else "N"
        dm = r.get('delta_m_tel_opt', -99)
        pred = "Y" if dm > 0 else "N"
        match = "✓" if pred == obs_str else "✗"
        moon_alt = r.get('moon_alt_sunset', 0)
        elong = r.get('elongation', 0)

        print(f"{r['no']:>3} {r['tanggal_obs']:>10} {r['nama']:<35} "
              f"{obs_str:>3} {moon_alt:>6.2f} {elong:>6.2f} "
              f"{dm:>+8.3f} {pred:>4} {match:>5}")

    print("─" * 100)


def print_confusion_matrix(cm: dict, label: str = ""):
    """Cetak confusion matrix yang rapi."""
    print(f"\n  Confusion Matrix {label}")
    print(f"  {'':15} {'Obs: Y':>10} {'Obs: N':>10} {'Total':>10}")
    print(f"  {'Pred: Y':<15} {cm['tp']:>10} {cm['fp']:>10} {cm['tp']+cm['fp']:>10}")
    print(f"  {'Pred: N':<15} {cm['fn']:>10} {cm['tn']:>10} {cm['fn']+cm['tn']:>10}")
    print(f"  {'Total':<15} {cm['tp']+cm['fn']:>10} {cm['fp']+cm['tn']:>10} {cm['n']:>10}")
    print()
    print(f"  Accuracy    : {cm['accuracy']:.1%}  ({cm['tp']+cm['tn']}/{cm['n']})")
    print(f"  Sensitivity : {cm['sensitivity']:.1%}  (TP/{cm['tp']+cm['fn']})")
    print(f"  Specificity : {cm['specificity']:.1%}  (TN/{cm['fp']+cm['tn']})")
    print(f"  Precision   : {cm['precision']:.1%}")
    print(f"  F1 Score    : {cm['f1']:.3f}")


def analyze_results(results: List[dict]):
    """Analisis lengkap: F-scan, confusion matrix, F optimal."""
    valid = [r for r in results if r.get('success', False)]
    if not valid:
        print("  [!] Tidak ada hasil valid untuk dianalisis.")
        return {}, []

    print(f"\n{'█' * 70}")
    print("  ANALISIS PERFORMA MODEL")
    print(f"{'█' * 70}")
    print(f"\n  Observasi valid : {len(valid)}/29")
    print(f"  Observasi Y     : {sum(1 for r in valid if r['observed'])}")
    print(f"  Observasi N     : {sum(1 for r in valid if not r['observed'])}")

    # ── F-scan untuk teleskop optimal ──
    print(f"\n{'─' * 70}")
    print("  F-SCAN TELESKOP (mode: optimal)")
    print(f"{'─' * 70}")

    scan = f_scan(valid, F_ref=FIELD_FACTOR_REF,
                  f_min=F_SCAN_MIN, f_max=F_SCAN_MAX, f_step=F_SCAN_STEP,
                  key='delta_m_tel_opt')

    # Cari F optimal (akurasi maksimum)
    best = max(scan, key=lambda x: (x['accuracy'], x['f1']))
    best_F = best['F']

    print(f"\n  {'F':>5} {'Acc':>7} {'Sens':>7} {'Spec':>7} {'Prec':>7} "
          f"{'F1':>7} {'TP':>4} {'TN':>4} {'FP':>4} {'FN':>4}")
    print(f"  {'─'*67}")

    for s in scan:
        marker = " ◄" if s['F'] == best_F else ""
        # Tampilkan semua yang akurasinya di atas 70% atau kelipatan 0.5
        show = (s['accuracy'] >= 0.7 or
                abs(s['F'] % 0.5) < 0.01 or
                s['F'] == best_F or
                abs(s['F'] - F_NAKED_REF) < 0.01 or
                abs(s['F'] - FIELD_FACTOR_REF) < 0.01)
        if show:
            print(f"  {s['F']:>5.1f} {s['accuracy']:>7.1%} {s['sensitivity']:>7.1%} "
                  f"{s['specificity']:>7.1%} {s['precision']:>7.1%} "
                  f"{s['f1']:>7.3f} {s['tp']:>4} {s['tn']:>4} "
                  f"{s['fp']:>4} {s['fn']:>4}{marker}")

    # ── Confusion matrix pada beberapa F kunci ──
    print(f"\n{'─' * 70}")
    print("  CONFUSION MATRIX PADA F KUNCI")
    print(f"{'─' * 70}")

    F_keys = sorted(set([1.0, 1.5, 2.0, 2.5, 3.0, best_F]))
    for F_val in F_keys:
        obs_list = [r['observed'] for r in valid]
        pred_list = [
            delta_m_at_F(r['delta_m_tel_opt'], FIELD_FACTOR_REF, F_val) > 0
            for r in valid
        ]
        cm = confusion_matrix(obs_list, pred_list)
        label = f"(F = {F_val:.1f})"
        if F_val == best_F:
            label += " ★ OPTIMAL"
        print_confusion_matrix(cm, label)

    # ── Ringkasan akhir ──
    print(f"\n{'█' * 70}")
    print("  KESIMPULAN")
    print(f"{'█' * 70}")
    print(f"\n  F optimal (teleskop)  : {best_F:.1f}")
    print(f"  Akurasi pada F={best_F:.1f}   : {best['accuracy']:.1%}")
    print(f"  Sensitivity           : {best['sensitivity']:.1%}")
    print(f"  Specificity           : {best['specificity']:.1%}")
    print(f"  F1 Score              : {best['f1']:.3f}")

    # Juga analisis untuk naked eye
    print(f"\n  --- Juga untuk referensi (Naked Eye) ---")
    scan_ne = f_scan(valid, F_ref=F_NAKED_REF,
                     f_min=F_SCAN_MIN, f_max=F_SCAN_MAX, f_step=F_SCAN_STEP,
                     key='delta_m_ne_opt')
    best_ne = max(scan_ne, key=lambda x: (x['accuracy'], x['f1']))
    print(f"  F optimal (naked eye) : {best_ne['F']:.1f}")
    print(f"  Akurasi pada F={best_ne['F']:.1f}   : {best_ne['accuracy']:.1%}")

    return {'best_F_tel': best_F, 'best_cm_tel': best,
            'best_F_ne': best_ne['F'], 'best_cm_ne': best_ne,
            'scan_tel': scan, 'scan_ne': scan_ne}


# ═══════════════════════════════════════════════════════════════════
# EXCEL OUTPUT
# ═══════════════════════════════════════════════════════════════════

def save_to_excel(results: List[dict], analysis: dict, filepath: str):
    """Simpan semua hasil ke file Excel."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

    wb = Workbook()
    styles = {
        'hdr_font': Font(name='Arial', bold=True, size=11, color='FFFFFF'),
        'hdr_fill': PatternFill('solid', fgColor='1F4E79'),
        'data_font': Font(name='Arial', size=10),
        'bold_font': Font(name='Arial', size=10, bold=True),
        'center': Alignment(horizontal='center', vertical='center'),
        'left': Alignment(horizontal='left', vertical='center'),
        'green': PatternFill('solid', fgColor='C6EFCE'),
        'red': PatternFill('solid', fgColor='FFC7CE'),
        'yellow': PatternFill('solid', fgColor='FFEB9C'),
        'border': Border(
            left=Side('thin', 'B0B0B0'), right=Side('thin', 'B0B0B0'),
            top=Side('thin', 'B0B0B0'), bottom=Side('thin', 'B0B0B0')),
    }

    def write_header(ws, row, headers):
        for ci, h in enumerate(headers, 1):
            c = ws.cell(row=row, column=ci, value=h)
            c.font = styles['hdr_font']
            c.fill = styles['hdr_fill']
            c.alignment = styles['center']
            c.border = styles['border']

    # ═══ Sheet 1: Hasil Per Observasi ═══
    ws1 = wb.active
    ws1.title = "Hasil Observasi"
    ws1.sheet_properties.tabColor = '1F4E79'

    headers1 = [
        'No', 'Tanggal', 'Lokasi', 'Lat', 'Lon', 'Elv',
        'Bulan Hijri', 'Obs (Y/N)',
        'Moon Alt (°)', 'Elongasi (°)', 'Phase Angle (°)',
        'Sky Bright (nL)', 'Lum Hilal (nL)', 'k_V',
        'RH (%)', 'T (°C)',
        f'Δm NE (F={F_NAKED_REF})', f'Δm Tel (F={FIELD_FACTOR_REF})',
        'Δm NE Opt', 'Δm Tel Opt',
        'Tel Gain', 'Prediksi', 'Cocok?',
        'Sunset Lokal', 'Waktu Optimal Tel',
    ]
    write_header(ws1, 1, headers1)

    for i, r in enumerate(results, 2):
        obs_str = "Y" if r['observed'] else "N"
        dm_tel = r.get('delta_m_tel_opt', -99)
        pred = "Y" if dm_tel > 0 else "N"
        cocok = "✓" if pred == obs_str else "✗"

        row_data = [
            r['no'], r['tanggal_obs'], r['nama'],
            r.get('lat', 0), r.get('lon', 0), r.get('elv', 0),
            f"{r.get('bulan_hijri', 0)}/{r.get('tahun_hijri', 0)}",
            obs_str,
            round(r.get('moon_alt_sunset', 0), 4),
            round(r.get('elongation', 0), 4),
            round(r.get('phase_angle', 0), 4),
            f"{r.get('sky_brightness_nl', 0):.4e}",
            f"{r.get('luminansi_hilal_nl', 0):.4e}",
            round(r.get('k_v', 0), 4),
            round(r.get('rh', 0), 2),
            round(r.get('temperature', 0), 2),
            round(r.get('delta_m_ne_sunset', -99), 4),
            round(r.get('delta_m_tel_sunset', -99), 4),
            round(r.get('delta_m_ne_opt', -99), 4),
            round(dm_tel, 4),
            round(r.get('telescope_gain_opt', 0), 4),
            pred, cocok,
            r.get('sunset_local', ''),
            r.get('optimal_time_tel', ''),
        ]

        for ci, val in enumerate(row_data, 1):
            c = ws1.cell(row=i, column=ci, value=val)
            c.font = styles['data_font']
            c.alignment = styles['center'] if ci != 3 else styles['left']
            c.border = styles['border']

            # Warnai kolom "Cocok?"
            if ci == len(row_data) - 2:  # kolom "Cocok?"
                c.fill = styles['green'] if cocok == "✓" else styles['red']

    # Auto-width
    for col_idx in range(1, len(headers1) + 1):
        max_len = len(str(headers1[col_idx - 1]))
        for row_idx in range(2, len(results) + 2):
            val = ws1.cell(row=row_idx, column=col_idx).value
            if val:
                max_len = max(max_len, len(str(val)))
        from openpyxl.utils import get_column_letter
        ws1.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 2, 30)
    ws1.freeze_panes = 'A2'

    # ═══ Sheet 2: F-Scan Teleskop ═══
    ws2 = wb.create_sheet("F-Scan Teleskop")
    ws2.sheet_properties.tabColor = '548235'

    headers2 = ['F', 'Accuracy', 'Sensitivity', 'Specificity',
                'Precision', 'F1 Score', 'TP', 'TN', 'FP', 'FN']
    write_header(ws2, 1, headers2)

    scan_data = analysis.get('scan_tel', [])
    best_F = analysis.get('best_F_tel', 2.0)
    for i, s in enumerate(scan_data, 2):
        row = [
            s['F'],
            round(s['accuracy'], 4),
            round(s['sensitivity'], 4),
            round(s['specificity'], 4),
            round(s['precision'], 4),
            round(s['f1'], 4),
            s['tp'], s['tn'], s['fp'], s['fn'],
        ]
        for ci, val in enumerate(row, 1):
            c = ws2.cell(row=i, column=ci, value=val)
            c.font = styles['data_font']
            c.alignment = styles['center']
            c.border = styles['border']
            if abs(s['F'] - best_F) < 0.01:
                c.fill = styles['yellow']

    for ci in range(1, len(headers2) + 1):
        ws2.column_dimensions[get_column_letter(ci)].width = 14
    ws2.freeze_panes = 'A2'

    # ═══ Sheet 3: Ringkasan ═══
    ws3 = wb.create_sheet("Ringkasan")
    ws3.sheet_properties.tabColor = 'BF8F00'
    ws3.column_dimensions['A'].width = 35
    ws3.column_dimensions['B'].width = 25

    summary_data = [
        ("KONFIGURASI", ""),
        ("Mode Perhitungan", CALC_MODE),
        ("Sumber Atmosfer", SUMBER_ATMOSFER),
        ("F Naked Eye (referensi)", F_NAKED_REF),
        ("F Teleskop (referensi)", FIELD_FACTOR_REF),
        ("Aperture Teleskop (mm)", TEL_PARAMS['aperture']),
        ("Magnifikasi", TEL_PARAMS['magnification']),
        ("Transmisi/permukaan", TEL_PARAMS['transmission']),
        ("Jumlah permukaan", TEL_PARAMS['n_surfaces']),
        ("", ""),
        ("HASIL VALIDASI TELESKOP", ""),
        ("Total Observasi", len(results)),
        ("Observasi Berhasil", sum(1 for r in results if r.get('success'))),
        ("Observasi Y", sum(1 for r in results if r['observed'])),
        ("Observasi N", sum(1 for r in results if not r['observed'])),
        ("", ""),
        ("F Optimal", best_F),
    ]

    best_cm = analysis.get('best_cm_tel', {})
    if best_cm:
        summary_data += [
            (f"Akurasi (F={best_F})", f"{best_cm['accuracy']:.1%}"),
            (f"Sensitivity (F={best_F})", f"{best_cm['sensitivity']:.1%}"),
            (f"Specificity (F={best_F})", f"{best_cm['specificity']:.1%}"),
            (f"F1 Score (F={best_F})", f"{best_cm['f1']:.3f}"),
            (f"TP", best_cm['tp']),
            (f"TN", best_cm['tn']),
            (f"FP", best_cm['fp']),
            (f"FN", best_cm['fn']),
        ]

    for i, (label, val) in enumerate(summary_data, 1):
        cl = ws3.cell(row=i, column=1, value=label)
        cv = ws3.cell(row=i, column=2, value=val)
        if label and not val and val != 0:
            cl.font = styles['bold_font']
            cl.fill = styles['hdr_fill']
            cl.font = styles['hdr_font']
            cv.fill = styles['hdr_fill']
        else:
            cl.font = styles['data_font']
            cv.font = styles['data_font']
        cl.border = styles['border']
        cv.border = styles['border']

    # Save
    out_dir = os.path.dirname(filepath)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    wb.save(filepath)
    print(f"\n  ✓ Excel disimpan: {filepath}")


# ═══════════════════════════════════════════════════════════════════
# PLOT (OPSIONAL)
# ═══════════════════════════════════════════════════════════════════

def plot_f_scan(analysis: dict, filepath: str):
    """Plot accuracy vs F dan simpan sebagai gambar."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker
    except ImportError:
        print("  [!] matplotlib tidak tersedia. Plot dilewati.")
        return

    scan = analysis.get('scan_tel', [])
    if not scan:
        return

    F_vals = [s['F'] for s in scan]
    acc_vals = [s['accuracy'] * 100 for s in scan]
    sens_vals = [s['sensitivity'] * 100 for s in scan]
    spec_vals = [s['specificity'] * 100 for s in scan]
    f1_vals = [s['f1'] * 100 for s in scan]

    best_F = analysis.get('best_F_tel', 2.0)
    best_acc = max(acc_vals)

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(F_vals, acc_vals, 'b-', linewidth=2.5, label='Accuracy', zorder=5)
    ax.plot(F_vals, sens_vals, 'g--', linewidth=1.5, label='Sensitivity', alpha=0.8)
    ax.plot(F_vals, spec_vals, 'r--', linewidth=1.5, label='Specificity', alpha=0.8)
    ax.plot(F_vals, f1_vals, 'm:', linewidth=1.5, label='F1 Score', alpha=0.8)

    ax.axvline(x=best_F, color='orange', linewidth=1.5, linestyle='-.',
               label=f'F optimal = {best_F:.1f}', alpha=0.9)
    ax.scatter([best_F], [best_acc], color='orange', s=100, zorder=10,
               edgecolors='black', linewidths=1)

    ax.set_xlabel('Field Factor (F)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Metrik (%)', fontsize=13, fontweight='bold')
    ax.set_title('Performa Model Crumey (2014) vs Data Observasi Hilal\n'
                 'Akurasi Klasifikasi sebagai Fungsi Field Factor',
                 fontsize=14, fontweight='bold')

    ax.set_xlim(F_SCAN_MIN, F_SCAN_MAX)
    ax.set_ylim(0, 105)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(0.5))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(10))
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=11, framealpha=0.9)

    plt.tight_layout()
    os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
    fig.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✓ Plot disimpan: {filepath}")


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    """Entry point utama."""
    # 1. Batch run
    results = run_batch()

    # 2. Tampilkan tabel
    print_results_table(results)

    # 3. Analisis (F-scan, confusion matrix)
    analysis, *_ = analyze_results(results), None

    # 4. Simpan ke Excel
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, 'output')

    excel_path = os.path.join(output_dir,
        f"Validasi_Crumey_29obs_{SUMBER_ATMOSFER}_{CALC_MODE}.xlsx")
    save_to_excel(results, analysis, excel_path)

    # 5. Plot F-scan
    plot_path = os.path.join(output_dir,
        f"F_Scan_Crumey_29obs_{SUMBER_ATMOSFER}_{CALC_MODE}.png")
    plot_f_scan(analysis, plot_path)

    # 6. Ringkasan akhir
    print(f"\n{'█' * 70}")
    print("  VALIDASI SELESAI")
    print(f"{'█' * 70}")
    print(f"  Excel : {excel_path}")
    print(f"  Plot  : {plot_path}")
    print(f"{'█' * 70}\n")

    return results, analysis


if __name__ == "__main__":
    results, analysis = main()