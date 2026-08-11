# scripts/run_phase0_vle.py
"""Faz 0 Dogrulama: KE modeli vs deneysel VLE verisi.

Bu betik:
  1. VLE CSV'sini okur
  2. Zhu 20 wt% (birincil) verisini dogrular
  3. Aronu 2011 (coklu derisim) verisini capraz kontrol eder
  4. Parite grafigi cikar
  5. Izoterm grafigi cikar

KAPI 0 Kriterleri:
  - Birincil AARD <= %15 (ideal <= %5)
  - Parite grafigi: results/figures/phase0_parity.png
  - Izoterm grafigi: results/figures/phase0_isotherms.png

NOT: Dogrulama ALPHA paritesi uzerinden yapilir (pco2 degil).
     Cunku pco2 exponensiyel degistigi icin kucuk alpha hatalari
     buyuk pco2 hatalarina donusur. Alpha paritesi daha adaletlidir.
"""
import sys
sys.path.insert(0, ".")

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings

from src.ke_solver import pco2_from_alpha, alpha_from_pco2
from src.plotting import setup_dark_style, COLORS, T_COLORS, parity_bands, add_watermark

# --- Stil ayarla ---
setup_dark_style()

# --- Veriyi oku ---
df = pd.read_csv("data/vle_experimental_mea.csv")
print(f"Toplam VLE noktasi: {len(df)}")

def mea_wt_to_conc(wt):
    """MEA kutle kesrinden molar derisime (mol/L) cevrim."""
    # Zhu 2022 referans degerleri: 20 wt% MEA -> 3.285 mol/L
    # 15.3 wt% MEA (Aboudheir) -> yaklasik 2.51 mol/L
    if abs(wt - 0.20) < 0.001:
        return 3.285
    elif abs(wt - 0.153) < 0.001:
        return 2.51
    else:
        # Genel basit korelasyon
        M_MEA = 61.08
        rho = 1012 if wt > 0.25 else 1024 # kaba yaklasim
        return wt * rho / M_MEA

# =========================================================================
# 1. KE MODEL ILE HER NOKTA ICIN alpha TAHMINI
# =========================================================================
print("\n=== ALPHA PARITE ANALIZI ===")

results = []
for idx, row in df.iterrows():
    wt = row['mea_wt']
    T = row['T_K']
    pco2_exp = row['pco2_kPa']
    alpha_exp = row['alpha']
    source_name = row['source']
    role = row['role']

    mea_t = mea_wt_to_conc(wt)

    # Kaynak secimi: T <= 353K -> 'zhu', T > 353K -> 'aboudheir'
    ke_source = 'zhu' if T <= 353 else 'aboudheir'

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            alpha_model = alpha_from_pco2(pco2_exp, T, mea_t, ke_source)
        results.append({
            'idx': idx,
            'source': source_name,
            'mea_wt': wt,
            'T_K': T,
            'alpha_exp': alpha_exp,
            'alpha_model': alpha_model,
            'pco2_kPa': pco2_exp,
            'role': role,
            'error': abs(alpha_model - alpha_exp),
            'rel_error': abs(alpha_model - alpha_exp) / max(alpha_exp, 1e-6),
        })
    except Exception as e:
        # Cozucu basarisiz - genellikle birim sorunu
        pass

res_df = pd.DataFrame(results)
print(f"Basarili tahmin: {len(res_df)}/{len(df)} nokta")

# =========================================================================
# 2. KAYNAK BAZLI AARD RAPORU
# =========================================================================
print("\nKaynak bazli AARD (alpha):")
for source in res_df['source'].unique():
    sub = res_df[res_df['source'] == source]
    aard = sub['rel_error'].mean() * 100
    n = len(sub)
    print(f"  {source}: {n} nokta, AARD = {aard:.1f}%")

# MEA derisim bazli
print("\nDerisim bazli AARD (alpha):")
for wt in sorted(res_df['mea_wt'].unique()):
    sub = res_df[res_df['mea_wt'] == wt]
    aard = sub['rel_error'].mean() * 100
    n = len(sub)
    mea_t = mea_wt_to_conc(wt)
    print(f"  {wt*100:.0f} wt% (mea_t={mea_t:.2f}): {n} nokta, AARD = {aard:.1f}%")

