# src/reduced_model.py
"""Hizli flowsheet vekili (indirgenmiş model) + KPI hesaplamalari.

Faz 1 donusumlerini kullanip tum flowsheet KPI'larini hizlica hesaplar.
DWSIM olmadan, saf Python ile tum isletme zarfini tarar.

KPI Denklemleri (Bolum D.10):
  (24) Yakalama(%) = 100*(n_CO2_flue - n_CO2_cleangas) / n_CO2_flue
  (27) Reboiler(kW) = Q_sensible + Q_reaction
       Q_sensible = m_solvent * Cp * (T_reb - T_abs)
       Q_reaction = n_CO2_stripped * dH_abs
  (28) Ozgul(MJ/kg) = Reboiler(kW) / (n_CO2_captured * M_CO2/1000) / 1000

Enerji notu: dH_abs = 64.0 kJ/mol (DWSIM degeri). Literatur ~85 kJ/mol.
  Bu fark uncertainty.md'de belgelenir.
  Kullanici istegine gore reduced_model icinde her iki deger ile
  karsilastirma yapilabilir.

Birimler: mol/s, K, kPa (KE ici), Pa (DWSIM/config), kW (enerji).
"""
import warnings
import numpy as np
from .equilibrium_stage import absorber_conversion, regenerator_conversion, calibrate_eta


def compute_kpi(L_over_G, alpha_lean, T_abs, T_reb, y_co2_flue,
                n_flue, mea_t, P_abs_kPa, P_reg_Pa,
                eta_abs, eta_reg,
                Cp_kJkgK, dH_abs_kJmol, M_CO2, M_MEA, M_H2O,
                mea_wt_frac, y_co2_regen=0.393):
    """Tek isletme noktasi icin tum KPI'lari hesapla.

    Parameters
    ----------
    L_over_G : float
        Solvent/gaz molar orani (n_MEA/n_gas)
    alpha_lean : float
        Giris yalin yukleme [mol CO2/mol MEA]
    T_abs : float
        Absorber sicakligi [K]
    T_reb : float
        Reboiler sicakligi [K]
    y_co2_flue : float
        Baca gazi CO2 mol kesri
    n_flue : float
        Baca gazi toplam molar akisi [mol/s]
    mea_t : float
        MEA molar derisimi [mol/L]
    P_abs_kPa : float
        Absorber basinci [kPa]
    P_reg_Pa : float
        Rejenerator basinci [Pa]
    eta_abs, eta_reg : float
        Yaklasma faktorleri
    Cp_kJkgK : float
        Solvent isi kapasitesi [kJ/kg/K]
    dH_abs_kJmol : float
        CO2 absorpsiyon entalpisi [kJ/mol]
    M_CO2, M_MEA, M_H2O : float
        Molar kutleler [g/mol]
    mea_wt_frac : float
        MEA kutle kesri

    Returns
    -------
    kpi : dict
        Hesaplanan KPI sozlugu
    """
    # Giris akimlari
    n_CO2_in = n_flue * y_co2_flue          # mol/s
    n_gas_in = n_flue                        # mol/s
    
    # L_over_G molar (n_MEA / n_gas) bazdadir (config.yaml envelope [1.0, 4.0])
    n_MEA = L_over_G * n_gas_in

    # Stripper CO2 kismi basinci (Fiziksel, Raoult Yasasi)
    x_h2o = 0.93  # 20 wt% MEA yaklasik H2O mol kesri
    T_C = T_reb - 273.15
    P_sat_h2o_bar = 10 ** (5.074 - 1657.4 / (T_C + 226.9))
    P_h2o_kPa = P_sat_h2o_bar * 100 * x_h2o
    P_CO2_strip_kPa = max(P_reg_Pa / 1000 - P_h2o_kPa, 1.0)

    # --- ABSORBER ---
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            X_abs, alpha_rich, a_eq = absorber_conversion(
                n_CO2_in, n_gas_in, n_MEA, alpha_lean,
                T_abs, P_abs_kPa, mea_t, eta_abs
            )
    except Exception:
        return _nan_kpi()

    # Tutulan CO2
    n_CO2_captured = X_abs * n_CO2_in
    n_CO2_cleangas = n_CO2_in - n_CO2_captured

    # Yakalama yuzdesi
    capture_pct = 100 * n_CO2_captured / n_CO2_in if n_CO2_in > 0 else 0

    # --- STRIPPER ---
    n_carbamate_in = n_CO2_captured  # karbamat = tutulan CO2 (1:1)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            X_reg, alpha_lean_out, n_stripped_eq = regenerator_conversion(
                alpha_rich, n_MEA, n_carbamate_in,
                T_reb, P_CO2_strip_kPa, mea_t, eta_reg
            )
    except Exception:
        return _nan_kpi()

    n_CO2_stripped = X_reg * n_carbamate_in

    # --- ENERJI ---
    # Solvent kutle akisi
    # 20 wt% MEA: cozelti = MEA + H2O
    # m_soln = n_MEA * M_MEA / mea_wt_frac   (toplam cozelti kutlesi)
    m_solvent_gs = n_MEA * M_MEA / mea_wt_frac  # g/s
    m_solvent_kgs = m_solvent_gs / 1000           # kg/s

    # Sensible isitma (solvent: T_abs -> T_reb)
    Q_sensible_kW = m_solvent_kgs * Cp_kJkgK * (T_reb - T_abs)

    # Reaksiyon isisi (soyulan CO2 icin)
    Q_reaction_kW = n_CO2_stripped * dH_abs_kJmol  # kJ/s = kW

    # Toplam reboiler gorevi
    Q_reboiler_kW = Q_sensible_kW + Q_reaction_kW

    # Ozgul reboiler enerji tuketimi [MJ/kg CO2]
    m_CO2_captured_kgs = n_CO2_captured * M_CO2 / 1000  # kg/s
    if m_CO2_captured_kgs > 0:
        specific_reboiler_MJkg = Q_reboiler_kW / m_CO2_captured_kgs / 1000
    else:
        specific_reboiler_MJkg = np.inf

    kpi = {
        'L_over_G': L_over_G,
        'alpha_lean': alpha_lean,
        'T_abs': T_abs,
        'T_reb': T_reb,
        'y_co2_flue': y_co2_flue,
        'X_abs': X_abs,
        'X_reg': X_reg,
        'alpha_rich': alpha_rich,
        'alpha_lean_out': alpha_lean_out,
        'capture_pct': capture_pct,
        'n_CO2_captured': n_CO2_captured,
        'n_CO2_stripped': n_CO2_stripped,
        'Q_sensible_kW': Q_sensible_kW,
        'Q_reaction_kW': Q_reaction_kW,
        'Q_reboiler_kW': Q_reboiler_kW,
        'specific_reboiler_MJkg': specific_reboiler_MJkg,
        'n_MEA': n_MEA,
        'n_CO2_in': n_CO2_in,
    }
    return kpi


