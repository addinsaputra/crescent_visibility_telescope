"""
This module provides a Python implementation of the visual limiting magnitude
calculator that appears on the Astronomical Visual Limits calculation page
published by Victor Reijs (based on work by Bradley E. Schaefer and Larry
Bogan).  The original implementation was written in JavaScript and is
available at the Archaeocosmology website.  The code here reproduces the
logic of that script in a clear and well‑structured Python form.

The core routine accepts atmospheric and observational parameters and
computes either the limiting magnitude of an object at a given altitude
or, if a goal magnitude is supplied, the altitude at which an object of
that brightness becomes just visible.  Intermediate quantities such as
air mass, extinction coefficients, sky brightness and the final visual
threshold are also returned for inspection.

References:

* The JavaScript source of the calculator defines the photometric
  constants and algorithms used to estimate extinction and sky
  brightness.  Arrays of wavelengths, zero points, ozone factors,
  aerosol factors, night sky background and colour terms are taken
  directly from that source【771736117259114†L13-L24】.  The code
  computes air masses, extinction coefficients and differential
  extinctions per waveband【771736117259114†L61-L81】, then models dark sky,
  moonlight, twilight and daylight contributions to the overall sky
  brightness【771736117259114†L90-L115】.  Finally it converts the sky
  brightness into nanolamberts and applies Schaefer’s threshold law to
  derive the visual magnitude threshold【771736117259114†L124-L135】.

Usage example:

>>> from visual_limit_calc import visual_limit
>>> result = visual_limit(
...     month=3, year=1972, phase_angle=180,  # New moon
...     altmoon=-90, azimoon=0,               # Moon below horizon
...     altsun=0, azisun=0,                   # Sun on horizon
...     humidity=20, temperature=21,          # Relative humidity and temperature
...     latitude=35.5, altitude=930,          # Observer latitude (deg) and altitude (m)
...     snellen_ratio=1.0, altstar=19.05,     # Visual acuity and object altitude
...     goal_magnitude=99                     # Compute limiting magnitude (99 indicates no goal)
... )
>>> print(result["limiting_magnitude"])
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class ExtinctionResult:
    """Container for intermediate extinction and sky brightness results."""
    sky_brightness_nl: float  # sky brightness in nanolamberts (BL)
    limiting_magnitude: float  # resulting visual limiting magnitude (MN)
    object_altitude: float  # topocentric altitude at which MN was computed
    gas_airmass: float
    aerosol_airmass: float
    ozone_airmass: float
    K: List[float] = field(default_factory=list)  # extinction coefficients per waveband
    DM: List[float] = field(default_factory=list)  # extinction/airmass per waveband
    B: List[float] = field(default_factory=list)   # sky brightness per waveband (picoergs)


def _compute_for_altitude(
    month: float,
    year: float,
    phase_angle: float,
    altmoon: float,
    azimoon: float,
    altsun: float,
    azisun: float,
    humidity: float,
    temperature: float,
    latitude: float,
    altitude: float,
    snellen_ratio: float,
    altitude_star: float,
) -> ExtinctionResult:
    """
    Compute limiting magnitude and auxiliary quantities for a fixed star altitude.

    This function implements the core of the JavaScript algorithm.  It
    calculates air mass factors, extinction coefficients (gas, aerosol,
    ozone, water vapour), sky brightness contributions (dark sky,
    moonlight, twilight and daylight) and the resultant visual threshold.
    Parameters mirror those in the web form; all angular quantities are
    expressed in degrees.

    Returns
    -------
    ExtinctionResult
        Dataclass containing the limiting magnitude, sky brightness in
        nanolamberts, input altitude, air masses and per band arrays.
    """
    # ============================================================
    # KONSTANTA FOTOMETRI SCHAEFER/BOGAN
    # ============================================================
    # WA: Wavelength tengah untuk setiap band fotometri (mikron)
    #     [U=0.365, B=0.44, V=0.55, R=0.7, I=0.9]
    WA = [0.365, 0.44, 0.55, 0.7, 0.9]

    # MO: Lunar magnitude offset per band (magnitudo intrinsik Bulan)
    MO = [-10.93, -10.45, -11.05, -11.90, -12.70]

    # OZ: Faktor ekstinsi ozon per band (koefisien serapan ozon)
    OZ = [0.000, 0.000, 0.031, 0.008, 0.000]

    # WT: Koefisien uap air per band (water vapour extinction coefficients)
    WT = [0.074, 0.045, 0.031, 0.020, 0.015]

    # BO: Dark sky background per band (ergs/cm²/s/μm/arcsec²)
    #     Kecerahan langit malam tanpa bulan/pengaruh lain
    BO = [8.0e-14, 7.0e-14, 1.0e-13, 1.0e-13, 3.0e-13]

    # CM: Colour term corrections (koreksi warna untuk kalkulasi Bulan)
    CM = [1.36, 0.91, 0.00, -0.76, -1.17]

    # MS: Solar magnitudes per band (magnitudo Matahari di setiap band)
    MS = [-25.96, -26.09, -26.74, -27.26, -27.55]

    # ============================================================
    # KONVERSI SATUAN
    # ============================================================
    # RD: Faktor konversi dari derajat ke radian
    RD = math.pi / 180.0

    # ============================================================
    # PERHITUNGAN GEOMETRI: ELONGASI (ANGULAR SEPARATION)
    # ============================================================
    # RM: Elongasi Bulan - Objek (derajat)
    #     Sudut pemisahan antara Bulan dan bintang/objek yang diamati
    #     Digunakan untuk menghitung kontribusi cahaya bulan ke sky brightness
    RM = math.degrees(
        math.acos(
            math.sin(altmoon * RD) * math.sin(altitude_star * RD)
            + math.cos(altmoon * RD) * math.cos(altitude_star * RD) * math.cos(azimoon * RD)
        )
    )

    # RS: Elongasi Matahari - Objek (derajat)
    #     Sudut pemisahan antara Matahari dan bintang/objek yang diamati
    #     Digunakan untuk menghitung kontribusi twilight dan daylight
    RS = math.degrees(
        math.acos(
            math.sin(altsun * RD) * math.sin(altitude_star * RD)
            + math.cos(altsun * RD) * math.cos(altitude_star * RD) * math.cos(azisun * RD)
        )
    )

    # ============================================================
    # ZENITH DISTANCE (JARAK DARI ZENITH)
    # ============================================================
    # ZM: Zenith distance Bulan (derajat) - sudut dari zenith ke Bulan
    ZM = 90.0 - altmoon

    # ZS: Zenith distance Matahari (derajat) - sudut dari zenith ke Matahari
    ZS = 90.0 - altsun

    # Z: Zenith distance objek/bintang (derajat) - sudut dari zenith ke objek
    Z = 90.0 - altitude_star

    # ============================================================
    # SUBROUTINE EXTINCTION: VARIABEL MUSIM & LOKASI
    # ============================================================
    # LT: Latitude pengamat dalam radian
    #     Digunakan untuk koreksi musiman pada ekstinsi ozon
    LT = latitude * RD

    # RA: Right Ascension proxy (rad) - aproksimasi posisi musiman
    #     (bulan - 3) × 30° → mengubah bulan menjadi sudut (0° di Maret)
    RA = (month - 3.0) * 30.0 * RD

    # SL: Sign latitude (+1 untuk belahan bumi utara, -1 untuk selatan)
    #     Menentukan arah koreksi musiman aerosol
    SL = 1.0 if latitude >= 0 else -1.0

    # ZZ: Zenith distance objek dalam radian (Z dikonversi ke radian)
    ZZ = Z * RD

    # ============================================================
    # AIRMASS CALCULATIONS (MASA UDARA)
    # ============================================================
    # XG: Gas airmass (Rayleigh scattering)
    #     Model Kasten & Young (1989) untuk scattering gas atmosfer
    #     Konstanta: 0.0286 dan -10.5 khusus untuk gas
    XG = 1.0 / (math.cos(ZZ) + 0.0286 * math.exp(-10.5 * math.cos(ZZ)))

    # XA: Aerosol airmass
    #     Airmass untuk partikel aerosol (berbeda dari gas karena
    #     aerosol terkonsentrasi di lapisan lebih rendah)
    #     Konstanta: 0.0123 dan -24.5
    XA = 1.0 / (math.cos(ZZ) + 0.0123 * math.exp(-24.5 * math.cos(ZZ)))

    # sinZZ: Nilai sin(zenith distance) - digunakan untuk kalkulasi ozon
    sinZZ = math.sin(ZZ)

    # XO: Ozone airmass
    #     Menggunakan model geometri spherical (bukan Kasten-Young)
    #     Anggap lapisan ozon pada ketinggian 20 km
    #     R = 6378 km (radius bumi), h = 20 km (ketinggian lapisan ozon)
    #     Rumus: XO = 1/√(1 - (sin(Z)/(1+h/R))²)
    XO = 1.0 / math.sqrt(1.0 - (sinZZ / (1.0 + (20.0 / 6378.0))) ** 2)

    # ============================================================
    # ARRAY HASIL PERHITUNGAN PER BAND FOTOMETRI
    # ============================================================
    # K: Extinction coefficient total per band [U, B, V, R, I]
    #    Bernilai magnitudo/airmass - makin besar = makin redup
    K: List[float] = [0.0] * 5

    # DM: Differential magnitude per band [U, B, V, R, I]
    #     Extinction tertimbang airmass (K × airmass)
    #     Ini adalah nilai extinction yang benar-benar dialami cahaya bintang
    DM: List[float] = [0.0] * 5

    # B: Sky brightness per band [U, B, V, R, I] (picoergs/cm²/s/μm/arcsec²)
    #    Kecerahan langit di setiap band setelah semua kontribusi
    B: List[float] = [0.0] * 5

    # ============================================================
    # LOOP: PERHITUNGAN EXTINCTION PER BAND FOTOMETRI (U, B, V, R, I)
    # ============================================================
    for i in range(5):
        # --------------------------------------------------------
        # KR: Rayleigh extinction coefficient (gas atmosfer)
        #     Scattering oleh molekul gas (N2, O2) - bergantung ketinggian & wavelength
        #     exp(-altitude/8200) : makin tinggi lokasi, makin tipis atmosfer
        #     (λ/0.55)^(-4) : hukum Rayleigh, λ lebih pendek = lebih redup
        # --------------------------------------------------------
        KR = 0.1066 * math.exp(-altitude / 8200.0) * (WA[i] / 0.55) ** (-4.0)

        # --------------------------------------------------------
        # KA: Aerosol extinction coefficient
        #     Scattering/absorpsi oleh partikel aerosol
        #     exp(-altitude/1500) : aerosol terkonsentrasi di lapisan rendah
        #     (λ/0.55)^(-1.3) : ketergantungan wavelength lebih lemah dari Rayleigh
        # --------------------------------------------------------
        KA = 0.1 * (WA[i] / 0.55) ** (-1.3) * math.exp(-altitude / 1500.0)

        # rh_fraction: Fraksi kelembaban relatif (dibatasi min 1% untuk hindari log(0))
        rh_fraction = max(humidity / 100.0, 0.01)

        # Koreksi kelembaban: makin lembab, makin banyak aerosol
        # (1 - 0.32/log(rh))^1.33 : empiris dari data
        KA *= (1.0 - 0.32 / math.log(rh_fraction)) ** 1.33

        # Koreksi musiman: 0.33 × SL × sin(RA)
        #     Belahan bumi utara (SL=+1) vs selatan (SL=-1) memiliki pola berbeda
        KA *= (1.0 + 0.33 * SL * math.sin(RA))

        # --------------------------------------------------------
        # KO: Ozone extinction coefficient
        #     Absorpsi oleh lapisan ozon, terutama di band U dan V
        #     Faktor musiman: (3 + 0.4 × (LT×cos(RA) - cos(3×LT))) / 3
        #     Mempertimbangkan variasi musiman ketebalan ozon
        # --------------------------------------------------------
        KO = OZ[i] * (3.0 + 0.4 * (LT * math.cos(RA) - math.cos(3.0 * LT))) / 3.0

        # --------------------------------------------------------
        # KW: Water vapour extinction coefficient
        #     Absorpsi oleh uap air, terutama di near-infrared (band I)
        #     0.94 × (humidity/100) : proporsional dengan kelembaban
        #     exp(temperature/15) : makin panas, makin banyak uap air
        #     exp(-altitude/8200) : makin tinggi, makin sedikit uap air
        # --------------------------------------------------------
        KW = WT[i] * 0.94 * (humidity / 100.0) * math.exp(temperature / 15.0) * math.exp(-altitude / 8200.0)

        # K: Total extinction coefficient per band
        K[i] = KR + KA + KO + KW

        # DM: Differential magnitude (extinction tertimbang airmass)
        #     Setiap komponen dikalikan dengan airmass yang sesuai:
        #     - Rayleigh (KR) × Gas airmass (XG)
        #     - Aerosol (KA) × Aerosol airmass (XA)
        #     - Ozone (KO) × Ozone airmass (XO)
        #     - Water (KW) × Gas airmass (XG) → uap air tersebar seperti gas
        DM[i] = KR * XG + KA * XA + KO * XO + KW * XG

    # ============================================================
    # SUBROUTINE SKY BRIGHTNESS: AIRMASS UNTUK SCATTERING
    # ============================================================
    # X: General airmass untuk sky brightness
    #   Model Kasten-Young dengan konstanta 0.025 dan -11.0
    #   Digunakan untuk perhitungan dark sky, twilight, dan daylight
    X = 1.0 / (math.cos(ZZ) + 0.025 * math.exp(-11.0 * math.cos(ZZ)))

    # XM: Moon airmass - airmass yang ditempuh cahaya Bulan
    #     Jika Bulan di bawah horizon (ZM > 90°), set ke 40.0 (praktis tak terhingga)
    XM = 1.0 / (math.cos(ZM * RD) + 0.025 * math.exp(-11.0 * math.cos(ZM * RD)))
    if ZM > 90.0:
        XM = 40.0

    # XS: Sun airmass - airmass yang ditempuh cahaya Matahari
    #     Jika Matahari di bawah horizon (ZS > 90°), set ke 40.0
    XS = 1.0 / (math.cos(ZS * RD) + 0.025 * math.exp(-11.0 * math.cos(ZS * RD)))
    if ZS > 90.0:
        XS = 40.0

    # ============================================================
    # LOOP: PERHITUNGAN SKY BRIGHTNESS PER BAND
    # ============================================================
    for i in range(5):
        # --------------------------------------------------------
        # BN: Dark night sky brightness (natural background)
        #     Kecerahan langit malam tanpa Bulan/Matahari
        # --------------------------------------------------------
        # Siklus 11 tahun (siklus matahari) mempengaruhi background
        BN = BO[i] * (1.0 + 0.3 * math.cos(6.283 * (year - 1992.0) / 11.0))

        # Koreksi zenith distance: makin dekat horizon, makin terang
        # Faktor (0.4 + 0.6/√(1 - 0.96×sin²(Z))): memperhitungkan
        # peningkatan brightness dekat horizon
        BN *= (0.4 + 0.6 / math.sqrt(max(1.0 - 0.96 * (math.sin(ZZ) ** 2), 1e-6)))

        # Transmisi atmosfer: 10^(-0.4 × K × X)
        # Cahaya langit melewati atmosfer dan mengalami extinction
        BN *= 10.0 ** (-0.4 * K[i] * X)

        # --------------------------------------------------------
        # BM: Moonlight brightness (kontribusi cahaya Bulan)
        # --------------------------------------------------------
        # MM: Magnitudo Bulan tergantung phase angle
        #     -12.73 : magnitudo Bulan purnama (-12.7)
        #     0.026 × |phase| : koreksi linear untuk phase
        #     4e-9 × phase^4 : koreksi orde-4 untuk phase ekstrem
        MM = -12.73 + 0.026 * abs(phase_angle) + 4e-9 * (phase_angle ** 4)

        # Tambahkan colour term correction untuk band ini
        MM += CM[i]

        # C3: Transmisi atmosfer untuk cahaya Bulan (airmass XM)
        C3 = 10.0 ** (-0.4 * K[i] * XM)

        # FM: Fase scattering Bulan (angular dependence)
        #     (6.2×10^7)/RM² : invers kuadrat jarak
        #     10^(6.15 - RM/40) : faktor fase
        #     10^5.36 × (1.06 + cos²(RM)) : backscattering enhancement
        if RM == 0.0:
            FM = 0.0
        else:
            FM = (6.2e7) / (RM ** 2) + 10.0 ** (6.15 - RM / 40.0)
        FM += 10.0 ** 5.36 * (1.06 + (math.cos(RM * RD) ** 2))

        # BM: Kecerahan langit akibat cahaya Bulan
        BM = 10.0 ** (-0.4 * (MM - MO[i] + 43.27))
        BM *= (1.0 - 10.0 ** (-0.4 * K[i] * X))
        BM *= (FM * C3 + 440000.0 * (1.0 - C3))

        # --------------------------------------------------------
        # BT: Twilight brightness (kontribusi senja)
        # --------------------------------------------------------
        # HS: Tinggi Matahari di atas horizon (derajat)
        HS = 90.0 - ZS

        # BT: Model twilight Schaefer
        #     MS[i] - MO[i] + 32.5 - HS : magnitudo twilight
        #     Z/(360×K) : koreksi zenith distance
        if K[i] == 0.0 or RS == 0.0:
            BT = 0.0
        else:
            BT = 10.0 ** (-0.4 * (MS[i] - MO[i] + 32.5 - HS - (Z / (360.0 * K[i]))))
            BT *= (100.0 / RS) * (1.0 - 10.0 ** (-0.4 * K[i] * X))

        # --------------------------------------------------------
        # BD: Daylight brightness (kontribusi siang hari)
        # --------------------------------------------------------
        # C4: Transmisi atmosfer untuk cahaya Matahari (airmass XS)
        C4 = 10.0 ** (-0.4 * K[i] * XS)

        # FS: Fase scattering Matahari (mirip FM tapi untuk Matahari)
        if RS == 0.0:
            FS = 0.0
        else:
            FS = 6.2e7 / (RS ** 2) + 10.0 ** (6.15 - RS / 40.0)
        FS += 10.0 ** 5.36 * (1.06 + (math.cos(RS * RD) ** 2))

        # BD: Kecerahan langit akibat cahaya Matahari
        BD = 10.0 ** (-0.4 * (MS[i] - MO[i] + 43.27))
        BD *= (1.0 - 10.0 ** (-0.4 * K[i] * X))
        BD *= (FS * C4 + 440000.0 * (1.0 - C4))

        # --------------------------------------------------------
        # KOMBINASI SEMUA KOMPONEN SKY BRIGHTNESS
        # --------------------------------------------------------
        # Gunakan yang lebih kecil antara daylight (BD) dan twilight (BT)
        if BD < BT:
            brightness = BN + BD
        else:
            brightness = BN + BT

        # Tambahkan kontribusi Bulan jika Bulan di atas horizon
        if ZM < 90.0:
            brightness += BM

        # Konversi dari ergs ke picoergs (×10^12)
        B[i] = brightness * 1.0e12

    # ============================================================
    # KONVERSI KE NANOLAMBERTS & PERHITUNGAN LIMITING MAGNITUDE
    # ============================================================
    # BL: Sky brightness dalam nanolamberts (band V)
    #     Nanolambert = satuan kecerahan langit (1 nL = 10^-10 cd/m²)
    #     Faktor 1.02e-3: konversi dari picoergs ke nanolamberts
    BL = B[2] / 1.02e-3

    # --------------------------------------------------------
    # TH: Visual threshold (ambang deteksi mata manusia)
    #     Menggunakan model empiris Schaefer
    # --------------------------------------------------------
    # C1, C2: Konstanta empiris untuk threshold function
    #          Ada 2 regime: langit gelap (<1500 nL) vs terang (≥1500 nL)
    if BL < 1500.0:
        # Langit gelap: konstanta berbeda
        C1 = 10.0 ** (-9.8)
        C2 = 10.0 ** (-1.9)
    else:
        # Langit terang: konstanta berbeda
        C1 = 10.0 ** (-8.350001)
        C2 = 10.0 ** (-5.9)

    # TH: Threshold function
    #     Rumus: C1 × (1 + √(C2 × BL))²
    #     Makin terang langit (BL besar), makin besar threshold
    TH = C1 * (1.0 + math.sqrt(C2 * BL)) ** 2.0

    # --------------------------------------------------------
    # LIMITING MAGNITUDE: Magnitudo paling redup yang masih terlihat
    # --------------------------------------------------------
    # limiting_mag: Rumus Schaefer untuk limiting magnitude
    #     -16.57 : konstanta basis
    #     -2.5 × log10(TH) : kontribusi threshold
    #     -DM[2] : koreksi extinction (band V)
    #     +5 × log10(snellen) : koreksi ketajaman penglihatan
    #                          (snellen=1 → normal, >1 → lebih tajam)
    limiting_mag = -16.57 - 2.5 * math.log10(TH) - DM[2] + 5.0 * math.log10(max(snellen_ratio, 1e-6))

    return ExtinctionResult(
        sky_brightness_nl=BL,
        limiting_magnitude=limiting_mag,
        object_altitude=altitude_star,
        gas_airmass=XG,
        aerosol_airmass=XA,
        ozone_airmass=XO,
        K=K,
        DM=DM,
        B=B,
    )


def visual_limit(
    month: float,
    year: float,
    phase_angle: float,
    altmoon: float,
    azimoon: float,
    altsun: float,
    azisun: float,
    humidity: float,
    temperature: float,
    latitude: float,
    altitude: float,
    snellen_ratio: float,
    altstar: float,
    goal_magnitude: Optional[float] = None,
    step_deg: float = 0.01,
) -> Dict[str, Any]:
    """
    Compute the visual limiting magnitude or the altitude required to reach
    a given magnitude.

    Parameters follow those of the original JavaScript form.  Angles are
    given in degrees.  If `goal_magnitude` is set to 99 or left as
    ``None``, the function computes the limiting magnitude for the
    supplied star altitude.  Otherwise it will iterate starting at
    altitude 0° and increment by `step_deg` until the computed
    magnitude equals or exceeds the goal magnitude.  A small step
    produces finer resolution at the cost of more computation.

    Returns
    -------
    Dict[str, Any]
        A dictionary containing the sky brightness (nanolamberts), the
        limiting magnitude, the altitude at which the result was
        obtained, air mass components and the per‑band extinction and
        brightness arrays.  Fields include:

        - ``sky_brightness`` – sky brightness in nanolamberts
        - ``limiting_magnitude`` – limiting magnitude of the object
        - ``altitude`` – the altitude used/found (degrees)
        - ``gas_airmass`` – air mass for gas scattering
        - ``aerosol_airmass`` – air mass for aerosols
        - ``ozone_airmass`` – air mass for ozone
        - ``K`` – list of extinction coefficients per photometric band
        - ``DM`` – list of differential magnitudes per band
        - ``B`` – list of sky brightness per band (picoergs)
    """
    # ============================================================
    # INISIALISASI VARIABEL UNTUK PENCARIAN GOAL MAGNITUDE
    # ============================================================
    # goal: Target magnitudo (99 = hitung limiting magnitude, bukan cari altitude)
    if goal_magnitude is None:
        goal = 99.0
    else:
        goal = float(goal_magnitude)

    # start_alt: Altitude awal untuk iterasi
    #           - Jika goal=99: mulai dari altstar (hitung sekali saja)
    #           - Jika goal≠99: mulai dari 0° (horizon) dan cari ke atas
    if goal == 99.0:
        start_alt = altstar
    else:
        start_alt = 0.0

    # MN: Limiting magnitude saat ini (diinisialisasi ke nilai sangat redup)
    MN = -99.0

    # current_alt: Altitude yang sedang diuji dalam loop pencarian
    current_alt = start_alt

    # last_result: Menyimpan hasil ExtinctionResult dari iterasi terakhir
    last_result: Optional[ExtinctionResult] = None

    # ============================================================
    # LOOP PENCARIAN: ITERASI SAMPAI GOAL TERCAPAI
    # ============================================================
    while MN < goal:
        # Hitung limiting magnitude untuk altitude saat ini
        result = _compute_for_altitude(
            month,
            year,
            phase_angle,
            altmoon,
            azimoon,
            altsun,
            azisun,
            humidity,
            temperature,
            latitude,
            altitude,
            snellen_ratio,
            current_alt,
        )

        # Update MN dengan limiting magnitude dari hasil perhitungan
        MN = result.limiting_magnitude

        # Simpan hasil untuk referensi
        last_result = result

        # --------------------------------------------------------
        # LOGIKA TERMINASI LOOP
        # --------------------------------------------------------
        if goal == 99.0:
            # Mode hitung limiting magnitude:
            # Set goal = MN agar loop berakhir setelah 1 iterasi
            # (mimik behaviour JavaScript asli)
            goal = MN
        else:
            # Mode cari altitude untuk goal magnitude:
            # Jika belum mencapai goal, naikkan altitude dan lanjutkan
            if MN < goal:
                current_alt += step_deg

    # ============================================================
    # FORMAT OUTPUT DICTIONARY
    # ============================================================
    # Cek kasus patologis (seharusnya tidak pernah terjadi)
    if last_result is None:
        return {}

    # Return dictionary dengan semua hasil perhitungan
    return {
        "sky_brightness": last_result.sky_brightness_nl,
        "limiting_magnitude": last_result.limiting_magnitude,
        "altitude": last_result.object_altitude,
        "gas_airmass": last_result.gas_airmass,
        "aerosol_airmass": last_result.aerosol_airmass,
        "ozone_airmass": last_result.ozone_airmass,
        "K": last_result.K,
        "DM": last_result.DM,
        "B": last_result.B,
    }


__all__ = ["visual_limit"]


# -----------------------------------------------------------------------------
# Command‑line interface
#
# The following block allows this module to be executed directly from the
# command line.  When run as a script it parses a handful of options
# corresponding to the parameters of ``visual_limit`` and prints the results
# to standard output.  Reasonable defaults are provided so that running
# ``python visual_limit_calc.py`` produces an example computation without
# requiring any arguments.

# -----------------------------------------------------------------------------
# Command‑line interface
#
# Bagian berikut memungkinkan modul dijalankan langsung dari command line.
# Saat dijalankan sebagai script, argumen baris perintah akan diparsing
# dan hasil perhitungan akan ditampilkan dalam format JSON.
# Default values disediakan sehingga `python visual_limit_calc.py`
# dapat langsung dijalankan tanpa argumen untuk contoh perhitungan.
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import json

    # Parser untuk argumen command line
    parser = argparse.ArgumentParser(
        description=(
            "Calculate the visual limiting magnitude or required altitude for a given magnitude."
        )
    )
    # Waktu & lokasi observasi
    parser.add_argument("--month", type=float, default=7, help="Month number (1–12) of observation")
    parser.add_argument("--year",  type=float, default=2022, help="Calendar year of observation")

    # Posisi Bulan
    parser.add_argument(
        "--phase-angle",
        type=float,
        default=180.0,
        dest="phase_angle",
        help="Lunar phase angle in degrees (180=new moon, 90=quarter, 0=full moon)",
    )
    parser.add_argument("--altmoon", type=float, default=-90.0, help="Moon topocentric altitude (°)")
    parser.add_argument("--azimoon", type=float, default=180.0, help="Moon azimuth difference relative to object (°)")

    # Posisi Matahari
    parser.add_argument("--altsun", type=float, default=-0.3, help="Sun topocentric altitude (°)")
    parser.add_argument("--azisun", type=float, default=5.037, help="Sun azimuth difference relative to object (°)")

    # Kondisi atmosfer
    parser.add_argument("--humidity", type=float, default=80.73, help="Relative humidity (%)")
    parser.add_argument("--temperature", type=float, default=25.27, help="Air temperature (°C)")

    # Lokasi & kondisi pengamat
    parser.add_argument("--latitude", type=float, default=-7.0, help="Observer latitude (°)")
    parser.add_argument("--altitude", type=float, default=89, help="Observer altitude above sea level (m)")
    parser.add_argument("--snellen", type=float, default=1.0, dest="snellen_ratio", help="Snellen ratio (1 for 20/20 vision)")

    # Objek yang diamati
    parser.add_argument("--altstar", type=float, default=4.1, help="Object topocentric altitude (°)")
    parser.add_argument("--goal", type=float, default=99.0, dest="goal_magnitude", help="Goal magnitude (99 to compute limiting magnitude)")
    parser.add_argument("--step", type=float, default=0.01, dest="step_deg", help="Altitude step when searching for goal magnitude (°)")

    # Parse argumen command line
    args = parser.parse_args()

    # Panggil fungsi visual_limit dengan argumen dari command line
    result = visual_limit(
        month=args.month,
        year=args.year,
        phase_angle=args.phase_angle,
        altmoon=args.altmoon,
        azimoon=args.azimoon,
        altsun=args.altsun,
        azisun=args.azisun,
        humidity=args.humidity,
        temperature=args.temperature,
        latitude=args.latitude,
        altitude=args.altitude,
        snellen_ratio=args.snellen_ratio,
        altstar=args.altstar,
        goal_magnitude=args.goal_magnitude,
        step_deg=args.step_deg,
    )

    # Tampilkan hasil dalam format JSON (pretty-printed)
    print(json.dumps(result, indent=2))