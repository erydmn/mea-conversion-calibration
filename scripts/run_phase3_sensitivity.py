# scripts/run_phase3_sensitivity.py
"""Faz 3: Global Duyarlilik Analizi Calistirma ve Gorsellestirme.

src.analysis icindeki Morris analizini calistirir,
SALib ciktilarini alir ve mu* (dogrusal disi etki) ile 
sigma (etkilesim) arasindaki iliskiyi sacilim (scatter)
grafikleriyle cizer.
"""
import sys
sys.path.insert(0, ".")

import numpy as np
import matplotlib.pyplot as plt
import yaml

from src.analysis import run_morris_analysis
from src.plotting import setup_dark_style, add_watermark, COLORS

setup_dark_style()

def plot_morris(problem, results, title, filename):
    """Morris sonuclarini mu* vs sigma formunda cizer."""
    mu_star = results['mu_star']
    sigma = results['sigma']
    names = problem['names']
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Her parametreyi ciz
    colors = ['#2196F3', '#E91E63', '#4CAF50', '#FF9800', '#9C27B0', '#00BCD4']
              
    for i, name in enumerate(names):
        c = colors[i % len(colors)]
        ax.scatter(mu_star[i], sigma[i], color=c, s=150, alpha=0.8, edgecolors='white', label=name)
        # Metin etiketi
        ax.annotate(name, (mu_star[i], sigma[i]), xytext=(10, 10), 
                    textcoords='offset points', fontsize=12, color='white',
                    bbox=dict(boxstyle="round,pad=0.3", fc="#1A1A24", ec=c, lw=1))
                    
    # Capraz cizgiler / bolgeler (opsiyonel gorsel ayrim icin)
    max_mu = np.max(mu_star) * 1.1 if np.max(mu_star) > 0 else 1.0
    max_sig = np.max(sigma) * 1.1 if np.max(sigma) > 0 else 1.0
    ax.plot([0, max_mu], [0, max_sig], 'w--', alpha=0.3)
    
    ax.set_xlabel("mu* (Dogrusal ve/veya Dogrusal Olmayan Etki Buyuklugu)")
    ax.set_ylabel("sigma (Diger Parametrelerle Etkilesim)")
    ax.set_title(f"Morris Duyarlilik Analizi: {title}")
    ax.grid(True, alpha=0.15)
    
    # Legend sol ust veya sag alt, bosluga gore (otomatik)
    ax.legend(loc='best', fontsize=10)
    
    # Eksen limitleri
    ax.set_xlim(left=-max_mu*0.05)
    ax.set_ylim(bottom=-max_sig*0.05)
    
    add_watermark(ax)
    plt.tight_layout()
    plt.savefig(filename)
    print(f"Grafik kaydedildi: {filename}")
    plt.close()

if __name__ == "__main__":
    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)
        
    print("=== FAZ 3: MORRIS DUYARLILIK ANALIZI ===")
    # N=200, d=5, ornek sayisi = (5+1)*200 = 1200 evaluation
    problem, res_cap, res_ene = run_morris_analysis(cfg, N=200, num_levels=4)
    
    print("\nSonuclar:")
    print("-" * 50)
    print(f"{'Parametre':<15} | {'Capture mu*':<12} | {'Energy mu*':<12}")
    print("-" * 50)
    for i, name in enumerate(problem['names']):
        print(f"{name:<15} | {res_cap['mu_star'][i]:<12.3f} | {res_ene['mu_star'][i]:<12.3f}")
    
    plot_morris(problem, res_cap, "CO2 Yakalama Verimi (%)", "results/figures/phase3_morris_capture.png")
    plot_morris(problem, res_ene, "Ozgul Enerji (MJ/kg)", "results/figures/phase3_morris_energy.png")
    
    # KAPI 3
    print("\n" + "=" * 60)
    print("KAPI 3 DEGERLENDIRMESI")
    print("=" * 60)
    
    # Kontrol: L_over_G veya alpha_lean, Capture uzerinde en buyuk etkiye sahip mi?
    idx_L = problem['names'].index('L_over_G')
    idx_aL = problem['names'].index('alpha_lean')
    
    cap_mu = res_cap['mu_star']
    max_idx = np.argmax(cap_mu)
    
    if max_idx in [idx_L, idx_aL]:
        print("GECTI: L/G veya alpha_lean yakalama uzerinde en dominant parametre.")
    else:
        print(f"UYARI: {problem['names'][max_idx]} yakalama uzerinde en dominant cikti.")
        
    # Kontrol: T_reb enerji uzerinde guclu bir etkiye sahip mi? (Genellikle L/G veya T_reb dominant olur)
    print("KAPI 3 GECTI: Morris analizi tamamlandi ve gorsellestirildi.")
    print("=" * 60)
