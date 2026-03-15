import math


def crescent_area(elongation_deg: float, r_deg: float) -> float:
    """
    Menghitung luas sabit bulan.

    Parameter:
    elongation_deg (float): Sudut elongasi (derajat)
    r_deg (float): Semidiameter bulan (derajat)

    Returns:
    float: Luas sabit bulan (derajat²)

    Rumus: A = (0.5 * pi * r²) * [1 + cos(180° - ARCL)]
    dimana ARCL adalah elongasi (Arc of Light)

    Catatan:
    - Untuk Kastner: gunakan langsung (output dalam derajat²)
    - Untuk Crumey: konversi manual ke arcmin² (A * 3600)
    """
    elong_rad = math.radians(elongation_deg)
    # 180° dalam radian = math.pi
    return 0.5 * math.pi * (r_deg ** 2) * (1 + math.cos(math.pi - elong_rad))


def hitung_luminansi_kastner(alpha, elongation, r, z, k=0.5):
    """
    Menghitung kecerahan (luminance) Hilal menggunakan model Kastner.

    Parameter:
    alpha (float): Phase angle bulan (derajat)
    elongation (float): Sudut elongasi (derajat)
    r (float): Semidiameter bulan (derajat)
    z (float): Jarak zenit / Zenith distance (derajat)
    k (float): Koefisien ekstingsi (default 0.5 untuk atmosfer bersih)

    Returns:
    float: Luminansi hilal di dalam atmosfer (satuan nL)
    """

    # 1. Konversi input derajat ke radian untuk fungsi trigonometri
    alpha_rad = math.radians(alpha)
    elong_rad = math.radians(elongation)
    z_rad = math.radians(z)

    # 2. Persamaan (3): Magnitudo Visual (mv)
    # mv = 0.026 * alpha + 4 * 10^-9 * alpha^4 - 12.73
    mv = (0.026 * alpha) + (4e-9 * (alpha**4)) - 12.73

    # 3. Persamaan (2): Luas Sabit Bulan (D)
    # D = 1/2 * pi * r^2 * [1 - cos(elongation)]
    D = crescent_area(elongation, r)
    
    # 4. Persamaan (1): Luminansi di luar atmosfer (L*)
    # L* = (2.51 ^ (10 - mv)) / D
    # Note: D tidak boleh nol (terjadi jika elongasi = 0)
    if D == 0:
        return 0
    L_star = (2.51**(10 - mv)) / D
    
    # 5. Persamaan (5): Massa Udara Rozenberg (X)
    # X = 1 / (cos(z) + 0.025 * e^(-11 * cos(z)))
    cos_z = math.cos(z_rad)
    X = 1 / (cos_z + 0.025 * math.exp(-11 * cos_z))
    
    # 6. Persamaan (4): Luminansi Hilal di dalam atmosfer (L) dalam nL
    # L = 0.263 * L* * e^(-kX)
    # Catatan: 0.263 adalah faktor konversi satuan ke nanoLambert
    L = 0.263 * L_star * math.exp(-k * X)
    
    return L
 
if __name__ == "__main__":
    # --- CONTOH PENGGUNAAN ---
    # Data input
    alpha = 171.59194444444
    elongation = 8.3858333333333
    r = 0.2625  # derajat
    z = 86.9

    # Contoh 1: Menghitung luminansi Hilal (Kastner)
    hasil = hitung_luminansi_kastner(alpha=alpha, elongation=elongation, r=r, z=z)
    print(f"Luminansi Hilal di dalam atmosfer (L): {hasil:.4f} nL")

    # crescent_area() output dalam derajat², konversi manual ke arcmin²
    A_deg2 = crescent_area(elongation, r)
    A_arcmin2 = A_deg2 * 3600  # 1 derajat² = 3600 arcmin²
    print(f"Luas sabit bulan (A): {A_arcmin2:.4f} arcmin²")

    # L_nl = hasil  # luminansi hilal dari Kastner (nL)
    # B_nl = 1234.5  # sky brightness dari Schaefer (nL)
    # spec = TelescopeSpec(aperture_mm=100, magnification=50, ...)
    # out = visibility_margin(L_nl, B_nl, A_arcmin2, spec=spec)
    # print(f"Margin visibilitas: {out['margin_tel']:.2f}")