# src/ke_solver.py
"""Kent-Eisenberg VLE cozucu: alpha <-> P_CO2.

Bu modul, KE modelinin cekirdek cozucusunu icerir. Iki temel fonksiyon:
  - alpha_from_pco2: verilen P_CO2, T, MEA_t -> denge yuklemesi alpha
  - pco2_from_alpha: verilen alpha, T, MEA_t -> denge P_CO2

Birimler (KE motoru ic birim sozlesmesi — §A.4):
  P_CO2     : kPa
  Derisimler: mol/L
  T         : K
  alpha     : mol CO2/mol MEA (boyutsuz)

Cozum Algoritmasi (Referans: Bolum D):
  Verilen [CO2] (Henry'den veya kok-arama ile) ve [H3O+] (yuk dengesinden):
    (3) [OH-]     = K_w / [H3O+]
    (4) [HCO3-]   = K_co2 * [CO2] / [H3O+]
    (5) [CO3^2-]  = K_bic * [HCO3-] / [H3O+]
    (6) [RNH2]    = MEA_t / (1 + [H3O+]/K_prot + [HCO3-]/K_carb_rev)
    (7) [RNH3+]   = [RNH2] * [H3O+] / K_prot
    (8) [RNHCOO-] = [RNH2] * [HCO3-] / K_carb_rev

  Yuk dengesi (kok bulunacak denklem):
    (11) [RNH3+] + [H3O+] = [OH-] + [HCO3-] + 2[CO3^2-] + [RNHCOO-]

  Yukleme:
    (10) alpha = ([CO2] + [HCO3-] + [CO3^2-] + [RNHCOO-]) / MEA_t

Aktivite katsayilari: gamma_i = 1 (ideal cozelti varsayimi).
Yuksek yuklemelerde (alpha > 0.5) ve yuksek MEA (> 30 wt%) bu sapma olusturur.
"""
import warnings
import numpy as np
from scipy.optimize import brentq
from .kent_eisenberg import K_w, K_co2, K_bic, K_prot, K_carb_rev, H_co2


def _species(H3O, CO2, T, mea_t, source):
    """Verilen [H3O+] ve [CO2] icin tum tur derisimleri.

    Parameters
    ----------
    H3O : float
        [H3O+] derisimi [mol/L]
    CO2 : float
        Serbest [CO2] derisimi [mol/L]
    T : float
        Sicaklik [K]
    mea_t : float
        Toplam MEA derisimi [mol/L] (= [RNH2] + [RNH3+] + [RNHCOO-])
    source : str
        'zhu' veya 'aboudheir'

    Returns
    -------
    tuple : (OH, HCO3, CO3, RNH2, RNH3, RNHCOO)
        Tum tur derisimler [mol/L]
    """
    OH     = K_w(T) / H3O                                              # (3)
    HCO3   = K_co2(T) * CO2 / H3O                                     # (4)
    CO3    = K_bic(T) * HCO3 / H3O                                    # (5)
    RNH2   = mea_t / (1 + H3O / K_prot(T, source)
                         + HCO3 / K_carb_rev(T, source))               # (6)
    RNH3   = RNH2 * H3O / K_prot(T, source)                           # (7)
    RNHCOO = RNH2 * HCO3 / K_carb_rev(T, source)                      # (8)
    return OH, HCO3, CO3, RNH2, RNH3, RNHCOO


def _solve_H3O(CO2, T, mea_t, source):
    """Yuk dengesini saglayan [H3O+]'yi bul (log-uzayinda brentq).

    Denklem (11): [RNH3+] + [H3O+] = [OH-] + [HCO3-] + 2[CO3^2-] + [RNHCOO-]

    Parameters
    ----------
    CO2 : float
        Serbest [CO2] derisimi [mol/L]
    T : float
        Sicaklik [K]
    mea_t : float
        Toplam MEA derisimi [mol/L]
    source : str
        'zhu' veya 'aboudheir'

    Returns
    -------
    H3O : float
        [H3O+] derisimi [mol/L]

    Notes
    -----
    Arama araligi: [H3O+] in [1e-12, 1e-2] mol/L
    Tolerans: xtol=1e-10 (Bolum E)
    """
    def charge(logH):
        H = 10**logH
        OH, HCO3, CO3, RNH2, RNH3, RNHCOO = _species(H, CO2, T, mea_t, source)
        # Yuk dengesi artigi: katyonlar - anyonlar = 0
        return (RNH3 + H) - (OH + HCO3 + 2 * CO3 + RNHCOO)

    logH = brentq(charge, -12, -2, xtol=1e-10)
    return 10**logH


def alpha_from_pco2(pco2, T, mea_t, source):
    """Verilen P_CO2 [kPa], T, MEA_t -> denge yuklemesi alpha.

    Algoritma (Bolum D.6):
      1. [CO2] = P_CO2 / H_CO2(T)  (Henry)
      2. [H3O+]'yi yuk dengesinden coz
      3. Tum turleri hesapla
      4. alpha = ([CO2] + [HCO3-] + [CO3^2-] + [RNHCOO-]) / MEA_t

    Parameters
    ----------
    pco2 : float
        CO2 kismi basinci [kPa]
    T : float
        Sicaklik [K]
    mea_t : float
        Toplam MEA derisimi [mol/L]
    source : str
        'zhu' (absorber) veya 'aboudheir' (stripper)

    Returns
    -------
    alpha : float
        Denge yuklemesi [mol CO2/mol MEA]
    """
    _validity_warn(pco2, T, source)
    CO2 = pco2 / H_co2(T)                                             # (2)
    H = _solve_H3O(CO2, T, mea_t, source)
    OH, HCO3, CO3, RNH2, RNH3, RNHCOO = _species(H, CO2, T, mea_t, source)
    return (CO2 + HCO3 + CO3 + RNHCOO) / mea_t                        # (10)


