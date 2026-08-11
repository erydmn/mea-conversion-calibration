# src/equilibrium_stage.py
"""Kosula bagli absorber/stripper donusum fonksiyonlari (KE tabanli).

Bu modul, sabit %90/%95 donusumu, isletme kosullarina duyarli
fiziksel formuellerle degistirir.

Absorber (Denklem 12-18, N-kademeli versiyon):
  Bilinmeyen: her kademedeki sivi ve gaz kompozisyonu.
  alpha_rich = alpha_N
  X_abs = a_real / n_CO2_in

Stripper (Denklem 19-22):
  P_CO2_strip = (yaklasik) regen tepesi CO2 kismi basinci
  alpha_lean_out = alpha_from_pco2(P_CO2_strip, T_reb, mea_t, 'aboudheir')
  X_reg = eta_reg * (alpha_rich - alpha_lean_out) * n_MEA / n_carbamate_in

Yaklasma faktoru eta (Denklem 23):
  X_effective = eta * X_equilibrium
  eta absorber ve stripper icin nominal kosulda X_abs=0.906, X_reg=0.95
  verecek sekilde kalibre edilir.

Birimler: mol/s (akislar), K (sicaklik), kPa (basinc, KE motoru ici).
"""
import warnings
import numpy as np
from scipy.optimize import brentq
from .ke_solver import alpha_from_pco2


def absorber_conversion(n_CO2_in, n_gas_in, n_MEA, alpha_lean,
                        T_abs, P_abs_kPa, mea_t, eta_stage, N=3):
    """N-kademeli ters akimli (counter-current) absorber modeli.
    
    Gaz asagidan girer (N-1. kademe), sivi yukaridan girer (0. kademe).
    
    Parameters
    ----------
    n_CO2_in : float
        Giris gaz CO2 molar akisi [mol/s]
    n_gas_in : float
        Giris gaz toplam molar akisi [mol/s]
    n_MEA : float
        Solvent MEA molar akisi [mol/s]
    alpha_lean : float
        Giris yalin yukleme [mol CO2/mol MEA]
    T_abs : float
        Absorber sicakligi [K]
    P_abs_kPa : float
        Absorber basinci [kPa]
    mea_t : float
        MEA molar derisimi [mol/L]
    eta_stage : float
        Kademe-basi yaklasma faktoru (Murphree benzeri, 0-1 arasi beklenir)
    N : int
        Kullanilacak denge kademesi sayisi

    Returns
    -------
    X_abs : float
        Absorber CO2 donusum orani (0-1)
    alpha_rich : float
        Cikis zengin yukleme [mol CO2/mol MEA]
    a_real : float
        Absorbe edilen miktar [mol/s]
    """
    if n_CO2_in <= 0:
        return 0.0, alpha_lean, 0.0

    alpha_guess = np.full(N, alpha_lean)
    n_inert = n_gas_in - n_CO2_in
    
    for iter_count in range(50):
        # 1. Gaz profili (Asagidan yukari: i=N-1'den 0'a)
        n_co2_gas = np.zeros(N + 1)
        n_co2_gas[N] = n_CO2_in
        for i in range(N - 1, -1, -1):
            a_in = alpha_guess[i-1] if i > 0 else alpha_lean
            transfer = n_MEA * (alpha_guess[i] - a_in)
            n_co2_gas[i] = max(n_co2_gas[i+1] - transfer, 1e-8)
            
        # 2. Sivi profili (Yukaridan asagi: i=0'dan N-1'e)
        alpha_new = np.zeros(N)
        for i in range(N):
            y_out = n_co2_gas[i] / (n_inert + n_co2_gas[i])
            P_CO2_out = max(y_out * P_abs_kPa, 1e-6)
            
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                try:
                    alpha_eq = alpha_from_pco2(P_CO2_out, T_abs, mea_t, 'zhu')
                except:
                    alpha_eq = alpha_lean
                
            a_in = alpha_new[i-1] if i > 0 else alpha_lean
            alpha_new[i] = a_in + eta_stage * (alpha_eq - a_in)
            
        # 3. Yakinlama kontrolu ve damping
        diff = np.abs(alpha_new - alpha_guess).max()
        if diff < 1e-5:
            alpha_guess = alpha_new
            break
            
        alpha_guess = 0.5 * alpha_guess + 0.5 * alpha_new
        
    alpha_rich = alpha_guess[-1]
    a_real = n_MEA * (alpha_rich - alpha_lean)
    X_abs = np.clip(a_real / n_CO2_in, 0, 1)
    
    if alpha_rich > 0.56:
        print(f"UYARI: Zengin yukleme (alpha_rich={alpha_rich:.3f}) fiziksel 0.56 sinirini asti!")
    
    return X_abs, alpha_rich, a_real