def _nan_kpi():
    """Bos/NaN KPI sozlugu (hesaplama basarisizliginda)."""
    keys = ['L_over_G', 'alpha_lean', 'T_abs', 'T_reb', 'y_co2_flue',
            'X_abs', 'X_reg', 'alpha_rich', 'alpha_lean_out',
            'capture_pct', 'n_CO2_captured', 'n_CO2_stripped',
            'Q_sensible_kW', 'Q_reaction_kW', 'Q_reboiler_kW',
            'specific_reboiler_MJkg', 'n_MEA', 'n_CO2_in']
    return {k: np.nan for k in keys}


def run_grid(cfg, eta_abs, eta_reg, n_LG=15, n_aL=15):
    """L/G x alpha_lean grid taramasi.

    Parameters
    ----------
    cfg : dict
        config.yaml tam icerik (nominal + physical + envelope)
    eta_abs, eta_reg : float
        Kalibre edilmis yaklasma faktorleri
    n_LG, n_aL : int
        Grid boyutu (varsayilan 15x15 = 225 nokta)

    Returns
    -------
    results : list of dict
        Her grid noktasi icin KPI sozlugu
    """
    nom = cfg['nominal']
    phys = cfg['physical']
    env = cfg['envelope']

    LG_range = np.linspace(env['L_over_G'][0], env['L_over_G'][1], n_LG)
    aL_range = np.linspace(env['lean_loading'][0], env['lean_loading'][1], n_aL)

    results = []
    total = n_LG * n_aL
    done = 0

    for LG in LG_range:
        for aL in aL_range:
            kpi = compute_kpi(
                L_over_G=LG,
                alpha_lean=aL,
                T_abs=nom['absorber_T'],
                T_reb=nom['reboiler_T'],
                y_co2_flue=nom['flue_gas_co2_frac'],
                n_flue=nom['flue_gas_molar_flow'],
                mea_t=nom['mea_conc_molL'],
                P_abs_kPa=nom['absorber_P_Pa'] / 1000,
                P_reg_Pa=nom['regen_P_Pa'],
                eta_abs=eta_abs,
                eta_reg=eta_reg,
                Cp_kJkgK=phys['Cp_solvent_kJkgK'],
                dH_abs_kJmol=phys['dH_abs_kJmol'],
                M_CO2=phys['M_CO2'],
                M_MEA=phys['M_MEA'],
                M_H2O=phys['M_H2O'],
                mea_wt_frac=nom['mea_wt_frac'],
                y_co2_regen=nom.get('regen_y_co2', 0.393)
            )
            results.append(kpi)
            done += 1
            if done % 50 == 0:
                print(f"  Grid ilerleme: {done}/{total}")

    return results


# =========================================================================
# Oz-test
# =========================================================================
if __name__ == "__main__":
    import yaml

    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)

    nom = cfg['nominal']
    phys = cfg['physical']

    # Kalibrasyon
    eta_abs, eta_reg, cal_info = calibrate_eta(nom)
    print(f"eta_abs={eta_abs:.4f}, eta_reg={eta_reg:.4f}")

    # Nominal KPI (Molar L/G)
    LG_nom = nom.get('L_over_G_nominal', 3.41)
    
    kpi = compute_kpi(
        L_over_G=LG_nom,
        alpha_lean=nom['lean_loading'],
        T_abs=nom['absorber_T'],
        T_reb=nom['reboiler_T'],
        y_co2_flue=nom['flue_gas_co2_frac'],
        n_flue=nom['flue_gas_molar_flow'],
        mea_t=nom['mea_conc_molL'],
        P_abs_kPa=nom['absorber_P_Pa'] / 1000,
        P_reg_Pa=nom['regen_P_Pa'],
        eta_abs=eta_abs,
        eta_reg=eta_reg,
        Cp_kJkgK=phys['Cp_solvent_kJkgK'],
        dH_abs_kJmol=phys['dH_abs_kJmol'],
        M_CO2=phys['M_CO2'],
        M_MEA=phys['M_MEA'],
        M_H2O=phys['M_H2O'],
        mea_wt_frac=nom['mea_wt_frac'],
        y_co2_regen=nom.get('regen_y_co2', 0.393)
    )

    print("\nNominal KPI:")
    for k, v in kpi.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.4f}")
        else:
            print(f"  {k}: {v}")
