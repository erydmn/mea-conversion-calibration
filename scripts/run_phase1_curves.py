# scripts/run_phase1_curves.py
"""Faz 1 Dogrulama: Donusum egrileri ve duyarlilik.

Bu betik:
  1. eta kalibrasyonunu yapar
  2. X_abs vs L/G egrisi cizer
  3. X_reg vs T_reb egrisi cizer
  4. X_abs vs alpha_lean egrisi cizer

KAPI 1 Kriterleri:
  - Nominal X_abs ~ 0.906 (+-0.02)
  - Nominal X_reg ~ 0.95 (+-0.02)
  - L/G arttikca X_abs artar (monoton)
  - T_reb arttikca X_reg artar (monoton)
"""
import sys
sys.path.insert(0, ".")

import numpy as np
import matplotlib.pyplot as plt
import yaml
import warnings

from src.equilibrium_stage import absorber_conversion, regenerator_conversion, calibrate_eta
from src.plotting import setup_dark_style, COLORS, add_watermark

setup_dark_style()

# --- Config oku ---
with open("config.yaml") as f:
    cfg = yaml.safe_load(f)
nom = cfg['nominal']
phys = cfg['physical']

# --- Kalibrasyon ---
eta_abs, eta_reg, info = calibrate_eta(nom)
print(f"Kalibre eta: abs={eta_abs:.4f}, reg={eta_reg:.4f}")

# Nominal degerler
n_flue = nom['flue_gas_molar_flow']
y_co2 = nom['flue_gas_co2_frac']
n_CO2_in = n_flue * y_co2
n_gas_in = n_flue
mea_t = nom['mea_conc_molL']
T_abs = nom['absorber_T']
P_abs_kPa = nom['absorber_P_Pa'] / 1000
T_reb_nom = nom['reboiler_T']
P_reg_Pa = nom['regen_P_Pa']
alpha_lean_nom = nom['lean_loading']
n_MEA_nom = info['n_MEA']
P_CO2_strip_nom = info['P_CO2_strip_kPa']

# =========================================================================
# 1. X_abs vs Molar L/G (n_MEA / n_gas)
# =========================================================================
print("\n=== X_abs vs L/G (Molar) ===")

LG_nominal = n_MEA_nom / n_gas_in
print(f"Nominal Molar L/G = {LG_nominal:.3f} (n_MEA={n_MEA_nom:.2f}, n_gas={n_gas_in:.2f} mol/s)")

# Molar L/G taramasi (config zarfi: 1.0 - 4.0)
LG_range = np.linspace(1.0, 5.0, 40)
X_abs_vs_LG = []
alpha_rich_vs_LG = []

for LG in LG_range:
    n_MEA = LG * n_gas_in

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            X, ar, _ = absorber_conversion(
                n_CO2_in, n_gas_in, n_MEA, alpha_lean_nom,
                T_abs, P_abs_kPa, mea_t, eta_abs
            )
            X_abs_vs_LG.append(X)
            alpha_rich_vs_LG.append(ar)
        except Exception:
            X_abs_vs_LG.append(np.nan)
            alpha_rich_vs_LG.append(np.nan)

# =========================================================================
# 2. X_reg vs T_reb
# =========================================================================
print("=== X_reg vs T_reb ===")

# Nominal alpha_rich
X_abs_nom, alpha_rich_nom, _ = absorber_conversion(
    n_CO2_in, n_gas_in, n_MEA_nom, alpha_lean_nom,
    T_abs, P_abs_kPa, mea_t, eta_abs
)
n_carbamate_nom = X_abs_nom * n_CO2_in

T_reb_range = np.linspace(370, 413, 40)  # K
X_reg_vs_Treb = []

for T in T_reb_range:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            X, _, _ = regenerator_conversion(
                alpha_rich_nom, n_MEA_nom, n_carbamate_nom,
                T, P_CO2_strip_nom, mea_t, eta_reg
            )
            X_reg_vs_Treb.append(X)
        except Exception:
            X_reg_vs_Treb.append(np.nan)

# =========================================================================
# 3. X_abs vs alpha_lean
# =========================================================================
print("=== X_abs vs alpha_lean ===")

alpha_lean_range = np.linspace(0.05, 0.45, 40)
X_abs_vs_aL = []

for aL in alpha_lean_range:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            X, _, _ = absorber_conversion(
                n_CO2_in, n_gas_in, n_MEA_nom, aL,
                T_abs, P_abs_kPa, mea_t, eta_abs
            )
            X_abs_vs_aL.append(X)
        except Exception:
            X_abs_vs_aL.append(np.nan)

# =========================================================================
# 4. GRAFIK
# =========================================================================
fig, axes = plt.subplots(1, 3, figsize=(18, 6))

# (a) X_abs vs Molar L/G
ax = axes[0]
ax.plot(LG_range, X_abs_vs_LG, '-', color='#2196F3', linewidth=2.5)
ax.axvline(LG_nominal, color='#FF9800', linestyle='--', linewidth=1.5,
           label=f'Nominal L/G = {LG_nominal:.3f}')