def regenerator_conversion(alpha_rich, n_MEA, n_carbamate_in,
                           T_reb, P_CO2_strip_kPa, mea_t, eta_reg):
    """Rejenerator (stripper) donusum orani (KE denge tabanli)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            alpha_lean_out = alpha_from_pco2(P_CO2_strip_kPa, T_reb, mea_t, 'aboudheir')
        except:
            alpha_lean_out = alpha_rich

    # Denge soyulma
    n_stripped_eq = (alpha_rich - alpha_lean_out) * n_MEA
    n_stripped_eq = max(n_stripped_eq, 0)

    # Yaklasma faktoru ile gercek donusum
    n_stripped = eta_reg * n_stripped_eq

    if n_carbamate_in > 0:
        X_reg = np.clip(n_stripped / n_carbamate_in, 0, 1)
    else:
        X_reg = 0.0

    alpha_lean_real = alpha_rich - n_stripped / n_MEA

    return X_reg, alpha_lean_real, n_stripped_eq


def calibrate_eta(cfg):
    """Yaklasma faktorlerini nominal kosulda kalibre et."""
    # Nominal degerler
    n_flue = cfg['flue_gas_molar_flow']       # mol/s
    y_co2 = cfg['flue_gas_co2_frac']
    n_CO2_in = n_flue * y_co2                  # mol/s
    n_gas_in = n_flue
    mea_t = cfg['mea_conc_molL']               # mol/L
    T_abs = cfg['absorber_T']                  # K
    P_abs_kPa = cfg['absorber_P_Pa'] / 1000    # Pa -> kPa
    T_reb = cfg['reboiler_T']                  # K
    P_reg_Pa = cfg['regen_P_Pa']               # Pa
    alpha_lean = cfg['lean_loading']

    # Solvent akisi (molar L/G * n_gas)
    L_over_G_nom = cfg.get('L_over_G_nominal', 3.41)
    n_MEA = L_over_G_nom * n_flue

    # --- ABSORBER KALIBRASYON ---
    # brentq ile X_abs = 0.906 veren eta_stage degerini bul.
    X_abs_target = 0.906
    def obj_eta(eta):
        X, _, _ = absorber_conversion(
            n_CO2_in, n_gas_in, n_MEA, alpha_lean,
            T_abs, P_abs_kPa, mea_t, eta_stage=eta, N=3
        )
        return X - X_abs_target

    try:
        eta_abs = brentq(obj_eta, 0.001, 0.2, xtol=1e-4)
    except ValueError:
        print("KRIITIK HATA: eta_stage [0.001, 0.2] araliginda kok bulunamadi.")
        print("n_MEA hala yanlis olabilir veya N (kademe sayisi) artirilmali.")
        eta_abs = 1.0

    X_eq_abs, _, _ = absorber_conversion(
        n_CO2_in, n_gas_in, n_MEA, alpha_lean,
        T_abs, P_abs_kPa, mea_t, eta_stage=1.0, N=3
    )

    # --- STRIPPER KALIBRASYON ---
    # alpha_rich gercek
    a_real = X_abs_target * n_CO2_in
    alpha_rich_real = alpha_lean + a_real / n_MEA
    n_carbamate_in = a_real

    # Stripper CO2 kismi basinci (Fiziksel, Raoult Yasasi)
    x_h2o = 0.93  # 20 wt% MEA yaklasik H2O mol kesri
    T_C = T_reb - 273.15
    P_sat_h2o_bar = 10 ** (5.074 - 1657.4 / (T_C + 226.9))
    P_h2o_kPa = P_sat_h2o_bar * 100 * x_h2o
    P_CO2_strip_kPa = max(P_reg_Pa / 1000 - P_h2o_kPa, 1.0)

    X_eq_reg, _, n_stripped_eq = regenerator_conversion(
        alpha_rich_real, n_MEA, n_carbamate_in,
        T_reb, P_CO2_strip_kPa, mea_t, eta_reg=1.0
    )

    X_reg_target = 0.95
    n_stripped_target = X_reg_target * n_carbamate_in
    if n_stripped_eq > 0:
        eta_reg = n_stripped_target / n_stripped_eq
    else:
        eta_reg = 0.90

    info = {
        'X_eq_abs': X_eq_abs,
        'X_eq_reg': X_eq_reg,
        'eta_abs_calibrated': eta_abs,
        'eta_reg_calibrated': eta_reg,
        'alpha_rich': alpha_rich_real,
        'n_CO2_in': n_CO2_in,
        'n_MEA': n_MEA,
        'P_CO2_strip_kPa': P_CO2_strip_kPa,
        'a_eq': 0, # N/A artik
        'n_stripped_eq': n_stripped_eq,
    }

    return eta_abs, eta_reg, info


if __name__ == "__main__":
    import yaml
    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)
    nom = cfg['nominal']

    print("=" * 60)
    print("Equilibrium Stage Kalibrasyon Testi")
    print("=" * 60)

    eta_abs, eta_reg, info = calibrate_eta(nom)
    print(f"\nDenge donusumleri (eta_stage=1):")
    print(f"  X_eq_abs (N=3) = {info['X_eq_abs']:.4f}")
    print(f"  X_eq_reg = {info['X_eq_reg']:.4f}")
    print(f"\nKalibre edilmis eta degerleri:")
    print(f"  eta_stage (absorber) = {eta_abs:.4f} (hedef: X_abs=0.906)")
    print(f"  eta_reg (stripper) = {eta_reg:.4f} (hedef: X_reg=0.95)")

    n_CO2_in = info['n_CO2_in']
    n_gas_in = nom['flue_gas_molar_flow']
    n_MEA = info['n_MEA']
    mea_t = nom['mea_conc_molL']
    T_abs = nom['absorber_T']
    P_abs_kPa = nom['absorber_P_Pa'] / 1000
    alpha_lean = nom['lean_loading']

    X_abs, alpha_rich, _ = absorber_conversion(
        n_CO2_in, n_gas_in, n_MEA, alpha_lean,
        T_abs, P_abs_kPa, mea_t, eta_abs, N=3
    )

    n_carbamate = X_abs * n_CO2_in
    P_CO2_strip = info['P_CO2_strip_kPa']
    T_reb = nom['reboiler_T']

    X_reg, alpha_lean_out, _ = regenerator_conversion(
        alpha_rich, n_MEA, n_carbamate,
        T_reb, P_CO2_strip, mea_t, eta_reg
    )

    print(f"\nNominal kosul dogrulamasi:")
    print(f"  X_abs = {X_abs:.4f} (hedef: 0.906)")
    print(f"  X_reg = {X_reg:.4f} (hedef: 0.950)")
    print(f"  alpha_rich = {alpha_rich:.4f}")
    print(f"  alpha_lean_out = {alpha_lean_out:.4f}")
