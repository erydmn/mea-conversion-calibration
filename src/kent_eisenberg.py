# src/kent_eisenberg.py
"""CO2-MEA Kent-Eisenberg denge sabitleri.

Bu modul, CO2-MEA sisteminin vapour-liquid equilibrium (VLE) hesaplamalari
icin gerekli tum termodinamik denge sabiti fonksiyonlarini icerir.

Kaynaklar:
  Edwards ve ark. 1978  -> K_w, K_co2, K_bic (uc makalede de ayni)
  Zhu ve ark. 2022      -> protonasyon+karbamat (20 wt%, 298-353 K)  [absorber]
  Aboudheir ve ark. 2003-> protonasyon+karbamat (298-413 K)          [stripper]

Form: ln K = a1/T + a2*ln(T) + a3   (T Kelvin)

Birimler:
  T     : Kelvin
  K_w   : (mol/L)^2
  K_co2 : mol/L
  K_bic : mol/L
  K_prot: mol/L
  K_carb: mol/L
  H_co2 : kPa*L/mol

Aktivite katsayilari: Bu klasik KE modeli, sivi faz tur aktivite
katsayilarini BIR (1.0) olarak kabul eder. Yuksek yuklemelerde
(alpha > 0.5) ve yuksek MEA derisimlerinde (> 30 wt%) bu varsayim
sapmalara yol acar. Detaylar: docs/uncertainty.md
"""
import numpy as np


def _K(a1, a2, a3, T):
    """Genel denge sabiti korelasyonu.

    ln K(T) = a1/T + a2*ln(T) + a3

    Parameters
    ----------
    a1, a2, a3 : float
        Korelasyon katsayilari (kaynak: Edwards 1978 / Zhu 2022 / Aboudheir 2003)
    T : float veya array-like
        Sicaklik [K]

    Returns
    -------
    K : float veya ndarray
        Denge sabiti degeri
    """
    return np.exp(a1 / T + a2 * np.log(T) + a3)


# =========================================================================
# Ortak denge sabitleri (Edwards ve ark. 1978)
# Kaynak: Edwards, Maurer, Newman, Prausnitz, AIChE J. 24 (1978) 966-976
# Bu uc sabit Zhu (2022) ve Aboudheir (2003)'de birebir aynidir.
# Gecerlilik: 273-498 K
# =========================================================================

def K_w(T):
    """Su oto-iyonizasyonu: 2H2O <-> H3O+ + OH-

    Birim: (mol/L)^2
    Kaynak: Edwards 1978, Denklem seti
    Gecerlilik: 273-498 K
    """
    return _K(-13445.9, -22.4773, 140.932, T)


def K_co2(T):
    """CO2 hidratasyonu: CO2 + 2H2O <-> H3O+ + HCO3-

    Birim: mol/L
    Kaynak: Edwards 1978
    Gecerlilik: 273-498 K
    """
    return _K(-12092.1, -36.7816, 235.482, T)


def K_bic(T):
    """Bikarbonat iyonizasyonu: HCO3- + H2O <-> CO3^2- + H3O+

    Birim: mol/L
    Kaynak: Edwards 1978
    Gecerlilik: 273-498 K
    """
    return _K(-12431.7, -35.4819, 220.067, T)


# =========================================================================
# Fit edilen sabitler: protonasyon + karbamat (IKI KAYNAK)
#
# DIKKAT: Zhu ve Aboudheir K8/K9 etiketlerini TERS kullanir.
# Bu yuzden koda K8/K9 yerine fiziksel anlami olan
# K_prot ve K_carb_rev isimleri kullanilir.
#
# Kaynak secimi kurali (ekstrapolasyondan kacinmak icin):
#   - Absorber (313-323 K): source='zhu'  -> 20 wt%'te en dogru
#   - Stripper (393 K):     source='aboudheir' -> 413 K'ye kadar gecerli
# =========================================================================

def K_prot(T, source):
    """Protonasyon dengesi: RNH3+ <-> RNH2 + H3O+

    K_prot = [RNH2][H3O+] / [RNH3+]

    Parameters
    ----------
    T : float
        Sicaklik [K]
    source : str
        'zhu' (absorber, 298-353 K) veya 'aboudheir' (stripper, 298-413 K)

    Returns
    -------
    K_prot : float
        Protonasyon denge sabiti [mol/L]
    """
    if source == 'zhu':
        # Zhu 2022, Tablo 3 K8 (20 wt%, 298-353 K)
        return _K(-5880.90, 0.0, -3.24111, T)
    if source == 'aboudheir':
        # Aboudheir 2003, K9 (298-413 K)
        return _K(-5851.11, 0.0, -3.3636, T)
    raise ValueError(f"bilinmeyen source: {source}")


