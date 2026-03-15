"""
Modul Integrasi: Koreksi Teleskop (Schaefer) + Contrast Threshold (Crumey)
==========================================================================

Mengimplementasi prosedur lengkap readd.md langkah 1-8:
  1. Input mentah: B (sky brightness), L_t (luminansi hilal), A (area hilal)
  2. Hitung faktor teleskop (Schaefer): Ft, Fp, Fa, Fm, Fr
  3. Terapkan koreksi ke L_t dan B
  4. Konversi satuan: nL → cd/m², arcmin² → sr
  5. Area efektif retina: A_eff = A_sr × M²
  6. Kontras objek: C_obj = (L_t_cd − B_cd) / B_cd
  7. Threshold Crumey: C_th = crumey_threshold(A_eff, B_cd)
  8. Keputusan visibilitas: visible = (C_obj > C_th)

Modul ini menjembatani:
  - telescope_limit.py  (langkah 1-3, faktor koreksi optik Schaefer 1990)
  - crumey.py           (langkah 4-8, model contrast threshold Crumey 2014)

Author: Integrasi otomatis
"""

import math
from dataclasses import dataclass, field
from typing import Optional

# Import modul yang sudah ada
from telescope_limit import TelescopeVisibilityModel
from crumey import (
    nL_to_cd_m2,
    cd_m2_to_nL,
    arcmin2_to_sr,
    crumey_threshold,
)


# ── Dataclass untuk spesifikasi teleskop ──────────────────────────────────────

@dataclass
class TelescopeSpec:
    """
    Parameter teleskop untuk perhitungan visibilitas.
    
    Attributes
    ----------
    aperture_mm : float
        Diameter aperture / objektif teleskop (mm)
    magnification : float
        Perbesaran teleskop
    obstruction_mm : float
        Diameter obstruksi cermin sekunder (mm). 0 untuk refraktor.
    transmission_per_surface : float
        Transmisi per permukaan optik (0-1), default 0.95
    n_surfaces : int
        Jumlah permukaan optik (lensa/cermin), default 6
    observer_age : float
        Usia pengamat (tahun), default 22
    seeing_arcsec : float
        Ukuran seeing disk (arcsec), default 3.0
    field_factor : float
        Faktor konservatif kondisi lapangan (F_obs ≥ 1), default 2.4
        Digunakan: visible = (C_obj > field_factor × C_th)
    phi : float
        Faktor koreksi tambahan (cadangan, default 1.0)
    """
    aperture_mm: float = 100.0
    magnification: float = 50.0
    obstruction_mm: float = 0.0
    transmission_per_surface: float = 0.95
    n_surfaces: int = 6
    observer_age: float = 22.0
    seeing_arcsec: float = 3.0
    field_factor: float = 2.4
    phi: float = 1.0


# ── Fungsi luas sabit hilal ──────────────────────────────────────────────────

def crescent_area_arcmin2(elongation_deg: float, r_deg: float) -> float:
    """
    Menghitung luas area sabit hilal dalam arcmin².
    
    Menggunakan pendekatan geometri sabit (crescent):
    Luas ≈ 2 r² (elong_rad − sin(elong_rad) cos(elong_rad))
    dalam satuan derajat² lalu di-konversi ke arcmin².
    
    Parameters
    ----------
    elongation_deg : float
        Elongasi bulan-matahari (derajat). Untuk bulan sabit,
        elongasi ≈ phase angle dan menentukan ketebalan sabit.
    r_deg : float
        Semidiameter bulan (derajat), tipikal ~0.25°.
    
    Returns
    -------
    float
        Luas sabit dalam arcmin².
    """
    if elongation_deg <= 0 or r_deg <= 0:
        return 0.0
    
    elong_rad = math.radians(elongation_deg)
    
    # Luas sabit = 2 r² (θ − sin θ cos θ), di mana θ = elongasi
    # (Derivasi: selisih luas dua setengah lingkaran yang overlap)
    area_deg2 = 2.0 * (r_deg ** 2) * (elong_rad - math.sin(elong_rad) * math.cos(elong_rad))
    
    # Konversi derajat² → arcmin² (1 derajat = 60 arcmin, 1 deg² = 3600 arcmin²)
    area_arcmin2 = area_deg2 * 3600.0
    
    return max(area_arcmin2, 1e-10)  # Cegah nol


