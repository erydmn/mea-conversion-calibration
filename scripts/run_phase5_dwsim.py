"""Faz 5: DWSIM vs KE-Fizibilite Analizi Karsilastirmasi.

Bu betik DWSIM'i orijinal (90%/95% sabit donusum) ayarlariyla calistirir.
Daha sonra, DWSIM'in hesapladigi reboiler duty ve kitle dengesini okur.
Ayni nominal sartlar icin Proxy Modeli (Fiziksel / Termodinamik sinirlariyla)
calistirarak gerceklesen enerjiyi karsilastirir.
Farkin nedenlerini aciklar (Lean-Rich Heat Exchanger etkileri, donusum sinirlari).
"""
import sys
sys.path.insert(0, ".")
import yaml

from src.dwsim_harness import DWSIMHarness
from src.reduced_model import compute_kpi
from src.equilibrium_stage import calibrate_eta

if __name__ == "__main__":
    print("=== FAZ 5: DWSIM KARSILASTIRMASI (GERCEK VALIDASYON) ===")
    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)
        
    nom = cfg['nominal']
    phys = cfg['physical']
    eta_abs, eta_reg, _ = calibrate_eta(nom)
    
    print("\n[1] DWSIM Orijinal Flowsheet Calistiriliyor (Sabit %90/%95 Donusum)...")
    try:
        harness = DWSIMHarness("Flowsheet.dwxmz", cfg, dwsim_path="C:/Users/Excalıbur/AppData/Local/DWSIM")
        harness.calculate()
        harness.check_mass_balance()
        
        # Oku
        kpis = harness.get_kpis()
        reboiler_kW = kpis.get('reboiler_duty_kW', 0.0)
        co2_out_kg_s = harness.get_stream_property(cfg['dwsim_map']['streams']['co2_product'], "MassFlow")
        
        dwsim_spec_MJ = (reboiler_kW / 1000.0) / co2_out_kg_s if co2_out_kg_s and co2_out_kg_s > 0 else 0.0
        
        print("\n--- DWSIM Orijinal Sonuclar ---")
        print(f"  Reboiler Duty (HT-1) : {reboiler_kW:.2f} kW")
        print(f"  CO2 Uretimi          : {co2_out_kg_s:.4f} kg/s")
        print(f"  Spesifik Enerji      : {dwsim_spec_MJ:.2f} MJ/kg CO2")
        print(f"  (Not: DWSIM Lean-Rich Isı Geri Kazanimi (ER-1) icerir.)")
            
    except Exception as e:
        print(f"\nDWSIM calistirilamadi: {e}")
        print("Lutfen DWSIM'in kurulu oldugundan ve pythonnet yuklu oldugundan emin olun.")
        sys.exit(1)
        
    print("\n[2] Proxy Model Analizi (Fiziksel Termodinamik Sinirlar)")
    # Nominal L/G'de Proxy model
    LG_nom = nom['L_over_G_nominal']
    aL_nom = nom['lean_loading']
    kpi_proxy = compute_kpi(LG_nom, aL_nom, nom['absorber_T'], nom['reboiler_T'], nom['flue_gas_co2_frac'], nom['flue_gas_molar_flow'], nom['mea_conc_molL'], nom['absorber_P_Pa']/1000, nom['regen_P_Pa'], eta_abs, eta_reg, phys['Cp_solvent_kJkgK'], phys['dH_abs_kJmol'], phys['M_CO2'], phys['M_MEA'], phys['M_H2O'], nom['mea_wt_frac'])
    
    print("\n--- Proxy Model (KE-Fizibilite) Sonuclari ---")
    print(f"  Hesaplanan X_abs      : %{kpi_proxy['X_abs']*100:.2f}")
    print(f"  Hesaplanan X_reg      : %{kpi_proxy['X_reg']*100:.2f}")
    print(f"  Reboiler Isitma Gereksinimi: {kpi_proxy['Q_reboiler_kW']:.2f} kW")
    print(f"  CO2 Yakalama Orani    : %{kpi_proxy['capture_pct']:.2f}")
    print(f"  Spesifik Enerji       : {kpi_proxy['specific_reboiler_MJkg']:.2f} MJ/kg CO2")
    
    # Karsilastirma Yorumu
    print("\n=== SONUC VE ACIKLAMA ===")
    print("DWSIM (sabit %90/%95) reaksiyon modelinde termodinamik dengeyi dikkate almaz;")
    print("bunun yerine dayatilan oranlarla cozume gider.")
    print("Ote yandan, proxy modelimiz gercek L/G, lean loading ve denge kisitlarina bagli olarak")
    print(f"CO2 ayirma kapasitesini {kpi_proxy['capture_pct']:.1f}% olarak hesaplamis ve stripper isisini buna gore belirlemistir.")
    print("\nEnerji farkinin iki ana nedeni vardir:")
    print("  1. Isı Geri Kazanimi: DWSIM'deki ER-1 (Lean-Rich Heat Exchanger) isiyi geri kazanirken,")
    print("     su anki proxy modelimiz duyurucu/isitici isiyi tamamen dissal (10+ MW) varsayiyor.")
    print("  2. Fizibilite (Stripping Siniri): Proxy modeli a_rich degerinin fiziksel stripping")
    print("     limitlerine vurdugu yerlerde uyarir; DWSIM ise bunu gormezden gelerek cozumu zorlar.")
