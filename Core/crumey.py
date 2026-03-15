# --- Tambahan / Integrasi: Implementasi rumus Crumey (extended source) ---
import math

# konversi unit: nanoLambert (nL) <-> cd/m^2
NANO_LAMBERT_TO_CD_M2 = 1e-5 / math.pi   # 1 nL = 1e-9 L; 1 L = 1e4 / pi cd/m^2 -> combine => 1e-5/pi
CD_M2_TO_NANO_LAMBERT = 1.0 / NANO_LAMBERT_TO_CD_M2

def nL_to_cd_m2(nl: float) -> float:
    """Convert nanoLambert to cd/m^2."""
    return nl * NANO_LAMBERT_TO_CD_M2

def cd_m2_to_nL(cd: float) -> float:
    """Convert cd/m^2 to nanoLambert."""
    return cd * CD_M2_TO_NANO_LAMBERT

def arcmin2_to_sr(area_arcmin2: float) -> float:
    """Convert area in arcmin^2 to steradian."""
    rad_per_arcmin = math.pi / (180.0 * 60.0)
    return area_arcmin2 * (rad_per_arcmin ** 2)

# --- Crumey model functions ---
def crumey_R(B_cd: float) -> float:
    """
    R(B) as smooth combined form (eq. 25 in Crumey).
    B_cd is background luminance in cd/m^2 (must be >0).
    """
    if B_cd <= 0:
        raise ValueError("B must be positive for Crumey functions.")
    # coefficients from paper
    a1 = 5.949e-8
    a2 = -2.389e-7
    a3 = 2.459e-7
    a4 = 4.120e-4
    a5 = -4.225e-4

    term1 = a1 * (B_cd ** -0.5) + a2 * (B_cd ** -0.25) + a3
    inner = math.sqrt(max(term1, 0.0))  # ensure non-negative
    outer = inner + a4 * (B_cd ** -0.25) + a5
    return outer ** 2

def crumey_Cinf(B_cd: float) -> float:
    """
    C_infty(B) combined form (eq. 39 in Crumey).
    """
    if B_cd <= 0:
        raise ValueError("B must be positive for Crumey functions.")
    b1 = 9.606e-6
    b2 = -4.112e-5
    b3 = 5.019e-5
    b4 = 4.837e-3
    b5 = -4.884e-3

    term = b1 * (B_cd ** -0.5) + b2 * (B_cd ** -0.25) + b3
    root = math.sqrt(max(term, 0.0))
    return root + b4 * (B_cd ** -0.25) + b5

def crumey_q(B_cd: float) -> float:
    """
    q parameter piecewise (eqs. 42-44 in Crumey). log base 10.
    """
    if B_cd <= 0:
        raise ValueError("B must be positive for Crumey functions.")
    logB = math.log10(B_cd)
    if B_cd >= 3.40:
        return 1.146 - 0.0885 * logB
    elif 0.193 <= B_cd < 3.40:
        return 0.8861 + 0.4 * logB
    else:
        return 0.6

def crumey_threshold(A_sr: float, B_cd: float) -> float:
    """
    Compute C_th = C(A,B) per Crumey eq. (41).
    A_sr: area in steradian
    B_cd: background luminance in cd/m^2
    Returns contrast threshold (dimensionless).
    """
    if A_sr <= 0:
        raise ValueError("Area A must be positive.")
    R = crumey_R(B_cd)
    Cinf = crumey_Cinf(B_cd)
    q = crumey_q(B_cd)
    # To avoid overflow, compute in a numerically stable way
    term = (R / A_sr) ** q + (Cinf ** q)
    return term ** (1.0 / q)

def crumey_visibility(Lt_cd: float, B_cd: float, A_sr: float) -> dict:
    """
    Given target luminance Lt (cd/m^2), background B (cd/m^2),
    and angular area A (sr), compute C_obj, C_th, and visible boolean.
    """
    if B_cd <= 0:
        raise ValueError("B must be positive.")
    C_obj = (Lt_cd - B_cd) / B_cd
    C_th = crumey_threshold(A_sr, B_cd)
    visible = C_obj > C_th
    return {"C_obj": C_obj, "C_th": C_th, "visible": visible}