# ── Fungsi utama: visibility_margin ──────────────────────────────────────────

def visibility_margin(
    Lt_nL: float,
    B_nL: float,
    A_arcmin2: float,
    spec: Optional[TelescopeSpec] = None,
    use_abs_contrast: bool = True
) -> dict:
    """
    Menghitung visibility margin teleskop mengikuti prosedur readd.md (langkah 1-8).
    
    Pipeline:
      1. Input: Lt (nL), B (nL), A (arcmin²)
      2. Hitung faktor teleskop via TelescopeVisibilityModel (Schaefer)
      3. Terapkan koreksi: Lt_corr, B_corr
      4. Konversi: nL → cd/m², arcmin² → sr
      5. Area efektif: A_eff = A_sr × M²
      6. C_obj = (Lt_cd − B_cd) / B_cd
      7. C_th = crumey_threshold(A_eff, B_cd)
      8. margin = log10(C_obj / (field_factor × C_th))
    
    Parameters
    ----------
    Lt_nL : float
        Luminansi hilal (nanoLambert)
    B_nL : float
        Sky brightness (nanoLambert)
    A_arcmin2 : float
        Luas angular sabit hilal (arcmin²)
    spec : TelescopeSpec, optional
        Spesifikasi teleskop. Jika None, gunakan default.
    use_abs_contrast : bool
        Jika True, gunakan |C_obj| untuk perbandingan (hilal bisa
        lebih terang maupun lebih redup dari sky).
    
    Returns
    -------
    dict
        Dictionary berisi:
        - margin_tel: float — log10(C_obj / (F_obs × C_th)), >0 = detectable
        - C_obj: float — kontras objek (Weber contrast)
        - C_thr_tel: float — threshold contrast Crumey
        - Ba_cd_m2: float — background setelah koreksi (cd/m²)
        - Lt_cd_m2: float — luminansi hilal setelah koreksi (cd/m²)
        - A_eff_sr: float — area efektif (sr)
        - exit_pupil_mm: float — exit pupil teleskop (mm)
        - throughput_T: float — throughput total
        - factors: dict — semua faktor koreksi teleskop
        - visible: bool — apakah hilal terdeteksi
    """
    if spec is None:
        spec = TelescopeSpec()
    
    # ── Langkah 2: Hitung faktor-faktor teleskop (Schaefer) ──────────────
    model = TelescopeVisibilityModel()
    factors = model.calculate_factors(
        D=spec.aperture_mm,
        Ds=spec.obstruction_mm,
        M=spec.magnification,
        age=spec.observer_age,
        t1=spec.transmission_per_surface,
        n=spec.n_surfaces,
        theta=spec.seeing_arcsec
    )
    
    FB = factors["FB"]  # Faktor gabungan sky: Fb × Ft × Fp × Fa × Fm
    FI = factors["FI"]  # Faktor gabungan hilal: Fb × Ft × Fp × Fa × Fr
    
    # ── Langkah 3: Terapkan koreksi ke luminansi ─────────────────────────
    # Lt_corr = Lt_raw × FI  (extended source)
    # B_corr  = B_raw  × FB  (sky background, termasuk efek magnifikasi Fm)
    Lt_corr_nL = Lt_nL * FI
    B_corr_nL = B_nL * FB
    
    # ── Langkah 4: Konversi satuan ───────────────────────────────────────
    # nL → cd/m²
    Lt_cd = nL_to_cd_m2(Lt_corr_nL)
    B_cd = nL_to_cd_m2(B_corr_nL)
    
    # arcmin² → sr
    A_sr = arcmin2_to_sr(A_arcmin2)
    
    # ── Langkah 5: Area efektif retina ───────────────────────────────────
    # Magnifikasi memperbesar area sudut objek di retina
    A_eff = A_sr * (spec.magnification ** 2)
    
    # ── Langkah 6: Kontras objek (Weber contrast) ────────────────────────
    if B_cd <= 0:
        return {
            "margin_tel": float('-inf'),
            "C_obj": float('nan'),
            "C_thr_tel": float('nan'),
            "Ba_cd_m2": B_cd,
            "Lt_cd_m2": Lt_cd,
            "A_eff_sr": A_eff,
            "exit_pupil_mm": factors["exit_pupil"],
            "throughput_T": 1.0 / factors["Ft"],
            "factors": factors,
            "visible": False
        }
    
    C_obj = (Lt_cd - B_cd) / B_cd
    
    # ── Langkah 7: Threshold Crumey ──────────────────────────────────────
    C_th = crumey_threshold(A_eff, B_cd)
    
    # ── Langkah 8: Keputusan visibilitas ─────────────────────────────────
    C_compare = abs(C_obj) if use_abs_contrast else C_obj
    effective_threshold = spec.field_factor * C_th
    
    if C_compare > 0 and effective_threshold > 0:
        margin_tel = math.log10(C_compare / effective_threshold)
    elif C_compare <= 0:
        margin_tel = float('-inf')
    else:
        margin_tel = float('-inf')
    
    visible = margin_tel > 0
    
    # Throughput total = 1 / Ft (karena Ft = 1 / (T_total))
    throughput_T = 1.0 / factors["Ft"] if factors["Ft"] > 0 else 0.0
    
    return {
        "margin_tel": margin_tel,
        "C_obj": C_obj,
        "C_thr_tel": C_th,
        "Ba_cd_m2": B_cd,
        "Lt_cd_m2": Lt_cd,
        "A_eff_sr": A_eff,
        "exit_pupil_mm": factors["exit_pupil"],
        "throughput_T": throughput_T,
        "factors": factors,
        "visible": visible
    }


