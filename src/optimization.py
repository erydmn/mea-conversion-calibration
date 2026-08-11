"""Faz 4: Dogrusal Olmayan Optimizasyon (SLSQP).

scipy.optimize.minimize (SLSQP) kullanarak %90 (veya uzeri) yakalama verimi
ve termodinamik kapali-dongu (absorber alpha_lean == stripper alpha_lean_out)
kisitlari altinda, solvent dolasimini (L/G oranini) minimize eden
optimum calisma kosullarini (L/G, alpha_lean, T_abs, T_reb) bulur.
"""
import numpy as np
from scipy.optimize import minimize
import yaml

from .equilibrium_stage import calibrate_eta
from .reduced_model import compute_kpi

def optimize_plant(cfg):
    nom = cfg['nominal']
    phys = cfg['physical']
    env = cfg['envelope']
    
    eta_abs, eta_reg, _ = calibrate_eta(nom)
    
    x0 = np.array([
        nom.get('L_over_G_nominal', 3.41),
        nom['lean_loading'],
        nom['absorber_T'],
        nom['reboiler_T']
    ])
    
    bounds = [
        (env['L_over_G'][0], env['L_over_G'][1]),
        (env['lean_loading'][0], env['lean_loading'][1]),
        (env['absorber_T'][0], env['absorber_T'][1]),
        (env['reboiler_T'][0], 393.15)
    ]
    
    def objective(x):
        LG, aL, Ta, Tr = x
        return LG
        
    def constraint_capture(x):
        LG, aL, Ta, Tr = x
        kpi = compute_kpi(LG, aL, Ta, Tr, nom['flue_gas_co2_frac'], nom['flue_gas_molar_flow'], nom['mea_conc_molL'], nom['absorber_P_Pa']/1000, nom['regen_P_Pa'], eta_abs, eta_reg, phys['Cp_solvent_kJkgK'], phys['dH_abs_kJmol'], phys['M_CO2'], phys['M_MEA'], phys['M_H2O'], nom['mea_wt_frac'])
        if np.isnan(kpi['capture_pct']):
            return -100.0
        return kpi['capture_pct'] - 90.0
        
    def constraint_loop(x):
        LG, aL, Ta, Tr = x
        kpi = compute_kpi(LG, aL, Ta, Tr, nom['flue_gas_co2_frac'], nom['flue_gas_molar_flow'], nom['mea_conc_molL'], nom['absorber_P_Pa']/1000, nom['regen_P_Pa'], eta_abs, eta_reg, phys['Cp_solvent_kJkgK'], phys['dH_abs_kJmol'], phys['M_CO2'], phys['M_MEA'], phys['M_H2O'], nom['mea_wt_frac'])
        if np.isnan(kpi['alpha_lean_out']):
            return -100.0
        return kpi['alpha_lean_out'] - aL
        
    constraints = [
        {'type': 'ineq', 'fun': constraint_capture},
        {'type': 'eq', 'fun': constraint_loop}
    ]
    
    print("SLSQP Optimizasyonu basliyor (Hedef: Minimum L/G)...")
    res = minimize(
        objective, 
        x0, 
        method='SLSQP', 
        bounds=bounds,
        constraints=constraints,
        options={'disp': True, 'maxiter': 100, 'ftol': 1e-4}
    )
    
    LG, aL, Ta, Tr = res.x
    kpi_opt = compute_kpi(LG, aL, Ta, Tr, nom['flue_gas_co2_frac'], nom['flue_gas_molar_flow'], nom['mea_conc_molL'], nom['absorber_P_Pa']/1000, nom['regen_P_Pa'], eta_abs, eta_reg, phys['Cp_solvent_kJkgK'], phys['dH_abs_kJmol'], phys['M_CO2'], phys['M_MEA'], phys['M_H2O'], nom['mea_wt_frac'])
    kpi_opt['loop_residual'] = kpi_opt['alpha_lean_out'] - aL
    
    return res, kpi_opt
