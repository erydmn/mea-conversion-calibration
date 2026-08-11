"""VLE CSV veri dogrulayici.
data/vle_experimental_mea.csv'nin gecerliligi kontrol edilir.
"""
import pandas as pd
import sys

df = pd.read_csv("data/vle_experimental_mea.csv")
problems = []

# Zorunlu sutun kontrolu
required_cols = ['source', 'mea_wt', 'T_K', 'alpha', 'pco2_kPa', 'role']
for col in required_cols:
    if col not in df.columns:
        problems.append(f"Eksik sutun: {col}")

if problems:
    print("SORUNLAR:", problems)
    sys.exit(1)

# NaN kontrolu (kritik sutunlarda)
if df[['mea_wt', 'T_K', 'alpha', 'pco2_kPa']].isnull().any().any():
    problems.append("NaN var (muhtemelen ondalik virgul sorunu)")

# alpha [0, 1] araliginda olmali
if not df['alpha'].between(0, 1).all():
    bad = list(df.index[~df['alpha'].between(0, 1)])
    problems.append(f"alpha [0,1] disinda: satirlar {bad}")

# pco2 > 0 olmali
if not (df['pco2_kPa'] > 0).all():
    problems.append("pco2_kPa <= 0 var")

# mea_wt [0, 1] araliginda olmali (kutle kesri)
if not df['mea_wt'].between(0, 1).all():
    bad_mea = list(df.index[~df['mea_wt'].between(0, 1)])
    problems.append(f"mea_wt [0,1] disinda: satirlar {bad_mea}")

# T_K makul aralikta olmali
if not df['T_K'].between(273, 500).all():
    problems.append("T_K [273,500] disinda")

# Ozet tablo
print(df[['source', 'mea_wt', 'T_K', 'alpha', 'pco2_kPa', 'role']].to_string())
print(f"\nToplam: {len(df)} satir")
print(f"Kaynaklar: {df['source'].unique().tolist()}")
print(f"mea_wt degerleri: {sorted(df['mea_wt'].unique())}")
print(f"T_K degerleri: {sorted(df['T_K'].unique())}")

if problems:
    print(f"\nSONUC: SORUNLU - {problems}")
    sys.exit(1)
else:
    print("\nSONUC: TEMIZ (tum kontroller gecti)")
    sys.exit(0)