# ── Fungsi Praktis (Wrapper) ─────────────────────────────────────────────────

def calculate_crumey_telescope_visibility(
    B_sky_nl: float,
    L_hilal_nl: float,
    elongation_deg: float,
    moon_sd_deg: float,
    aperture: float = 100.0,
    magnification: float = 50.0,
    central_obstruction: float = 0.0,
    transmission: float = 0.95,
    n_surfaces: int = 6,
    age: float = 22.0,
    seeing: float = 3.0,
    field_factor: float = 2.4
) -> dict:
    """
    Fungsi praktis dan terpadu untuk menghitung visibilitas hilal dengan teleskop.
    Fungsi ini menyatukan perhitungan luas sabit, pembuatan spesifikasi teleskop,
    dan konversi satuan (cd/m² kembali ke nL) agar mudah dipanggil di program lain
    sebagai satu kesatuan yang utuh (mirip calculate_telescope_visibility versi lama).
    
    Parameters
    ----------
    B_sky_nl : float
        Kecerahan langit (nanoLamberts)
    L_hilal_nl : float
        Luminansi hilal (nanoLamberts)
    elongation_deg : float
        Elongasi bulan-matahari (derajat)
    moon_sd_deg : float
        Semidiameter bulan (derajat)
    aperture : float
        Diameter aperture teleskop (mm)
    magnification : float
        Perbesaran teleskop
    central_obstruction : float
        Diameter obstruksi cermin sekunder (mm)
    transmission : float
        Transmisi per permukaan optik
    n_surfaces : int
        Jumlah permukaan optik
    age : float
        Usia pengamat (tahun)
    seeing : float
        Ukuran seeing disk (arcsec)
    field_factor : float
        Faktor konservatif kondisi lapangan
        
    Returns
    -------
    dict
        Hasil komprehensif termasuk C_obj, margin_tel, visible, B_eff_nl, I_eff_nl
    """
    A_arcmin2 = crescent_area_arcmin2(elongation_deg, moon_sd_deg)
    spec = TelescopeSpec(
        aperture_mm=aperture,
        magnification=magnification,
        obstruction_mm=central_obstruction,
        transmission_per_surface=transmission,
        n_surfaces=n_surfaces,
        observer_age=age,
        seeing_arcsec=seeing,
        field_factor=field_factor
    )
    res = visibility_margin(L_hilal_nl, B_sky_nl, A_arcmin2, spec=spec)
    
    # Konversi cd/m² -> nL untuk kompatibilitas program yang ada
    res["B_eff_nl"] = cd_m2_to_nL(res["Ba_cd_m2"])
    res["I_eff_nl"] = cd_m2_to_nL(res["Lt_cd_m2"])
    
    return res


