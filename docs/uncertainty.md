# Model Varsayımları ve Belirsizlikler (Uncertainty & Limitations)

Bu döküman, MEA Karbondioksit Yakalama projesinde Kent-Eisenberg tabanlı analitik vekil (proxy) modelde yapılan temel kabulleri, bunların fiziksel karşılıklarını ve olası limitasyonlarını listelemek amacıyla hazırlanmıştır.

## 1. Eta ($\eta$) Yaklaşma Faktörü ve Etkin Kademe Etkisi
**Durum:** `eta_abs` kalibrasyon sonucunda `~2.49` gibi 1'den büyük bir değer almıştır.
**Açıklama:** Standart termodinamikte bir denge yaklaşma faktörü 1'i aşamaz (denge sınırıdır). Ancak burada kullandığımız model **tek kademeli** bir denge (flash) tankı mantığıyla çalışmaktadır. Gerçek absorber kolonu ise çok kademelidir ve her kademede yeniden denge kurarak kümülatif olarak çok daha yüksek bir dönüşüm elde eder. 
**Sonuç:** `eta_abs > 1` olması matematiksel bir hata değil, tek kademeli modelin çok kademeli fiziksel kolonu (etkin kademe sayısı mekanizmasıyla) taklit etmesi için gereken bir yapay "scale" faktörüdür. 

## 2. Denge (Equilibrium) Üst Sınırı ve Kinetik Kısıtlar
**Durum:** Kent-Eisenberg modeli tamamen termodinamik bir modeldir ve reaksiyon kinetiğini (hızını) göz ardı eder.
**Açıklama:** Gaz-sıvı kütle transfer dirençleri ve reaksiyon kinetiği hesaba katılmamıştır. `eta` parametresi bu kinetik ve hidrolik eksiklikleri toplu olarak (lumped) "absorber/stripper verimi" adı altında kalibre etmek için kullanılmıştır.

## 3. MEA ve CO₂ İçin 1:1 Stokiyometri Kabulu
**Durum:** Karbamat oluşumu geleneksel olarak $2 \text{MEA} + \text{CO}_2 \rightleftharpoons \text{MEACOO}^- + \text{MEAH}^+$ reaksiyonu üzerinden yürür ve teorik maksimum yükleme (alpha) 0.5 mol CO₂ / mol MEA'dır. Ancak DWSIM psödo-reaksiyon modelinde bu 1:1 olarak tanımlanmıştır.
**Açıklama:** Modelde zengin yükleme ($\alpha_{rich}$) zaman zaman 1.0'ı aşabilmektedir. Bu, sistemin sadece karbamat değil, aynı zamanda bikarbonat ($HCO_3^-$) oluşumunu da (ikincil reaksiyonları) dolaylı olarak tek bir "yakalama" reaksiyonu içinde birleştirdiğini gösterir. Bu, DWSIM yapısının getirdiği bilinen bir kısıtlamadır.

## 4. Reaksiyon Entalpisi (Absorption Heat, $\Delta H_{abs}$)
**Durum:** Kullanılan reaksiyon ısısı `64.0 kJ/mol CO2`'dir (DWSIM tabanlı).
**Açıklama:** Literatürde %30 wt MEA için CO₂ absorbsiyon ısısı yaklaşık `80 - 85 kJ/mol` olarak bilinmektedir. DWSIM'in Peng-Robinson veya diğer EOS tabanlı varsayılan özellikleri bu değeri biraz daha düşük (`64 kJ/mol`) tahmin etmiştir. Reboiler görevindeki (duty) hesaplamalar DWSIM ile konsistent olması için 64 kJ/mol üzerinden yapılmıştır. Literatür uyumu aranırsa bu değerin yükseltilmesi gerekebilir.

## 5. %18.4 Baca Gazı CO₂ Derişimi ve Ekstrapolasyon
**Durum:** Enerji santrali (muhtemelen kömür veya ağır fuel-oil yakıtlı, ya da çimento/demir-çelik tesisi) baca gazında %18.4 CO₂ bulunmaktadır. Standart doğalgaz santrallerinde bu değer %4-%8 arasındadır.
**Açıklama:** Model %18 civarındaki yüksek kısmi basınç bölgesine göre kalibre edilmiştir. Parametrik sweep (tarama) işlemlerinde CO₂ derişimi %4'lere kadar indirgendiğinde (ekstrapolasyon), `eta` yaklaşım faktörünün doğrusal olmayan (non-linear) davranış gösterme ihtimali vardır. Optimum sonuçlar %15-%20 CO₂ bandında en yüksek doğruluğa sahiptir.

## 6. İdeal Çözelti (Activity Coefficients $\gamma = 1$)
**Durum:** Klasik Kent-Eisenberg modeli çözeltiyi ideal kabul eder.
**Açıklama:** Elektrolit sistemlerde (özellikle iyonik gücün yüksek olduğu yüklü MEA çözeltilerinde) aktivite katsayıları 1'den oldukça farklıdır. Bu model, konsantrasyonları direkt aktivite olarak kabul eder. Bu basitleştirme kalibrasyon (veri fitleme) ile kompanse edilmiştir.

## 7. Duyarlılık Analizi: Morris Metodu ($\mu^*$)
**Durum:** Parametrelerin küresel duyarlılığı için SHAP (Shapley) veya Sobol yerine SALib kütüphanesinin Morris metodu tercih edilmiştir.
**Açıklama:** Morris metodu her bir parametrenin çıktılar üzerindeki "Elementary Effects"ini tarayarak bağımsız ve non-lineer etkilerin büyüklüğünü ($\mu^*$) ve etkileşimleri ($\sigma$) ölçer. Bu, XGBoost vb. karmaşık makine öğrenmesi algoritmaları kurmadan analitik fiziksel model üzerinde çok daha hızlı, klasik ve etkili bir parametre tarama (screening) yöntemidir. Duyarlılık metrikleri klasik Sobol indeksleri değil, $\mu^*$ (mu_star) üzerinden değerlendirilmelidir.