def K_carb_rev(T, source):
    """Karbamat (reversion formu): RNHCOO- + H2O <-> RNH2 + HCO3-

    Ic temsil (reversion):
        [RNHCOO-] = [RNH2] * [HCO3-] / K_carb_rev

    Parameters
    ----------
    T : float
        Sicaklik [K]
    source : str
        'zhu' (absorber, 298-353 K) veya 'aboudheir' (stripper, 298-413 K)

    Returns
    -------
    K_carb_rev : float
        Karbamat reversion denge sabiti [mol/L]

    Notes
    -----
    Zhu formu: K_carb_rev = K_prot_zhu * K9_Zhu
      K9_Zhu (consumption) = [RNH3+][HCO3-] / ([RNHCOO-][H3O+])
      -> K_carb_rev = K_prot * K9_Zhu = ([RNH2][H3O+]/[RNH3+]) *
                      ([RNH3+][HCO3-]/([RNHCOO-][H3O+]))
                    = [RNH2][HCO3-] / [RNHCOO-]  (beklenen reversion formu)

    Aboudheir formu: dogrudan K8_Ab = [RNH2][HCO3-] / [RNHCOO-]
    """
    if source == 'zhu':
        # K_carb_rev = K_prot(zhu) * K9_Zhu
        # K9_Zhu: a1=3117.05, a2=0, a3=8.94366
        # Kaynak: Zhu 2022, Tablo 3
        return K_prot(T, 'zhu') * _K(3117.05, 0.0, 8.94366, T)
    if source == 'aboudheir':
        # Aboudheir 2003, K8 (dogrudan reversion)
        return _K(-3090.83, 0.0, 6.69425, T)
    raise ValueError(f"bilinmeyen source: {source}")


# =========================================================================
# Henry sabiti (Zhu 2022, Tablo 2, 20 wt%)
# Ham degerler: 298K->3251.62, 313K->4078.31, 333K->5344.08, 353K->6791.55
# Fit (dogrulanmis, kusursuz uyum): ln H = 12.8141 - 1408.69/T
# Birim: kPa*L/mol
# Kullanim: [CO2]_serbest = P_CO2 / H_CO2(T)  -> mol/L
# =========================================================================

def H_co2(T):
    """Henry sabiti: CO2 cozunurlugu (20 wt% MEA cozeltisi).

    H_CO2(T) = exp(12.8141 - 1408.69/T)

    Birim: kPa*L/mol
    Kaynak: Zhu 2022, Tablo 2'den lineer fit
    Gecerlilik: 298-353 K (ekstrapolasyon 393 K'ye kadar makul)

    Kullanim: [CO2] = P_CO2(kPa) / H_CO2(T)  -> mol/L
    """
    return np.exp(12.8141 - 1408.69 / T)


# =========================================================================
# Oz-test: Zhu Tablo 3 capraz-kontrolu
# Hesaplanan sabitler tablo degerleriyle %5 icinde otusmalidir.
# =========================================================================

if __name__ == "__main__":
    # Zhu 2022 Tablo 3 referans degerleri
    tablo = {
        298: (1.09693e-10, 2.66631e8),
        313: (2.63471e-10, 1.62296e8),
        333: (7.78297e-10, 8.90972e7),
        353: (2.40987e-9,  5.22888e7),
    }

    print("=" * 72)
    print("Kent-Eisenberg Sabit Dogrulama (Zhu 2022 Tablo 3)")
    print("=" * 72)
    print(f"{'T(K)':<6} {'K_prot(hesap)':>14} {'K_prot(tablo)':>14} {'Hata%':>7} | "
          f"{'K9_Zhu(hesap)':>14} {'K9_Zhu(tablo)':>14} {'Hata%':>7}")
    print("-" * 72)

    max_err_prot = 0
    max_err_k9 = 0

    for T, (k8_ref, k9_ref) in tablo.items():
        k_prot_calc = K_prot(T, 'zhu')
        k9_calc = _K(3117.05, 0.0, 8.94366, T)  # K9_Zhu ham

        err_prot = abs(k_prot_calc - k8_ref) / k8_ref * 100
        err_k9 = abs(k9_calc - k9_ref) / k9_ref * 100
        max_err_prot = max(max_err_prot, err_prot)
        max_err_k9 = max(max_err_k9, err_k9)

        print(f"{T:<6} {k_prot_calc:>14.4e} {k8_ref:>14.4e} {err_prot:>6.2f}% | "
              f"{k9_calc:>14.4e} {k9_ref:>14.4e} {err_k9:>6.2f}%")

    print("-" * 72)

    # Henry sabiti dogrulama
    print("\nHenry sabiti dogrulama (Zhu Tablo 2):")
    h_ref = {298: 3251.62, 313: 4078.31, 333: 5344.08, 353: 6791.55}
    max_err_h = 0
    for T, href in h_ref.items():
        hcalc = H_co2(T)
        err = abs(hcalc - href) / href * 100
        max_err_h = max(max_err_h, err)
        print(f"  T={T}K: H_calc={hcalc:.2f}, H_ref={href:.2f}, hata={err:.2f}%")

    # Ortusme kontrolu: 333-353 K'de iki kaynak %10 icinde uyusmali
    print("\nKaynak ortusme kontrolu (333-353 K):")
    for T in [333, 353]:
        kp_z = K_prot(T, 'zhu')
        kp_a = K_prot(T, 'aboudheir')
        diff_prot = abs(kp_z - kp_a) / kp_a * 100

        kc_z = K_carb_rev(T, 'zhu')
        kc_a = K_carb_rev(T, 'aboudheir')
        diff_carb = abs(kc_z - kc_a) / kc_a * 100

        print(f"  T={T}K: K_prot fark={diff_prot:.1f}%, K_carb_rev fark={diff_carb:.1f}%")

    # Sonuc
    print("\n" + "=" * 72)
    passed = max_err_prot <= 5 and max_err_k9 <= 5 and max_err_h <= 1
    if passed:
        print(f"KAPI 3 GECTI: K_prot max hata={max_err_prot:.2f}%, "
              f"K9 max hata={max_err_k9:.2f}%, H max hata={max_err_h:.2f}%")
    else:
        print(f"KAPI 3 BASARISIZ: K_prot={max_err_prot:.2f}%, "
              f"K9={max_err_k9:.2f}%, H={max_err_h:.2f}%")
    print("=" * 72)
