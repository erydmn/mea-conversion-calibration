# MEA CO₂ Tutma — Tam Hesaplama ve Modelleme Referansı
### Her sayı, her denklem, her literatür verisi, her DWSIM değeri — baştan sona, sırayla

> **Bu dosya nedir?** `MEA_Conversion_Calibration_PLAN.md` *ne yapacağını* anlatır; bu dosya *hangi sayıyı nereye koyacağını ve hangi denklemi nasıl yazacağını* anlatır. Kod yazarken açık tutacağın referans budur. Sıra önemlidir — yukarıdan aşağıya oku.

---

# BÖLÜM A — Nasıl çalışacaksın: ortam, araçlar, veri akışı

Kod yazmadan önce *nerede* çalışacağını netleştir. Bu proje iki tür işten oluşur ve bunlar farklı yerlerde çalışır.

## A.1 — Ne nerede çalışır?

| Katman | Nerede yazılır/çalışır | DWSIM gerekir mi? | İşletim sistemi |
|---|---|---|---|
| KE modeli, denge kademesi, indirgenmiş model, analiz, optimizasyon, grafik | Saf Python (VS Code / herhangi bir IDE / terminal) | **Hayır** | Windows / Linux / Mac — hepsi olur |
| DWSIM doğrulama tezgahı (`dwsim_harness.py`) | Python + pythonnet, DWSIM kurulu | **Evet** | **Windows** (DWSIM Automation .NET üzerinden) |

Önemli sonuç: projenin **%80'i (Faz 0, 1, 3, 4) DWSIM olmadan çalışır.** DWSIM'e yalnızca Faz 2'deki seyrek doğrulama noktalarında ihtiyacın var. Bu yüzden KE motorunu ve analizi önce tamamen Python'da kur, DWSIM'i en sona bırak.

## A.2 — DWSIM'i iki şekilde kullanacaksın

**(1) DWSIM GUI (elle) — anlama ve doğrulama için.** `Flowsheet.dwxmz`'yi çift tıkla, aç. Burada yapacakların:
- Baseline'ı doğrula (F5 ile hesapla, akım değerlerinin BÖLÜM C'deki tabloyla eştiğini gör).
- Reaksiyon ayarlarını oku: menüden *Simulation → Reactions* → iki reaksiyonun dönüşüm ifadesini (`90`, `95`) ve baz bileşenini gör.
- Reaktör ayarlarını oku: RCONV-1 / RCONV-2'ye çift tıkla → hangi reaksiyon setini kullandığını, çalışma modunu (adyabatik) gör.
- Bağlantıları izle: hangi akım nereye gidiyor.

