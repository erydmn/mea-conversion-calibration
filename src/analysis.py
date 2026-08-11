# src/analysis.py
"""Faz 3: Global Duyarlilik Analizi (Morris Metodu).

SALib (Sensitivity Analysis Library) kullanarak flowsheet vekil modelinin
parametrelerinin (L/G, alpha_lean, T_abs, T_reb, y_co2) capture(%) ve
reboiler ozgul enerjisi uzerindeki dogrusal olmayan etkilerini (mu*)
ve etkilesimlerini (sigma) hesaplar.
"""
import numpy as np
from SALib.sample import morris as morris_sample
from SALib.analyze import morris as morris_analyze
import yaml

from .equilibrium_stage import calibrate_eta
from .reduced_model import compute_kpi

def run_morris_analysis(cfg, N=100, num_levels=4):
    """SALib kullanarak Morris duyarlilik analizini calistir.
    
    Parameters
    ----------
    cfg : dict
        config.yaml sozlugu
    N : int
        Morris yorunge (trajectory) sayisi (varsayilan: 100)
    num_levels : int
        Grid seviye sayisi (varsayilan: 4)
        
    Returns
    -------
    problem : dict
        SALib problem tanimi
    results_capture : dict
        Capture pct duyarlilik sonuclari
    results_energy : dict
        Specific energy duyarlilik sonuclari
    """
    nom = cfg['nominal']
    phys = cfg['physical']
    env = cfg['envelope']
    
    # SALib Problem tanimi
    problem = {
        'num_vars': 5,
        'names': ['L_over_G', 'alpha_lean', 'T_abs', 'T_reb', 'y_co2_flue'],
        'bounds': [
            env['L_over_G'],
            env['lean_loading'],
            env['absorber_T'],
            env['reboiler_T'],
            env['flue_gas_co2_frac']
        ]
    }
    
    # Ornekleme
    print(f"SALib Morris ornekleme (N={N}, levels={num_levels})...")
    X = morris_sample.sample(problem, N=N, num_levels=num_levels)
    num_samples = X.shape[0]
    print(f"Toplam ornek sayisi: {num_samples}")
    
    # Eta kalibrasyonu (Nominal duruma gore 1 kere yapilir ve sabit tutulur)
    # Cunku 'eta' cihazin (kolonlarin) fiziksel donanim limitidir.
    eta_abs, eta_reg, _ = calibrate_eta(nom)
    
    Y_capture = np.zeros(num_samples)
    Y_energy = np.zeros(num_samples)
    
    # Degerlendirme
    print("Vekil model (reduced_model) uzerinde degerlendiriliyor...")
    for i in range(num_samples):
        LG, aL, Ta, Tr, yco2 = X[i, :]
        
        # Sadece L_over_G kutlesel oldugundan m_gas ve n_MEA'yi guncelleyecegiz.
        # Bu zaten compute_kpi icinde kutlesel olarak yorumlaniyor.
        kpi = compute_kpi(
            L_over_G=LG,
            alpha_lean=aL,
            T_abs=Ta,
            T_reb=Tr,
            y_co2_flue=yco2,
            n_flue=nom['flue_gas_molar_flow'], # baca gazi debisi sabit
            mea_t=nom['mea_conc_molL'],
            P_abs_kPa=nom['absorber_P_Pa']/1000,
            P_reg_Pa=nom['regen_P_Pa'],
            eta_abs=eta_abs,
            eta_reg=eta_reg,
            Cp_kJkgK=phys['Cp_solvent_kJkgK'],
            dH_abs_kJmol=phys['dH_abs_kJmol'],
            M_CO2=phys['M_CO2'],
            M_MEA=phys['M_MEA'],
            M_H2O=phys['M_H2O'],
            mea_wt_frac=nom['mea_wt_frac']
        )
        
        # Basarisiz kosullar icin ceza degeri atanir
        if np.isnan(kpi['capture_pct']) or kpi['capture_pct'] < 0 or kpi['capture_pct'] > 100:
            Y_capture[i] = 0.0 # Yakalama basarisiz
        else:
            Y_capture[i] = kpi['capture_pct']
            
        if np.isnan(kpi['specific_reboiler_MJkg']) or kpi['specific_reboiler_MJkg'] <= 0:
            Y_energy[i] = 100.0 # Cok yuksek enerji (ceza)
        else:
            Y_energy[i] = kpi['specific_reboiler_MJkg']
            
    # Analiz
    print("Morris analiz sonuclari hesaplaniyor...")
    results_capture = morris_analyze.analyze(problem, X, Y_capture, print_to_console=False)
    results_energy = morris_analyze.analyze(problem, X, Y_energy, print_to_console=False)
    
    return problem, results_capture, results_energy