## 8. N-Kademeli Absorber ve alpha-AARD Metrigi
**Durum:** Absorber 3 teorik kademeli (N=3) ters akimli (counter-current) model ile temsil edilmistir ve Faz 0 dogrulamasinda pco2 yerine alpha AARD si kullanilmistir.
**Aciklama:** Gercek bir MEA absorber kolonu 15-20 teorik kademeden olusur. Modelde kullanilan 3 kademe + kademe-basi Murphree benzeri yaklasimla (eta_stage) gercek kolonun asimptotik doyma davranisi etkin (empirical) olarak taklit edilmektedir. Gercek kolon kademe sayisi modellenmemistir. Faz 0 da pco2 nin ustel degisiminden kaynaklanan sapmalari onlemek ve adil bir hata dagilimi saglamak icin dogrulama alpha uzerinden yapilmistir.


## 9. Asiri Solvent Fazlasi ve Yapay Verim (eta_stage = 0.054)
**Durum:** Absorber kalibrasyonu, %90 yakalama hedefini saglamak icin eta_stage'i cok dusuk (0.054) bir degere cekmistir.
**Aciklama:** Gercek kolon donanimlarinda Murphree verimi tipik olarak 0.7 - 0.95 araligindadir. Ancak flowsheet'teki inanilmaz yuksek dolasan solvent (MEA) orani (molar L/G ~ 3.4), absorpsiyon potansiyelini o kadar artirir ki, tek bir teorik kademe bile CO2'nin tamamina yakinini (veya asirisini) yakalama egilimi gosterir. Bu yuzden eta_stage=0.054 fiziksel bir donanim (kademelerin kütle transfer etkinligi) gostergesi degil, asiri-guclu modeli gercek limite ceken suni bir kalibrasyon carpanidir. 

## 10. Rejenerator Termodinamigi ve P_CO2_strip Artefakti
**Durum:** DWSIM'in nominal ciktisindan alinan sabit y_co2_regen = 0.393 kullanildiginda P_CO2_strip 73.2 kPa olur. Bu basincta denge alpha_lean_out degeri 0.337'dir. Ancak asiri solvent yuzunden absorberdan gelen alpha_rich 0.249'dur. Eger P_CO2 73.2 kPa olsaydi, 0.249 < 0.337 oldugundan fiziksel siyrilma (stripping) tamamen imkansiz olurdu (X_reg = 0).
**Aciklama:** Gercek bir reboiler'da buharlasma basincini SU BUHARI belirler. 120 C ve 186 kPa toplam basincta, suyun kismi basinci (Raoult yasasi ile) yaklasik 184 kPa'dir. Bu da gercek P_CO2'nin yaklasik 2.4 kPa civarinda (73 kPa degil!) oldugu anlamina gelir. P_CO2 = 2.4 kPa iken alpha_lean_out 0.114'e duser ve siyrilma fiziksel olarak gecerli hale gelir. Model artik sabit DWSIM ciktisindan kurtarilip buhar basinci fiziksel prensiplerine baglanmistir.

## 11. Reboiler Ozgul Enerjisinde Buharlasma Gizli Isisinin (Latent Heat) Eksikligi
**Durum:** Faz 4 (Optimizasyon) senaryosunda 'ozgul enerjiyi minimize et' derseniz, model sadece duyari isi (sensible) ve reaksiyon isisini (reaction) hesapladigi icin, L/G oranini kisitin izin verdigi en alt degere yapistirir (U-egrisi ic-minimumu yoktur).
**Aciklama:** Gercek bir MEA sisteminde, L/G orani cok dustugunde siyirma islemine guc vermek icin asiri miktarda su buharina (stripping steam) ihtiyac duyulur. Bu suyun buharlasma gizli isisi (latent heat of vaporization) dusuk L/G bolgesinde devasa bir enerji cezasidir ve U-egrisinin sol kolunu olusturur. Indirgenmis (proxy) modelimizde suyun buharlasma entalpisi acikca modellenmediginden, model sadece azalan k�tle debisinden (m_solvent) dolayi duyarl� isi tasarrufunu gorur ve enerjiyi monoton olarak asagi ceker. Bu yuzden optimizasyon hedefi 'enerji minimizasyonu' yerine 'minimum feasible solvent dolasimi' olarak cercevelenmistir.

## 12. Stripper Kapasite Kisiti (T_reb = 120 C)
**Durum:** Kapali dongu (alpha_lean_out == alpha_lean) ve %90 yakalama sartlari altinda, 120 C sinirina ulasan reboiler solventi ancak L/G = 3.4 seviyesine kadar indirebiliyor.
**Aciklama:** Eger L/G oranini 3.4'un altina dusurursek, absorberden gelen alpha_rich yukseliyor. Bu daha kirli solventi ayni T_reb (120 C) ile stripper ayni alpha_lean seviyesine temizleyemiyor. Sistemin daha dusuk solvent debisinde calisabilmesi icin stripper sicakliginin 120 C'yi asmasi gerekiyor. Optimizasyonun nominal deger olan 3.41'de kalmasinin sebebi enerji eksikligi degil, stripperin 120 C kapasite tavanina (bottleneck) carpmasidir. Bu bir basarisizlik degil, DWSIM donaniminin termodinamik siniridir.