# ── Contoh penggunaan ────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 70)
    print("INTEGRASI: KOREKSI TELESKOP (SCHAEFER) + THRESHOLD (CRUMEY)")
    print("Prosedur readd.md langkah 1-8")
    print("=" * 70)
    
    # Contoh input (dari output program visibilitas hilal)
    Lt_nL = 4.2422e+06    # Luminansi hilal (nL)
    B_nL = 1.2114e+09       # Sky brightness (nL)
    elongation = 8.3914194444444     # Elongasi (derajat)
    r_deg = 0.2465833333333       # Semidiameter bulan (derajat)
    
    # Hitung luas sabit
    A_arcmin2 = crescent_area_arcmin2(elongation, r_deg)
    
    # Spesifikasi teleskop
    spec = TelescopeSpec(
        aperture_mm=100.0,
        magnification=50.0,
        obstruction_mm=0.0,         # Refraktor
        transmission_per_surface=0.95,
        n_surfaces=6,
        observer_age=22,
        seeing_arcsec=3.0,
        field_factor=2.4
    )
    
    print(f"\n[INPUT]")
    print(f"  Luminansi Hilal (Lt)  : {Lt_nL:.2f} nL")
    print(f"  Sky Brightness (B)    : {B_nL:.2f} nL")
    print(f"  Elongasi              : {elongation:.4f}°")
    print(f"  Semidiameter Bulan    : {r_deg:.6f}°")
    print(f"  Luas Sabit (A)        : {A_arcmin2:.4f} arcmin²")
    
    print(f"\n[TELESKOP]")
    print(f"  Aperture              : {spec.aperture_mm} mm")
    print(f"  Magnification         : {spec.magnification}x")
    print(f"  Obstruction           : {spec.obstruction_mm} mm")
    print(f"  Transmisi/permukaan   : {spec.transmission_per_surface}")
    print(f"  Jumlah permukaan      : {spec.n_surfaces}")
    print(f"  Usia pengamat         : {spec.observer_age} tahun")
    print(f"  Seeing                : {spec.seeing_arcsec} arcsec")
    print(f"  Field factor (F_obs)  : {spec.field_factor}")
    
    # Jalankan pipeline
    result = visibility_margin(Lt_nL, B_nL, A_arcmin2, spec=spec)
    
    print(f"\n[FAKTOR KOREKSI TELESKOP — Schaefer]")
    f = result["factors"]
    print(f"  Fb (Binokular)        : {f['Fb']:.4f}")
    print(f"  Ft (Transmisi)        : {f['Ft']:.4f}")
    print(f"  Fp (Pupil)            : {f['Fp']:.4f}")
    print(f"  Fa (Aperture)         : {f['Fa']:.6f}")
    print(f"  Fm (Magnifikasi)      : {f['Fm']:.6f}")
    print(f"  Fr (Resolusi)         : {f['Fr']:.4f}")
    print(f"  FB (sky gabungan)     : {f['FB']:.6e}")
    print(f"  FI (hilal gabungan)   : {f['FI']:.6e}")
    print(f"  Exit pupil            : {f['exit_pupil']:.2f} mm")
    print(f"  Throughput            : {result['throughput_T']:.4f}")
    
    print(f"\n[KONVERSI & KOREKSI]")
    print(f"  Lt terkoreksi (cd/m²) : {result['Lt_cd_m2']:.6e}")
    print(f"  B terkoreksi (cd/m²)  : {result['Ba_cd_m2']:.6e}")
    print(f"  A_eff (sr)            : {result['A_eff_sr']:.6e}")
    
    print(f"\n[VISIBILITAS — Crumey]")
    print(f"  C_obj (Weber contrast): {result['C_obj']:.6f}")
    print(f"  C_th  (threshold)     : {result['C_thr_tel']:.6f}")
    print(f"  Margin teleskop       : {result['margin_tel']:.4f}")
    print(f"  Status                : {'DETECTABLE [OK]' if result['visible'] else 'NOT DETECTABLE [X]'}")
    
    print("\n" + "=" * 70)