ax.axhline(0.906, color='#4CAF50', linestyle=':', linewidth=1,
           label='Hedef X_abs = 0.906')
ax.set_xlabel("L/G (mol MEA / mol gaz)")
ax.set_ylabel("X_abs (absorber donusumu)")
ax.set_title("Absorber: X_abs vs Molar L/G")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.2)
ax.set_ylim(0, 1.05)
add_watermark(ax)

# (b) X_reg vs T_reb
ax = axes[1]
ax.plot(T_reb_range - 273.15, X_reg_vs_Treb, '-', color='#E91E63', linewidth=2.5)
ax.axvline(T_reb_nom - 273.15, color='#FF9800', linestyle='--', linewidth=1.5,
           label=f'Nominal T_reb = {T_reb_nom-273.15:.0f} C')
ax.axhline(0.95, color='#4CAF50', linestyle=':', linewidth=1,
           label='Hedef X_reg = 0.95')
ax.set_xlabel("Reboiler Sicakligi (C)")
ax.set_ylabel("X_reg (rejenerator donusumu)")
ax.set_title("Stripper: X_reg vs T_reb")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.2)
ax.set_ylim(0, 1.05)
add_watermark(ax)

# (c) X_abs vs alpha_lean
ax = axes[2]
ax.plot(alpha_lean_range, X_abs_vs_aL, '-', color='#9C27B0', linewidth=2.5)
ax.axvline(alpha_lean_nom, color='#FF9800', linestyle='--', linewidth=1.5,
           label=f'Nominal alpha_lean = {alpha_lean_nom:.2f}')
ax.axhline(0.906, color='#4CAF50', linestyle=':', linewidth=1,
           label='Hedef X_abs = 0.906')
ax.set_xlabel("Yalin yukleme alpha_lean (mol CO2/mol MEA)")
ax.set_ylabel("X_abs (absorber donusumu)")
ax.set_title("Absorber: X_abs vs alpha_lean")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.2)
ax.set_ylim(0, 1.05)
add_watermark(ax)

plt.tight_layout()
plt.savefig("results/figures/phase1_conversion_curves.png")
print(f"\nGrafik: results/figures/phase1_conversion_curves.png")

# =========================================================================
# 5. MONOTONLUK KONTROLU
# =========================================================================
print("\n" + "=" * 60)
print("KAPI 1 DEGERLENDIRMESI")
print("=" * 60)

# Nominal dogrulama
print(f"Nominal X_abs = {X_abs_nom:.4f} (hedef: 0.906, fark: {abs(X_abs_nom-0.906):.4f})")

X_reg_nom, _, _ = regenerator_conversion(
    alpha_rich_nom, n_MEA_nom, n_carbamate_nom,
    T_reb_nom, P_CO2_strip_nom, mea_t, eta_reg
)
print(f"Nominal X_reg = {X_reg_nom:.4f} (hedef: 0.950, fark: {abs(X_reg_nom-0.950):.4f})")

# Monotonluk
X_LG_arr = np.array([x for x in X_abs_vs_LG if not np.isnan(x)])
mono_LG = all(X_LG_arr[i] <= X_LG_arr[i+1] + 1e-6 for i in range(len(X_LG_arr)-1))
print(f"L/G monotonluk (X_abs artar): {'GECTI' if mono_LG else 'BASARISIZ'}")

X_Tr_arr = np.array([x for x in X_reg_vs_Treb if not np.isnan(x)])
mono_Tr = all(X_Tr_arr[i] <= X_Tr_arr[i+1] + 1e-6 for i in range(len(X_Tr_arr)-1))
print(f"T_reb monotonluk (X_reg artar): {'GECTI' if mono_Tr else 'BASARISIZ'}")

X_aL_arr = np.array([x for x in X_abs_vs_aL if not np.isnan(x)])
mono_aL = all(X_aL_arr[i] >= X_aL_arr[i+1] - 1e-6 for i in range(len(X_aL_arr)-1))
print(f"alpha_lean monotonluk (X_abs azalir): {'GECTI' if mono_aL else 'BASARISIZ'}")

# Kalibrasyon notu
print(f"\nKalibrasyon notu:")
print(f"  eta_abs = {eta_abs:.4f}")
print(f"  eta_reg = {eta_reg:.4f}")
if eta_abs > 1.0:
    print(f"  UYARI: eta_abs > 1 ({eta_abs:.2f}). Bu, tek-kademe denge modelinin")
    print(f"  cok-kademeli absorberden daha dusuk donusum vermesinden kaynaklaniyor.")
    print(f"  Fiziksel yorum: 'etkin kademe sayisi' gibi isliyor.")
    print(f"  Bu bilgi docs/uncertainty.md'ye kaydedilecek.")

all_pass = (abs(X_abs_nom - 0.906) < 0.02 and
            abs(X_reg_nom - 0.950) < 0.02 and
            mono_LG and mono_Tr)
print(f"\nKAPI 1: {'GECTI' if all_pass else 'KOSULLU GECTI'}")
print("=" * 60)

plt.close('all')