def pco2_from_alpha(alpha, T, mea_t, source):
    """Verilen alpha -> P_CO2 [kPa] (alpha_from_pco2'nin tersi).

    Algoritma (Bolum D.5):
      Dis: P_CO2'yi ara, ic: alpha_from_pco2(P_CO2) - alpha = 0
      Arama log-uzayinda: P_CO2 in [1e-4, 1e5] kPa

    Parameters
    ----------
    alpha : float
        Denge yuklemesi [mol CO2/mol MEA]
    T : float
        Sicaklik [K]
    mea_t : float
        Toplam MEA derisimi [mol/L]
    source : str
        'zhu' (absorber) veya 'aboudheir' (stripper)

    Returns
    -------
    pco2 : float
        CO2 kismi basinci [kPa]
    """
    def f(logp):
        return alpha_from_pco2(10**logp, T, mea_t, source) - alpha

    logp = brentq(f, -4, 5, xtol=1e-8)
    return 10**logp


def _validity_warn(pco2, T, source):
    """Gecerlilik penceresi disinda uyari ver.

    Zhu 2022 katsayilari: 298-353 K (20 wt%)
    Aboudheir 2003 katsayilari: 298-413 K

    Ekstrapolasyon riskleri docs/uncertainty.md'de belgelenir.
    """
    if source == 'zhu' and not (298 <= T <= 353):
        warnings.warn(
            f"T={T}K Zhu araligi (298-353 K) disinda; "
            f"stripper icin source='aboudheir' kullan.",
            stacklevel=3
        )
    if source == 'aboudheir' and not (298 <= T <= 413):
        warnings.warn(
            f"T={T}K Aboudheir araligi (298-413 K) disinda. "
            f"Ekstrapolasyon guvenirligi dusuk.",
            stacklevel=3
        )


# =========================================================================
# Oz-test: alpha_from_pco2 monotonluk testi (Bolum E)
# Basinc artinca yukleme de artmali -> fiziksel olarak dogru
# =========================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("KE Cozucu Testi: P_CO2(kPa) -> alpha (Zhu, 313K, 3.285 mol/L)")
    print("=" * 60)

    mea_t = 3.285  # 20 wt% MEA = 3.285 mol/L
    T = 313.15

    pressures = [0.1, 1, 10, 100, 1000]
    alphas = []

    print(f"{'P_CO2 (kPa)':>12} -> {'alpha':>8}")
    print("-" * 25)

    for p in pressures:
        a = alpha_from_pco2(p, T, mea_t, 'zhu')
        alphas.append(a)
        print(f"{p:>12} -> {a:>8.4f}")

    # Monotonluk kontrolu
    is_monotone = all(alphas[i] < alphas[i+1] for i in range(len(alphas)-1))
    print(f"\nMototonluk (basinc artinca alpha artiyor): {'DOGRU' if is_monotone else 'BASARISIZ'}")

    # Ters cozum testi
    print(f"\n{'Ters cozum testi: alpha -> P_CO2':}")
    print(f"{'alpha':>8} -> {'P_CO2 (kPa)':>12} -> {'alpha (geri)':>12} -> {'Hata':>8}")
    print("-" * 50)
    for a_test in [0.3, 0.4, 0.5, 0.6]:
        p_calc = pco2_from_alpha(a_test, T, mea_t, 'zhu')
        a_back = alpha_from_pco2(p_calc, T, mea_t, 'zhu')
        err = abs(a_back - a_test)
        print(f"{a_test:>8.4f} -> {p_calc:>12.4f} -> {a_back:>12.6f} -> {err:>8.2e}")

    # Aboudheir 393 K testi (stripper kosullari)
    print(f"\nStripper testi: Aboudheir, 393K, 3.285 mol/L")
    print(f"{'P_CO2 (kPa)':>12} -> {'alpha':>8}")
    print("-" * 25)
    for p in [1, 10, 100, 500]:
        a = alpha_from_pco2(p, 393.15, mea_t, 'aboudheir')
        print(f"{p:>12} -> {a:>8.4f}")

    print("\n" + "=" * 60)
    ref_vals = [0.3411, 0.4528, 0.5368, 0.6544, 0.8903]
    close_enough = all(abs(a - r) < 0.05 for a, r in zip(alphas, ref_vals))
    print(f"Referans degerlerle karsilastirma: {'UYUMLU' if close_enough else 'KONTROL ET'}")
    for p, a, r in zip(pressures, alphas, ref_vals):
        print(f"  P={p:>6} kPa: hesap={a:.4f}, ref={r:.4f}, fark={abs(a-r):.4f}")
    print("=" * 60)