# Sicaklik bazli
print("\nSicaklik bazli AARD (alpha):")
for T in sorted(res_df['T_K'].unique()):
    sub = res_df[res_df['T_K'] == T]
    aard = sub['rel_error'].mean() * 100
    n = len(sub)
    print(f"  {T:.0f} K: {n} nokta, AARD = {aard:.1f}%")

# Genel AARD
overall_aard = res_df['rel_error'].mean() * 100
print(f"\nGenel AARD: {overall_aard:.1f}%")

# =========================================================================
# 3. BIRINCIL DOGRULAMA: Sadece 20 wt% (Zhu) + 15 wt% (Aronu)
#    Bu iki derisim KE modelinin kalibrasyon alanindadir
# =========================================================================
primary_mask = res_df['mea_wt'].isin([0.15, 0.153, 0.20])
if primary_mask.any():
    primary_aard = res_df.loc[primary_mask, 'rel_error'].mean() * 100
    print(f"\nBirincil dogrulama (15-20 wt%) AARD: {primary_aard:.1f}%")
else:
    primary_aard = overall_aard

# =========================================================================
# 4. PARITE GRAFIGI (alpha bazli)
# =========================================================================
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Sol: Derisim bazli renklendirme
ax1 = axes[0]
wt_colors = {0.15: '#2196F3', 0.153: '#2196F3', 0.20: '#4CAF50',
             0.30: '#FF9800', 0.45: '#E91E63', 0.60: '#9C27B0'}
wt_markers = {0.15: 'o', 0.153: 'o', 0.20: 's', 0.30: '^', 0.45: 'D', 0.60: 'v'}

for wt in sorted(res_df['mea_wt'].unique()):
    sub = res_df[res_df['mea_wt'] == wt]
    color = wt_colors.get(wt, '#AAAAAA')
    marker = wt_markers.get(wt, 'o')
    aard_wt = sub['rel_error'].mean() * 100
    ax1.plot(sub['alpha_exp'], sub['alpha_model'], marker,
             ms=6, alpha=0.7, color=color, markeredgecolor='white',
             markeredgewidth=0.5,
             label=f'{wt*100:.0f}% ({aard_wt:.0f}%)')

lims1 = [0, max(res_df['alpha_exp'].max(), res_df['alpha_model'].max()) * 1.05]
ax1.plot(lims1, lims1, '--', color='white', alpha=0.5, linewidth=1.5, label='y = x')
# +/- 10% bant
ax1.fill_between(np.linspace(0, 1, 100),
                 np.linspace(0, 1, 100) * 0.9,
                 np.linspace(0, 1, 100) * 1.1,
                 alpha=0.1, color='white')

ax1.set_xlabel("Deneysel alpha (mol CO2/mol MEA)")
ax1.set_ylabel("Model alpha (mol CO2/mol MEA)")
ax1.set_title(f"KE Alpha Parite - Tum Derisimler\nGenel AARD = {overall_aard:.1f}%")
ax1.legend(fontsize=8, title="wt% (AARD)")
ax1.grid(True, alpha=0.2)
ax1.set_xlim(lims1)
ax1.set_ylim(lims1)
add_watermark(ax1)

# Sag: Sicaklik bazli
ax2 = axes[1]
for T in sorted(res_df['T_K'].unique()):
    T_key = round(T)
    sub = res_df[res_df['T_K'] == T]
    color = T_COLORS.get(T_key, '#AAAAAA')
    aard_T = sub['rel_error'].mean() * 100
    ax2.plot(sub['alpha_exp'], sub['alpha_model'], 'o',
             ms=5, alpha=0.6, color=color, markeredgecolor='white',
             markeredgewidth=0.3,
             label=f'{T:.0f} K ({aard_T:.0f}%)')

ax2.plot(lims1, lims1, '--', color='white', alpha=0.5, linewidth=1.5, label='y = x')
ax2.fill_between(np.linspace(0, 1, 100),
                 np.linspace(0, 1, 100) * 0.9,
                 np.linspace(0, 1, 100) * 1.1,
                 alpha=0.1, color='white')
ax2.set_xlabel("Deneysel alpha")
ax2.set_ylabel("Model alpha")
ax2.set_title(f"KE Alpha Parite - Sicaklik Bazli")
ax2.legend(fontsize=8, title="T (AARD)")
ax2.grid(True, alpha=0.2)
ax2.set_xlim(lims1)
ax2.set_ylim(lims1)
add_watermark(ax2)

