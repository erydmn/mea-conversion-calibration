# src/plotting.py
"""Ortak grafik yardimci fonksiyonlari.

Tum proje genelinde tutarli, profesyonel gorsel stili saglar.
Koyu tema, renk paleti ve standart grafik ayarlari.
"""
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np


# =========================================================================
# Proje geneli gorsel sabitleri
# =========================================================================

# Renk paleti (derisimlere/kaynaklara gore)
COLORS = {
    'primary':     '#2196F3',   # mavi - birincil veri
    'cross_check': '#FF9800',   # turuncu - capraz kontrol
    'validation':  '#4CAF50',   # yesil - dogrulama
    'model':       '#E91E63',   # pembe - model tahmini
    'ideal':       '#FFFFFF',   # beyaz - y=x cizgisi
    'band':        '#FF5722',   # kirmizi - hata bandi
}

# Sicakliga gore renk
T_COLORS = {
    313: '#2196F3',   # mavi
    333: '#4CAF50',   # yesil
    353: '#FF9800',   # turuncu
    373: '#E91E63',   # pembe
    393: '#9C27B0',   # mor
}

# MEA derimine gore isaret
MEA_MARKERS = {
    0.15:  'o',
    0.153: 'o',
    0.20:  's',
    0.30:  '^',
    0.45:  'D',
    0.60:  'v',
}


def setup_dark_style():
    """Koyu tema stil ayarlari.
    Tum scripts/run_phaseX_*.py betiklerinin basinda cagirilmali.
    """
    plt.style.use('dark_background')
    mpl.rcParams.update({
        'figure.facecolor': '#1a1a2e',
        'axes.facecolor':   '#16213e',
        'axes.edgecolor':   '#e94560',
        'axes.labelcolor':  '#e0e0e0',
        'text.color':       '#e0e0e0',
        'xtick.color':      '#a0a0a0',
        'ytick.color':      '#a0a0a0',
        'grid.color':       '#333355',
        'grid.alpha':       0.3,
        'font.size':        11,
        'axes.titlesize':   13,
        'axes.labelsize':   12,
        'figure.dpi':       150,
        'savefig.dpi':      300,
        'savefig.facecolor': '#1a1a2e',
        'savefig.bbox':     'tight',
    })


def get_T_color(T_K):
    """Sicakliga gore renk dondur (en yakin isarete).

    Parameters
    ----------
    T_K : float
        Sicaklik [K]

    Returns
    -------
    color : str
        Hex renk kodu
    """
    T_rounded = round(T_K)
    return T_COLORS.get(T_rounded, '#AAAAAA')


def get_mea_marker(mea_wt):
    """MEA kutle kesrine gore isaret dondur.

    Parameters
    ----------
    mea_wt : float
        MEA kutle kesri (0-1)

    Returns
    -------
    marker : str
        matplotlib isaret kodu
    """
    # En yakin deger
    closest = min(MEA_MARKERS.keys(), key=lambda x: abs(x - mea_wt))
    return MEA_MARKERS[closest]


def parity_bands(ax, lims, bands=[0.30]):
    """Parite grafigin y=x ve +/- bant cizgileri ekle.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Grafik ekseni
    lims : tuple
        (xmin, xmax) sinirlar
    bands : list
        Bant yuzdeleri (varsayilan +/- %30)
    """
    ax.loglog(lims, lims, '--', color=COLORS['ideal'], alpha=0.7,
              linewidth=1.5, label='y = x')
    for b in bands:
        ax.loglog(lims, [l * (1 + b) for l in lims], ':',
                  color=COLORS['band'], alpha=0.4, linewidth=1)
        ax.loglog(lims, [l * (1 - b) for l in lims], ':',
                  color=COLORS['band'], alpha=0.4)


def add_watermark(ax, text="KE Model v1.0"):
    """Grafige sag alt koseye filigran ekle."""
    ax.text(0.98, 0.02, text, transform=ax.transAxes,
            fontsize=8, alpha=0.3, ha='right', va='bottom',
            style='italic', color='#888888')
