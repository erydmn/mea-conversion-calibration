# scripts/run_phase2_grid.py
"""Faz 2: Indirgenmis Model Isletme Zarfi Taramasi (Grid Sweep).

L/G ve alpha_lean uzerinde grid taramasi yaparak sunlari uretir:
  1. Capture(%) heatmap
  2. Ozgul Enerji (MJ/kg) heatmap

Bu grafikler, optimum calisma araligini (sweet spot) belirlemek
ve DWSIM ile olan karsilastirmalarin (Faz 5) zeminini olusturmak
icin kullanilir.
"""
import sys
sys.path.insert(0, ".")

import numpy as np
import matplotlib.pyplot as plt
import yaml
import warnings

from src.equilibrium_stage import calibrate_eta
from src.reduced_model import run_grid
from src.plotting import setup_dark_style, add_watermark

setup_dark_style()

# --- Config oku ---
with open("config.yaml") as f:
    cfg = yaml.safe_load(f)
nom = cfg['nominal']
env = cfg['envelope']

# =========================================================================
# 1. Kalibrasyon ve Grid Calistirma
# =========================================================================
print("=== FAZ 2: GRID SWEEP ===")
print("Model kalibre ediliyor...")
eta_abs, eta_reg, cal_info = calibrate_eta(nom)
print(f"  eta_abs = {eta_abs:.4f}, eta_reg = {eta_reg:.4f}")

# Grid boyutlari
n_LG = 30
n_aL = 30

print(f"\nGrid calistiriliyor ({n_LG} x {n_aL} = {n_LG * n_aL} nokta)...")
results = run_grid(cfg, eta_abs, eta_reg, n_LG, n_aL)

# =========================================================================
# 2. Verileri Matrislere Donusturme
# =========================================================================
LG_vals = sorted(list(set([r['L_over_G'] for r in results])))
aL_vals = sorted(list(set([r['alpha_lean'] for r in results])))

LG_mesh, aL_mesh = np.meshgrid(LG_vals, aL_vals, indexing='ij')

capture_grid = np.zeros((n_LG, n_aL))
energy_grid = np.zeros((n_LG, n_aL))

for r in results:
    i = LG_vals.index(r['L_over_G'])
    j = aL_vals.index(r['alpha_lean'])
    capture_grid[i, j] = r['capture_pct']
    energy_grid[i, j] = r['specific_reboiler_MJkg']

# Fiziksel olmayan veya mantiksiz (X < 0 vb.) sonuclari filtrele
capture_grid = np.where(capture_grid < 0, np.nan, capture_grid)
capture_grid = np.where(capture_grid > 100, np.nan, capture_grid)
energy_grid = np.where(energy_grid <= 0, np.nan, energy_grid)
energy_grid = np.where(energy_grid > 20, np.nan, energy_grid) # 20 MJ/kg ustu pratik degil

# =========================================================================
# 3. Heatmap Grafikleri
# =========================================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

# Nominal L/G (molar)
LG_nom = nom.get('L_over_G_nominal', 3.41)

# (a) Capture Pct
c1 = ax1.contourf(aL_mesh, LG_mesh, capture_grid, levels=20, cmap='viridis')
cbar1 = fig.colorbar(c1, ax=ax1)
cbar1.set_label("CO2 Yakalama (%)")
# Kontur cizgileri (ozellikle %90)
cs1 = ax1.contour(aL_mesh, LG_mesh, capture_grid, levels=[70, 80, 85, 90, 95],
                  colors='white', alpha=0.5, linestyles='dashed')
ax1.clabel(cs1, inline=True, fontsize=10, colors='white')
ax1.plot([nom['lean_loading']], [LG_nom],
         'r*', ms=12, label='Nominal')
ax1.set_xlabel("Yalin Yukleme, alpha_lean (mol/mol)")
ax1.set_ylabel("L/G Orani (mol MEA/mol gaz)")
ax1.set_title("CO2 Yakalama Verimi (%)")
ax1.legend()
add_watermark(ax1)

# (b) Specific Reboiler Energy
# Enerjiyi kucuk olan (iyisi) koyu gosterecek sekilde coolwarm kullanalim
# Ters yonde
c2 = ax2.contourf(aL_mesh, LG_mesh, energy_grid, levels=np.linspace(3, 10, 20),
                  cmap='plasma_r', extend='max')
cbar2 = fig.colorbar(c2, ax=ax2)
cbar2.set_label("Ozgul Enerji (MJ/kg CO2)")
# Kontur cizgileri
cs2 = ax2.contour(aL_mesh, LG_mesh, energy_grid, levels=[3.0, 3.5, 4.0, 5.0, 7.0],
                  colors='white', alpha=0.5, linestyles='dashed')
ax2.clabel(cs2, inline=True, fontsize=10, colors='white')
ax2.plot([nom['lean_loading']], [LG_nom],
         'g*', ms=12, label='Nominal')
ax2.set_xlabel("Yalin Yukleme, alpha_lean (mol/mol)")
ax2.set_ylabel("L/G Orani (mol MEA/mol gaz)")
ax2.set_title("Reboiler Ozgul Enerji (MJ/kg CO2)")
ax2.legend()
add_watermark(ax2)

plt.tight_layout()
plt.savefig("results/figures/phase2_heatmaps.png")
print(f"\nHeatmap grafikleri kaydedildi: results/figures/phase2_heatmaps.png")

# KAPI 2
print("\n" + "=" * 60)
print("KAPI 2 DEGERLENDIRMESI")
print("=" * 60)

# Monotonluk testi (Her alpha_lean sutununda L/G arttikca Capture artmali)
# capture_grid sekli: (n_LG, n_aL)
is_monotonic = True
for j in range(n_aL):
    col = capture_grid[:, j]
    valid_col = col[~np.isnan(col)]
    if len(valid_col) > 1:
        # strict monoton yerine >= kabul ediyoruz (nümerik gürültü için +1e-5 tolerans)
        mono = all(valid_col[i] <= valid_col[i+1] + 1e-5 for i in range(len(valid_col)-1))
        if not mono:
            is_monotonic = False
            break

# En dusuk aL ve en yuksek L/G koseyi bul
max_cap_val = np.nanmax(capture_grid)
# En dusuk aL -> indeks 0, En yuksek L/G -> indeks n_LG-1
expected_max = capture_grid[n_LG-1, 0]

is_expected_corner = abs(max_cap_val - expected_max) < 0.1

if is_monotonic and is_expected_corner:
    print("KAPI 2 GECTI: Fiziksel yonelimler tutarli (monotonluk ve kose sartlari saglandi).")
else:
    print(f"KAPI 2 BASARISIZ:")
    print(f"  L/G ekseninde monotonluk: {'GECTI' if is_monotonic else 'KALDI'}")
    print(f"  Max yakalama kosede mi: {'GECTI' if is_expected_corner else 'KALDI'}")
print("=" * 60)
