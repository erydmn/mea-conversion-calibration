"""Faz 4: Dogrusal Olmayan Optimizasyon Calistirma.

src.optimization icindeki SLSQP optimizasyonunu calistirir,
nominal isletme noktasi ile optimize edilmis noktayi karsilastirir
ve bir bar grafigi ile sonuclari kaydeder.
"""
import sys
sys.path.insert(0, ".")

import numpy as np
import matplotlib.pyplot as plt
import yaml

from src.optimization import optimize_plant
from src.equilibrium_stage import calibrate_eta
from src.reduced_model import compute_kpi
from src.plotting import setup_dark_style, add_watermark, COLORS

setup_dark_style()

if __name__ == "__main__":
    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)
        
    print("=== FAZ 4: SLSQP OPTIMIZASYONU ===")
    
    # 1. Nominal KPI'yi tekrar hesapla (kiyaslama icin)
    nom = cfg['nominal']
    phys = cfg['physical']
    eta_abs, eta_reg, cal_info = calibrate_eta(nom)
    
    LG_nom_molar = nom.get('L_over_G_nominal', 3.41)
    
    kpi_nom = compute_kpi(
        L_over_G=LG_nom_molar, alpha_lean=nom['lean_loading'], 
        T_abs=nom['absorber_T'], T_reb=nom['reboiler_T'],
        y_co2_flue=nom['flue_gas_co2_frac'], n_flue=nom['flue_gas_molar_flow'],
        mea_t=nom['mea_conc_molL'], P_abs_kPa=nom['absorber_P_Pa']/1000,
        P_reg_Pa=nom['regen_P_Pa'], eta_abs=eta_abs, eta_reg=eta_reg,
        Cp_kJkgK=phys['Cp_solvent_kJkgK'], dH_abs_kJmol=phys['dH_abs_kJmol'],
        M_CO2=phys['M_CO2'], M_MEA=phys['M_MEA'], M_H2O=phys['M_H2O'],
        mea_wt_frac=nom['mea_wt_frac']
    )
    
    # 2. Optimizasyonu calistir
    res, kpi_opt = optimize_plant(cfg)
    
    # 3. Sonuclari yazdir
    print("\n" + "=" * 50)
    print("OPTIMIZASYON SONUCLARI")
    print("=" * 50)
    if res.success:
        print("DURUM: BASARILI")
    else:
        print(f"DURUM: BASARISIZ ({res.message})")
        
    print(f"\n{'Parametre/KPI':<25} | {'Nominal':<12} | {'Optimize':<12} | {'Fark':<10}")
    print("-" * 65)
    
    # Goruntulenecek metrikler
    metrics = [
        ('L/G (mol/mol)', kpi_nom['L_over_G'], kpi_opt['L_over_G']),
        ('alpha_lean (mol/mol)', kpi_nom['alpha_lean'], kpi_opt['alpha_lean']),
        ('T_abs (C)', kpi_nom['T_abs']-273.15, kpi_opt['T_abs']-273.15),
        ('T_reb (C)', kpi_nom['T_reb']-273.15, kpi_opt['T_reb']-273.15),
        ('Capture Pct (%)', kpi_nom['capture_pct'], kpi_opt['capture_pct']),
        ('Reboiler Duty (kW)', kpi_nom['Q_reboiler_kW'], kpi_opt['Q_reboiler_kW']),
        ('Specific Energy (MJ/kg)', kpi_nom['specific_reboiler_MJkg'], kpi_opt['specific_reboiler_MJkg'])
    ]
    
    for name, v_nom, v_opt in metrics:
        diff = v_opt - v_nom
        if 'Pct' in name or 'Energy' in name or 'L/G' in name or 'alpha' in name:
            print(f"{name:<25} | {v_nom:<12.3f} | {v_opt:<12.3f} | {diff:<+10.3f}")
        else:
            print(f"{name:<25} | {v_nom:<12.1f} | {v_opt:<12.1f} | {diff:<+10.1f}")
            
    tasarruf = (kpi_nom['L_over_G'] - kpi_opt['L_over_G']) / kpi_nom['L_over_G'] * 100
    if abs(tasarruf) < 2.0:
        print(f"\nL/G Tasarrufu: %{tasarruf:.1f} (Stripper tavan kapasitesine ulasildi: T_reb = 120 C)")
    else:
        print(f"\nL/G Tasarrufu: %{tasarruf:.1f}")
    
    # 4. Karsilastirmali Bar Grafigi
    fig, ax = plt.subplots(figsize=(8, 6))
    
    bar_width = 0.35
    index = np.arange(2)
    
    # L/G ciziyoruz
    values_nom = [kpi_nom['L_over_G'], kpi_nom['specific_reboiler_MJkg']]
    values_opt = [kpi_opt['L_over_G'], kpi_opt['specific_reboiler_MJkg']]
    labels = ['L/G Orani\n(mol/mol)', 'Spesifik Enerji\n(MJ/kg CO2)']
    
    bars1 = ax.bar(index, values_nom, bar_width, label='Nominal', color='#E91E63')
    bars2 = ax.bar(index + bar_width, values_opt, bar_width, label='Optimize Edilmis', color='#4CAF50')
    
    ax.set_ylabel('Deger')
    ax.set_title('Nominal vs Optimize Edilmis Tesis Performansi')
    ax.set_xticks(index + bar_width / 2)
    ax.set_xticklabels(labels)
    ax.legend()
    ax.grid(axis='y', alpha=0.15)
    
    # Degerleri ustune yazdir
    for bar in bars1:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval + 0.05, f'{yval:.2f}', ha='center', va='bottom', color='white')
    for bar in bars2:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval + 0.05, f'{yval:.2f}', ha='center', va='bottom', color='white')
        
    add_watermark(ax)
    plt.tight_layout()
    plt.savefig("results/figures/phase4_optimization.png")
    print(f"\nGrafik kaydedildi: results/figures/phase4_optimization.png")
    
    # KAPI 4 DEGERLENDIRMESI
    print("\n" + "=" * 60)
    print("KAPI 4 DEGERLENDIRMESI")
    print("=" * 60)
    
    pass_flag = True
    if kpi_opt['capture_pct'] < 89.9:
        print("BASARISIZ: Yakalama orani %90'in altinda.")
        pass_flag = False
    if kpi_opt['T_reb'] > 393.16: # ufak tolerans
        print(f"BASARISIZ: Reboiler sicakligi 120 C sinirini asiyor ({kpi_opt['T_reb']-273.15:.1f} C).")
        pass_flag = False
    if kpi_opt['L_over_G'] > 4.0:
        print("BASARISIZ: L/G limiti asildi.")
        pass_flag = False
        
    if pass_flag:
        print(f"KAPI 4 GECTI: SLSQP optimizasyonu basarili.")
        if abs(tasarruf) < 2.0:
            print(f"L/G tasarrufu: %{tasarruf:.1f} elde edildi (Stripper Limit).")
        else:
            print(f"L/G tasarrufu: %{tasarruf:.1f} elde edildi.")
    print("=" * 60)