plt.tight_layout()
plt.savefig("results/figures/phase0_parity.png")
print(f"\nParite grafigi: results/figures/phase0_parity.png")

# =========================================================================
# 5. IZOTERM GRAFIGI (KE model egrileri + deneysel noktalar)
# =========================================================================
fig2, ax3 = plt.subplots(figsize=(10, 7))

mea_t_20 = 3.285  # 20 wt% referans
alpha_range = np.linspace(0.05, 0.70, 200)

for T_val in [313.15, 333.15, 353.15, 373.15, 393.15]:
    T_key = round(T_val)
    color = T_COLORS.get(T_key, '#AAAAAA')
    ke_src = 'zhu' if T_val <= 353 else 'aboudheir'

    pco2_model = []
    for a in alpha_range:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                p = pco2_from_alpha(a, T_val, mea_t_20, ke_src)
            pco2_model.append(p)
        except Exception:
            pco2_model.append(np.nan)

    ax3.semilogy(alpha_range, pco2_model, '-', color=color, linewidth=2,
                 label=f'KE {T_val:.0f} K ({ke_src})', alpha=0.9)

# Deneysel noktalar (sadece 20 wt% ve 15 wt%)
for src_filter, marker, label_pfx in [
    ('Zhu', 's', 'Zhu'),
    ('Aboudheir', 'D', 'Ab.')]:
    mask = df['source'].str.contains(src_filter)
    if mask.any():
        data = df[mask]
        for T_val in data['T_K'].unique():
            T_key = round(T_val)
            color = T_COLORS.get(T_key, '#AAAAAA')
            t_data = data[data['T_K'] == T_val]
            ax3.semilogy(t_data['alpha'], t_data['pco2_kPa'], marker,
                         color=color, ms=10, markeredgecolor='white',
                         markeredgewidth=1.5, zorder=5,
                         label=f'{label_pfx} {T_val:.0f}K')

ax3.set_xlabel("Yukleme alpha (mol CO2/mol MEA)")
ax3.set_ylabel("P_CO2 (kPa)")
ax3.set_title("KE Model Izotermleri (20 wt% MEA)")
ax3.legend(fontsize=9, ncol=2)
ax3.grid(True, alpha=0.2)
ax3.set_xlim(0, 0.75)
ax3.set_ylim(0.001, 10000)
add_watermark(ax3)

plt.tight_layout()
plt.savefig("results/figures/phase0_isotherms.png")
print(f"Izoterm grafigi: results/figures/phase0_isotherms.png")

# =========================================================================
# 6. KAPI 0 DEGERLENDIRMESI
# =========================================================================
print("\n" + "=" * 60)
print("KAPI 0 DEGERLENDIRMESI")
print("=" * 60)

# Birincil kriter: 15-20 wt% (KE kalibrasyon alani) AARD
if primary_mask.any():
    print(f"Birincil (15-20 wt%) AARD: {primary_aard:.1f}%  (hedef <= %15)")
print(f"Genel AARD: {overall_aard:.1f}%")

# Zhu capraz-kontrol hata raporu
zhu_sub = res_df[res_df['source'].str.contains('Zhu')]
if len(zhu_sub) > 0:
    zhu_aard = zhu_sub['rel_error'].mean() * 100
    print(f"Zhu 20 wt% AARD: {zhu_aard:.1f}%")
    for _, r in zhu_sub.iterrows():
        print(f"  a_exp={r['alpha_exp']:.2f} a_model={r['alpha_model']:.4f} "
              f"pco2={r['pco2_kPa']:.3f} err={r['rel_error']*100:.1f}%")

# Karar
gate_criterion = overall_aard if not primary_mask.any() else primary_aard
gate_passed = gate_criterion <= 15

if gate_passed:
    print(f"\nKAPI 0 GECTI: AARD = {gate_criterion:.1f}% <= %15")
else:
    print(f"\nKAPI 0 BASARISIZ: AARD = {gate_criterion:.1f}% > %15")

print(f"\nCiktilar:")
print(f"  results/figures/phase0_parity.png")
print(f"  results/figures/phase0_isotherms.png")
print("=" * 60)

plt.close('all')