**(2) DWSIM Automation (pythonnet ile — başsız, Python'dan sürülür).** Faz 2'de senaryoları otomatik çözmek için. Kurulum kalıbı (PhysSep-C3'teki gibi):

```python
# dwsim_harness.py — kurulum iskeleti
import pythonnet
pythonnet.load("coreclr")                      # .NET 8 runtime
import clr, System
from System.Globalization import CultureInfo
System.Threading.Thread.CurrentThread.CurrentCulture = CultureInfo.InvariantCulture  # TÜRKÇE LOCALE ŞART

dwsim_path = r"C:\Program Files\DWSIM"
clr.AddReference(dwsim_path + r"\DWSIM.Automation.dll")
clr.AddReference(dwsim_path + r"\DWSIM.Interfaces.dll")
from DWSIM.Automation import Automation2

interf = Automation2()
sim = interf.LoadFlowsheet(r"...\Flowsheet.dwxmz")

# Bir akıma erişim (tag ile):
stream = sim.GetFlowsheetSimulationObject("Flue Gas")
# Bir reaksiyonun dönüşümünü ayarlama:
# sim.Reactions[reaksiyon_id].Expression = "90.6"
# Hesapla:
interf.CalculateFlowsheet2(sim)
# Sonuç oku: stream.GetOverallComposition(), .GetTemperature(), .GetMolarFlow() vb.
```

> Not: Tam API isimleri DWSIM sürümüne göre değişebilir; GUI'de bir kez çözüp objeleri gördükten sonra teyit et. `Reactions` sözlüğünün anahtarı reaksiyonun GUID/adıdır — GUI'den ya da `sim.Reactions.Keys` ile bul.

## A.3 — Veri akış şeması (nereden nereye)

```
BÖLÜM B (bu dosya)  ──► kent_eisenberg.py içine SABİT olarak gömülür
BÖLÜM C (bu dosya)  ──► config.yaml içine nominal değer olarak yazılır
Deneysel VLE (§B.5) ──► data/vle_experimental_mea.csv  (sen sağlayacaksın)
        │
KE motoru (Python) ──► dönüşümler X_abs, X_reg  ──► (aynı süreçte) DWSIM harness
        │                                                    │
        └──► reduced_model grid ──► results/data/*.parquet ◄─┘ (DWSIM sonuçları)
                                          │
                                    analysis.py ──► results/figures/*.png
```

## A.4 — Birim sözleşmesi (BUNU BİR KEZ SABİTLE, HER YERDE UYGULA)

Hataların %90'ı birim karışıklığından çıkar. Kararlar:

| Büyüklük | Birim | Not |
|---|---|---|
| Sıcaklık | **K** (Kelvin) | Her yerde. DWSIM de K kullanır. |
| Basınç (KE modeli) | **kPa** | Henry sabiti kPa tabanlı (§B.3). |
| Basınç (DWSIM/config) | **Pa** | DWSIM Pa kullanır. Dönüşüm: kPa = Pa/1000. |
| Derişim (KE modeli) | **mol/L** (= kmol/m³) | Henry kPa·L/mol → [CO₂]=P/H mol/L verir. |
| Molar akış | **mol/s** | DWSIM akım tablosuyla uyumlu. |
| Enerji/görev | **kW** (akımlar), **kJ/mol** (reaksiyon), **MJ/kg** (özgül) | |
| Yükleme α | **mol CO₂ / mol MEA** | Boyutsuz. |

**KE motorunun içi tamamen {kPa, mol/L, K} ile çalışır.** DWSIM'e/config'e giriş-çıkışta {Pa, mol/s} ile çevir.

---

# BÖLÜM B — Literatür sayısal verileri (tüm sabitler)

Bunların hepsi `kent_eisenberg.py` içine, kaynağı yorum satırı olarak yazılmış hâlde gömülecek.

## B.1 — Ortak denge sabitleri (Edwards ve ark. 1978)

Form: **ln K = a₁/T + a₂·ln T + a₃**, T Kelvin. Bu üçü Zhu ve Aboudheir'de birebir aynıdır (yalnızca etiket farklı).

| Sabit | Reaksiyon | a₁ | a₂ | a₃ | Birim | T aralığı |
|---|---|---|---|---|---|---|
| `K_w` | 2H₂O ⇌ H₃O⁺ + OH⁻ | −13445.9 | −22.4773 | 140.932 | (mol/L)² | 273–498 K |
| `K_co2` | CO₂ + 2H₂O ⇌ H₃O⁺ + HCO₃⁻ | −12092.1 | −36.7816 | 235.482 | mol/L | 273–498 K |
| `K_bic` | HCO₃⁻ + H₂O ⇌ CO₃²⁻ + H₃O⁺ | −12431.7 | −35.4819 | 220.067 | mol/L | 273–498 K |

## B.2 — Fit edilen sabitler: protonasyon + karbamat (İKİ KAYNAK)

**⚠️ İki makale K₈/K₉ etiketlerini TERS kullanır. Koda çıplak `K8`/`K9` yazma; `K_prot` ve `K_carb_rev` gibi anlamlı isim kullan.**

Aynı form: **ln K = a₁/T + a₂·ln T + a₃**.

| Kaynak | Protonasyon `K_prot` = [RNH₂][H₃O⁺]/[RNH₃⁺] | Karbamat (ham) | Geçerli T |
|---|---|---|---|
| **Zhu 2022** (20 wt%) | a: **−5880.90, 0, −3.24111**<br>(Zhu'nun K₈'i) | K₉_Zhu (consumption) = [RNH₃⁺][HCO₃⁻]/([RNHCOO⁻][H₃O⁺])<br>a: **3117.05, 0, 8.94366** | 298–353 K |
| **Aboudheir 2003** (KE-1976) | a: **−5851.11, 0, −3.3636**<br>(Aboudheir'in K₉'u) | K₈_Ab (reversion) = [RNH₂][HCO₃⁻]/[RNHCOO⁻]<br>a: **−3090.83, 0, 6.69425** | 298–413 K |

## B.3 — Henry sabiti (Zhu 2022, Tablo 2, 20 wt%)

Ham tablo (birim **kPa/(kmol/m³) = kPa·L/mol**):

| T (K) | 298 | 313 | 333 | 353 |
|---|---|---|---|---|
| H_CO₂ | 3251.62 | 4078.31 | 5344.08 | 6791.55 |

**Sıcaklık interpolasyonu için fit (doğruladım, kusursuz uyum):**

```
H_CO2(T) = exp(12.8141 − 1408.69 / T)     # kPa·L/mol, T Kelvin
```

Kullanım: `[CO2]_serbest = P_CO2 / H_CO2(T)`  → P_CO2 kPa ise [CO₂] mol/L çıkar.

## B.4 — İKİ KAYNAĞI TEK ÇÖZÜCÜDE BİRLEŞTİRME (kritik sentez)

Karbamat reaksiyonu iki makalede farklı yazıldığı için, ikisini **tek bir "reversion" formunda** birleştir. İç temsil olarak şunu kullan:

```
[RNHCOO⁻] = [RNH₂]·[HCO₃⁻] / K_carb_rev
```

`K_carb_rev(T)` her kaynak için (sayısal olarak doğruladım — iki kaynak %5–11 içinde örtüşüyor):

```python
# source='aboudheir':
K_carb_rev(T) = exp(-3090.83/T + 6.69425)                       # doğrudan K8_Ab
# source='zhu':
K_carb_rev(T) = exp(-5880.90/T - 3.24111) * exp(3117.05/T + 8.94366)   # = K_prot_zhu * K9_zhu
```

**Kaynak seçimi kuralı (ekstrapolasyondan kaçınmak için):**
- **Absorber** (313–323 K): `source='zhu'` → 20 wt%'te en doğru, aralık içinde, ±%5 parite.
- **Stripper** (393 K): `source='aboudheir'` → Zhu'nun 353 K tavanının üstünde; Aboudheir 413 K'ye kadar geçerli.
- Örtüşme kontrolü: 333–353 K'de iki kaynak %10 içinde uyuşmalı (doğruladım). Uyuşmuyorsa sabitlerde hata var.

## B.5 — Doğrulama için deneysel VLE verisi (SEN SAĞLAYACAKSIN)

Zhu'nun ham (α, P_CO₂) ölçümleri makalede ambargolu. Bu yüzden `data/vle_experimental_mea.csv`'yi şuradan doldur:

- **Öncelik:** Jou, Otto & Mather (1995) veya Lee, Otto & Mather (1976) — CO₂/MEA VLE'nin en çok kullanılan referans setleri; 313 K civarı ve geniş yükleme açıkça mevcut. (Aboudheir Şekil 3'ün kaynak verisi bunlardır.)
- **Alternatif:** Zhu Şekil 3 veya Aboudheir Şekil 3'ü WebPlotDigitizer ile dijitalleştir.

CSV formatı: `T_K, mea_wt, alpha, pco2_kPa, source`. En az 313 K'de ~10–15 nokta yeterli. **Hedef: parite AARD ≤ %5** (Aboudheir kendi modelinde %12.5 raporlar — tolerans buna göre gevşetilebilir).

## B.6 — Fiziksel özellikler (indirgenmiş model ve reboiler görevi için)

| Büyüklük | Değer | Kaynak / not |
|---|---|---|
| Molar kütle CO₂ | 44.01 g/mol | |
| Molar kütle MEA | 61.08 g/mol | |
| Molar kütle H₂O | 18.02 g/mol | |
| Molar kütle N₂ / O₂ | 28.01 / 32.00 g/mol | inert |
| Molar kütle MEA_Carbamate (C₃H₇NO₃) | 105.09 g/mol | psödo-bileşen |
| Solvent ısı kapasitesi Cp | ~3.9 kJ/(kg·K) @20 wt% | literatür; 30 wt%'te ~3.7 |
| CO₂ absorpsiyon entalpisi ΔH_abs | **64.0 kJ/mol** (DWSIM değeri) *veya* ~85 kJ/mol (literatür) | **KARAR:** flowsheet ile tutarlılık için DWSIM'in 64.0'ını kullan; literatürün ~85 olduğunu `uncertainty.md`'ye not düş. |
| MEA çözelti derişimi (20 wt%) | 3.285 mol/L | Zhu; [RNH₂]_t olarak kullan |

## B.7 — Zhu Tablo 3 ayrık değerleri (çapraz-kontrol için)

Korelasyonunun doğru kodlandığını bunlarla teyit et (ben ettim, %5 içinde tutuyor):

| T (K) | K_prot (Zhu K₈) | K₉_Zhu |
|---|---|---|
| 298 | 1.09693×10⁻¹⁰ | 2.66631×10⁸ |
| 313 | 2.63471×10⁻¹⁰ | 1.62296×10⁸ |
| 333 | 7.78297×10⁻¹⁰ | 8.90972×10⁷ |
| 353 | 2.40987×10⁻⁹ | 5.22888×10⁷ |

---

# BÖLÜM C — DWSIM'den çekeceğin sayısal veriler (nominal referans)

Bunları `Flowsheet.dwxmz`'yi GUI'de açıp (F5 ile çözüp) *Material Streams* tablosundan okuyacaksın; hepsi `config.yaml`'a nominal değer olarak gider. Aşağıdaki değerleri ben zaten XML'den çıkardım — GUI'de teyit et.

## C.1 — Akım tablosu (temel akımlar)

| Akım | T (K) | P (Pa) | Toplam (mol/s) | CO₂ | MEA | Carbamate | H₂O | N₂ | O₂ |
|---|---|---|---|---|---|---|---|---|---|
| **Flue Gas** | 315.19 | 101325 | 32.27 | 5.94 | 0 | 0 | 0.516 | ~24.27 | ~1.55 |
| **Lean Mea** (taze) | 319.15 | 101325 | 40.57 | 0 | 6.248 | 0 | 34.32 | 0 | 0 |
| **Rich Mea** | 299.375 | 96325 | 587.99 | ~0.039 | ~çok | 5.658 | ~çok | 0 | 0 |
| **Clean Gas** | 299.375 | 96325 | 27.13 | 0.559 | 0.0022 | 0 | 0.766 | ~24.27 | ~1.55 |
| **CO₂ Product** | 382.48 | 186325 | 13.66 | 5.371 | 0.106 | 0 | 8.18 | ~0 | ~0 |
| **Compressed CO₂** | 298.15 | 813675 | 4.768 | 4.734 | 0 | 0 | 0.027 | ~0 | ~0 |

Baca gazı mol kesirleri: CO₂ 0.184, N₂ 0.752, O₂ 0.048, H₂O 0.016.

## C.2 — Reaktör ayarları

| Reaktör | Rol | Baz bileşen | Dönüşüm (mevcut, sabit) | Mod |
|---|---|---|---|---|
| RCONV-1 | Absorber | CO₂ | **%90** | adyabatik (E-04≈0) |
| RCONV-2 | Regeneratör | MEA_Carbamate | **%95** | adyabatik (E-02≈0) |

Reaksiyon (1:1 psödo): `CO₂ + MEA → MEA_Carbamate` (absorpsiyon), ters (rejenerasyon). Dönüşüm DWSIM'de `Reaction.Expression` alanında string olarak tutulur — **senin yazacağın nokta budur.**

## C.3 — Ünite görevleri (referans)

| Ünite | Ayar | Görev |
|---|---|---|
| PUMP-1 | +100 kPa | +2.09 kW |
| HT-1 | çıkış 393.15 K | ~6149 kW (ER-1 ile net düşer) |
| CL-1 | çıkış 298.15 K | 5466.21 kW → ER-1'e |
| ER-1 | enerji geri-devri | CL-1 ısısını HT-1'e köprüler |
| C-1 | → 500 kPa, η=%75 | +63.17 kW |
| CL-2 | → 298.15 K | −492.93 kW (buhar frak. 0.35) |
| V-2 | flaş (su ayırma) | — |
| C-2 | → 813.675 kPa, η=%75 | +7.89 kW |
| CL-3 | → 298.15 K | −9.09 kW |
| SPL-1 | geri-devir/pörç | 0.9691 / 0.0309 |

## C.4 — Türetilmiş performans (mevcut flowsheet)

- Absorber tutma: (5.94−0.559)/5.94 = **%90.6**
- Nihai ürüne geri-kazanım: 4.734/5.94 = **%79.7**
- V-2'de kaybedilen CO₂: 5.371−4.734 = ~0.637 mol/s = besleme CO₂'sinin **%10.7'si** (en büyük sızıntı)

## C.5 — config.yaml (hepsi bir arada)

```yaml
nominal:
  flue_gas_molar_flow: 32.27
  flue_gas_co2_frac: 0.184
  flue_gas_n2_frac: 0.752
  flue_gas_o2_frac: 0.048
  flue_gas_h2o_frac: 0.016
  absorber_T: 313.15
  absorber_P_Pa: 101325
  reboiler_T: 393.15
  regen_P_Pa: 186325
  mea_wt_frac: 0.20            # KARAR: 20 wt% (Zhu sabitleriyle uyum)
  mea_conc_molL: 3.285
  lean_loading: 0.20
  eta_abs: 0.85
  eta_reg: 0.90
physical:
  Cp_solvent_kJkgK: 3.9
  dH_abs_kJmol: 64.0          # DWSIM değeri (literatür ~85, uncertainty.md'ye not)
  M_CO2: 44.01
  M_MEA: 61.08
  M_H2O: 18.02
envelope:
  L_over_G: [1.0, 4.0]
  lean_loading: [0.15, 0.30]
  absorber_T: [308.15, 323.15]
  reboiler_T: [383.15, 403.15]
  flue_gas_co2_frac: [0.04, 0.18]
```

---

# BÖLÜM D — Yazacağın tüm denklemler (numaralı, baştan sona)

## D.1 — Denge sabiti korelasyonu (her sabit için)

```
(1)   K(T) = exp( a1/T + a2·ln(T) + a3 )      T Kelvin
```
`K_w, K_co2, K_bic` → §B.1 katsayıları. `K_prot, K_carb_rev` → §B.2/B.4, source'a göre.

## D.2 — Henry

```
(2)   [CO2] = P_CO2 / H_CO2(T),    H_CO2(T) = exp(12.8141 − 1408.69/T)   [kPa·L/mol]
```

## D.3 — Tür-derişim ilişkileri (verilen [H₃O⁺] ve [CO₂] için)

```
(3)   [OH⁻]     = K_w / [H3O⁺]
(4)   [HCO3⁻]   = K_co2 · [CO2] / [H3O⁺]
(5)   [CO3²⁻]   = K_bic · [HCO3⁻] / [H3O⁺]
(6)   [RNH2]    = MEA_t / ( 1 + [H3O⁺]/K_prot + [HCO3⁻]/K_carb_rev )
(7)   [RNH3⁺]   = [RNH2] · [H3O⁺] / K_prot
(8)   [RNHCOO⁻] = [RNH2] · [HCO3⁻] / K_carb_rev
```

## D.4 — Kütle ve yük dengeleri

```
(9)   Amin:    [RNH2] + [RNH3⁺] + [RNHCOO⁻] = MEA_t              (Denklem 6 bunu zaten sağlar)
(10)  Karbon:  α·MEA_t = [CO2] + [HCO3⁻] + [CO3²⁻] + [RNHCOO⁻]   (yükleme tanımı)
(11)  Yük:     [RNH3⁺] + [H3O⁺] = [OH⁻] + [HCO3⁻] + 2[CO3²⁻] + [RNHCOO⁻]
```

## D.5 — KE çözüm algoritması: `pco2_from_alpha(alpha, T, wt, source)`

Verilen α ve T → P_CO₂. Bilinmeyen [CO₂] (dolayısıyla P_CO₂) ve [H₃O⁺]. İç içe iki kök:

```
dış: [CO2]'yi ara (brentq, [CO2] ∈ [1e-8, 5])
     iç: verilen [CO2] için [H3O⁺]'yi yük dengesinden (11) çöz (brentq, [H3O⁺] ∈ [1e-12, 1e-6])
         → (3)-(8) ile tüm türler
     dış artık:  g_C = α·MEA_t − ([CO2]+[HCO3⁻]+[CO3²⁻]+[RNHCOO⁻])   → 0 olmalı (Denklem 10)
[CO2] bulununca → P_CO2 = [CO2]·H_CO2(T)
```

## D.6 — Ters çözüm: `alpha_from_pco2(pco2, T, wt, source)`

Verilen P_CO₂ → α. Daha basit: [CO₂] doğrudan Henry'den (Denklem 2), sonra tek kök:

```
[CO2] = P_CO2 / H_CO2(T)
[H3O⁺]'yi yük dengesinden (11) çöz (brentq, [1e-12, 1e-6])
(3)-(8) ile türler
α = ([CO2]+[HCO3⁻]+[CO3²⁻]+[RNHCOO⁻]) / MEA_t     (Denklem 10)
```

Bu ikisi Faz 0'ın çekirdeğidir. `alpha_from_pco2` daha çok kullanılır (absorber/stripper çözücüleri buna dayanır).

## D.7 — Absorber tek-kademe denge → X_abs (Faz 1)

Bilinmeyen: gazdan sıvıya geçen mol CO₂ = `a`. Denklemler:

```
(12)  n_CO2_liq_out = α_lean·n_MEA + a           →  α_rich = α_lean + a/n_MEA
(13)  n_CO2_gas_out = n_CO2_gas_in − a
(14)  y_CO2_out     = n_CO2_gas_out / (n_gas_in − a)
(15)  P_CO2_out     = y_CO2_out · P_absorber
(16)  Denge kapanışı: α_rich = alpha_from_pco2(P_CO2_out, T_abs, wt, 'zhu')
```
`a`'yı (16)'nın kökü olarak çöz (brentq, a ∈ [0, n_CO2_gas_in]). Sonra:

```
(17)  a_gerçek = η_abs · a_denge
(18)  X_abs = a_gerçek / n_CO2_gas_in        # DWSIM RCONV-1'e yazılacak dönüşüm
```

## D.8 — Stripper → X_reg (Faz 1, yaklaşık)

Stripper koşulunda (T_reb, regen_P) erişilebilir yalın yükleme:

```
(19)  P_CO2_strip ≈ (CO2 mol kesri, regen tepesi) · regen_P     # yaklaşık; DWSIM rafine eder
(20)  α_lean_out = alpha_from_pco2(P_CO2_strip, T_reb, wt, 'aboudheir')
(21)  n_CO2_stripped_denge = (α_rich − α_lean_out) · n_MEA
(22)  X_reg = η_reg · n_CO2_stripped_denge / n_carbamate_in
```
> Bu adım yaklaşıktır (P_CO2_strip'in kendisi stripping'e bağlı). Faz 2'de DWSIM rigorous değeri verir; indirgenmiş model onu ±%3 içinde tutmalı.

## D.9 — Yaklaşma faktörü η (tek dürüst varsayım)

```
(23)  X_effective = η · X_equilibrium,    η ∈ [0.70, 0.95]
```
**Kalibrasyon kararı:** η'yu, nominal koşulda X_abs ≈ 0.906 ve X_reg ≈ 0.95 verecek şekilde geri-hesapla (mevcut flowsheet ile tutarlılık), ya da literatür Murphree değeri (~0.85) sabitle. Hangisini seçersen `uncertainty.md`'ye yaz.

## D.10 — KPI denklemleri (Faz 3)

```
(24)  Yakalama (%)          = 100·(n_CO2_flue − n_CO2_cleangas)/n_CO2_flue
(25)  Geri-kazanım (%)      = 100·n_CO2_compressed / n_CO2_flue        # sadece DWSIM
(26)  Ürün saflığı (%)      = 100·n_CO2_comp / n_total_comp            # sadece DWSIM
(27)  Reboiler görevi (kW)  = Q_sensible + Q_reaction
        Q_sensible = m_solvent[kg/s]·Cp[kJ/kg·K]·(T_reb − T_abs)
        Q_reaction = n_CO2_stripped[mol/s]·ΔH_abs[kJ/mol]
(28)  Özgül reboiler (MJ/kg)= Reboiler_görevi[kW] / (n_CO2_captured[mol/s]·0.04401[kg/mol]) / 1000
(29)  Net dış ısı (kW)      = Q_HT1 − Q_CL1(ER-1 ile geri kazanılan)    # DWSIM'den
```
> (28) hedef: gerçek MEA bandı ~3.5–4.0 MJ/kg. Modelin bunun neresinde çıkacağını göreceğiz — ekstrapolasyon/basitleştirme etkilerini gösterir.

## D.11 — Optimizasyon problemi (Faz 4)

```
min   Özgül_reboiler(x)          x = [solvent_debisi, α_lean, T_reb]
s.t.  Yakalama(x) ≥ 90 %
      Saflık(x)   ≥ 99 %
      x ∈ envelope (config.yaml)
```
Çöz: (a) Faz 2 gridinde grid-argmin, (b) `scipy.optimize.minimize(method='SLSQP')` ile indirgenmiş model üzerinde rafine. Optimumu DWSIM'de re-simüle et.

---

# BÖLÜM E — Sayısal modelleme detayları (çözücü ayarları)

| Konu | Ayar / değer |
|---|---|
| Kök bulucu (1D) | `scipy.optimize.brentq` — sağlam, aralık gerektirir |
| [H₃O⁺] aralığı | `[1e-12, 1e-6]` mol/L (Zhu'nun fit sınırı) |
| [CO₂] aralığı | `[1e-8, 5]` mol/L |
| α aralığı | `[1e-4, 0.55]` (gerçek MEA maks ~0.5; 1:1 psödo için kod tarafında ayrı yönet) |
| Tolerans | `xtol=1e-10, rtol=1e-8` |
| Çift-hassasiyet | numpy float64 (varsayılan) — Jacobian hassasiyeti için önemli |
| Geçerlilik uyarısı | T veya P_CO₂ §B aralığı dışındaysa `warnings.warn(...)` |
| 1:1 vs 2:1 | KE gerçek 2:1 (α_max~0.5) verir; DWSIM'e **X = mol_CO2_absorbe/mol_CO2_giren** oranı olarak yaz (yüzde yükleme değil) — §D.7-D.8 zaten böyle |
| Başlangıç tahmini | Yüksek yüklemede baskın türler RNHCOO⁻, RNH₃⁺, HCO₃⁻; [H₃O⁺]~1e-9 iyi başlangıç |

**Yaygın hatalar ve önlem:**
- Birim karışıklığı (Pa↔kPa): KE motoruna her zaman kPa ver. → §A.4
- K₈/K₉ etiket takası: `K_prot`/`K_carb_rev` isimlerini kullan. → §B.2
- Turkish locale ondalık: DWSIM tarafında `InvariantCulture`. → §A.2
- Ekstrapolasyon: stripper'da Zhu kullanma, Aboudheir kullan. → §B.4

---

# BÖLÜM F — Baştan sona sıra (yapılacaklar, tam sırayla)

Bu, ilk açtığın günden bitişe kadar atacağın adımların tam listesi.

1. **Ortamı kur.** Klasör ağacını (PLAN.md §3.1) oluştur, `requirements.txt`'i kur (`numpy scipy pandas pyarrow matplotlib plotly pyyaml`; pythonnet'i sona bırak).
2. **config.yaml'ı yaz** — BÖLÜM C.5'i olduğu gibi koy.
3. **DWSIM GUI'de flowsheet'i aç, F5 ile çöz.** Akım tablosunun BÖLÜM C.1 ile eştiğini teyit et. Reaksiyon Expression alanlarını (90/95) ve reaktör baz bileşenlerini gör. (Bu adım DWSIM tarafını "anlama" adımıdır; henüz kod yok.)
4. **`kent_eisenberg.py`'yi yaz** — BÖLÜM B'deki tüm sabitler + Denklem (1)-(8) + `alpha_from_pco2`, `pco2_from_alpha` (§D.5-D.6). Sabitleri §B.7 ayrık değerleriyle çapraz-kontrol et.
5. **`data/vle_experimental_mea.csv`'yi sağla** (§B.5) ve **`run_phase0_validate_vle.py`** ile parite + izoterm grafiklerini üret. **KAPI 0:** AARD ≤ %5. Geçmeden durma.
6. **`equilibrium_stage.py`'yi yaz** — Denklem (12)-(23), `absorber_conversion`, `regenerator_conversion`. **KAPI 1:** nominal koşulda X_abs≈0.906, X_reg≈0.95; fiziksel işaretler doğru (§D.7-D.9). η'yu burada kalibre et.
7. **`reduced_model.py`'yi yaz** — Faz 1 dönüşümleri + kütle dengesi + reboiler görevi (Denklem 24-28). Düzenli grid üret (§Faz2), `results/data/reduced_grid.parquet`'e yaz.
8. **`dwsim_harness.py`'yi yaz** (pythonnet, §A.2). Tek nominal senaryoyu çöz. **KAPI 2:** kütle dengesi ~%0, `Calculated=True`, HT-1/ER-1 enerji tutarsızlığını netleştir. Sonra ~30–50 seyrek doğrulama noktası koş.
9. **`analysis.py` + `plotting.py`'yi yaz** — 6 görsel (§Faz3). **KAPI 3:** fiziksel tutarlılık (U-eğrisi minimumu, kontur monotonluğu).
10. **`optimize.py`'yi yaz** — Denklem (D.11). Grid-argmin + SLSQP. Optimumu DWSIM'de re-simüle et. **KAPI 4:** DWSIM'de kısıtlar sağlanmalı.
11. **`docs/uncertainty.md`'yi yaz** — η varsayımı, denge=üst-sınır, 1:1 stokiyometri, ΔH seçimi (64 vs 85), ekstrapolasyon pencereleri, %18.4 baca CO₂'si.
12. **(Opsiyonel) Faz 6** — KE'yi DWSIM'e gömülü script yap.

**Başlangıç noktası: Adım 4 (`kent_eisenberg.py`).** Her şey ona bağlı.

---

### Özet karar listesi (kod boyunca sabit tut)
- Birimler: KE içi {kPa, mol/L, K}; DWSIM/config {Pa, mol/s}. (§A.4)
- wt% = 20, [RNH₂]_t = 3.285 mol/L. (§B.6)
- Absorber sabitleri = Zhu; stripper sabitleri = Aboudheir; karbamat = reversion formu. (§B.4)
- Dönüşüm = mutlak mol CO₂ oranı, yüzde yükleme değil. (§E)
- ΔH_abs = 64.0 kJ/mol (DWSIM), literatürü not düş. (§B.6)
- η: nominal koşulda %90.6/%95 verecek şekilde kalibre. (§D.9)
