# MEA CO2 Yakalama: DWSIM Kalibrasyon ve KE-Fizibilite Projesi

Bu proje, geleneksel proses simülatörlerinin (özellikle DWSIM) CO2 absorbsiyonu/desorpsiyonu modellenirken kullandığı **sabit reaksiyon dönüşüm oranlarının (fixed conversion fractions)** fiziksel ve termodinamik gerçeklikten (fizibilite sınırlarından) ne kadar saptığını kanıtlamak amacıyla geliştirilmiştir. 

Proje, temel termodinamik kısıtları (Kütle-Etki, Kent-Eisenberg) merkeze alan bir **Proxy Model** inşa ederek, DWSIM'in iyimser varsayımları ile fiziksel gerçeklik arasındaki uçurumu (özellikle enerji tüketimi boyutunda) nicelleştirir.

---

## 1. Proje Mimarisi ve Kaynak Kodlar (`src/`)

Sistemin kalbi `src/` klasöründeki modüllerden oluşur. Her modül belirli bir mühendislik/yazılım sorumluluğunu üstlenir:

### Termodinamik ve Denge Çekirdeği
* **`kent_eisenberg.py`**: Sistemin temel termodinamik denklemlerini barındırır. MEA-CO2-H2O sistemindeki iyonlaşma dengeleri, reaksiyon sabitleri (K1-K7), Henry yasası ve aktivasyon enerjileri bu modülde tanımlanır.
* **`ke_solver.py`**: `kent_eisenberg.py` içindeki non-lineer denklem setlerini (denge kısıtlarını) çözen algoritmik yapıdır. Verilen bir P, T ve MEA konsantrasyonu için CO2 yüklemesini ($\alpha$) veya tersini hesaplayan optimizasyon/root-finding fonskiyonlarını içerir.

### Ünite Operasyonları ve Hızlı Model
* **`equilibrium_stage.py`**: Kolon operasyonlarını (Absorber ve Regenerator/Stripper) matematiksel olarak simüle eder. Sisteme özgü kalibrasyon çarpanlarını ($\eta_{abs}$, $\eta_{reg}$) kullanarak teorik denge değerlerini "gerçekleşen" değerlere dönüştürür.
* **`reduced_model.py`**: Fiziksel modele dayalı bir "hızlı vekil (proxy)" modeldir. Tüm flowsheet KPI'larını (kütle dengesi, sensible ısı, reaksiyon ısısı, reboiler görevi, spesifik enerji) saniyeden çok daha kısa sürede hesaplayarak binlerce senaryonun taranmasını sağlar.

### Analiz, Optimizasyon ve DWSIM Entegrasyonu
* **`optimization.py`**: Proxy model üzerinde SLSQP veya genetik algoritmalar kullanarak minimum spesifik enerji tüketimini sağlayacak optimum işletme parametrelerini (L/G oranı, $T_{reb}$, vs.) arar.
* **`dwsim_harness.py`**: Pythonnet kullanarak DWSIM'in (`Flowsheet.dwxmz`) arka planda sessizce (UI olmadan) çalıştırılmasını sağlar. Kütle ve enerji akımlarından `GetMassFlow()`, `EnergyFlow` gibi özelliklerle verileri doğrudan çeker.
* **`plotting.py` & `analysis.py`**: Elde edilen verilerin görselleştirilmesi (ısı haritaları, Pareto eğrileri) ve istatistiksel / hassasiyet analizlerinin yapılması için kullanılan yardımcı script'lerdir.

---

## 2. Çalıştırma Adımları (Fazlar) ve Yorumlama (`scripts/`)

Projenin analitik akışı, 6 farklı evreye (Faz 0'dan Faz 5'e) bölünmüştür. **Projeyi çalıştırırken bu sırayı takip etmelisiniz.** 

Tüm scriptler projenin kök dizininde şu formatta çalıştırılır: `python scripts/<script_adi>.py`

### Faz 0: Termodinamik Doğrulama (`run_phase0_vle.py`)
* **Ne Yapar?**: Kütle-Etki (KE) modelimizin doğruluğunu literatürdeki Buhar-Sıvı Dengesi (VLE) verileriyle (Joung, Shen vb.) karşılaştırır.
* **Nasıl Yorumlanır?**: Modelin literatür verileriyle iyi örtüştüğünü gösteren bir hata (RMSE) raporu üretir. Eğer bu aşamada sapma çok yüksekse, sonraki fazlardaki hesaplamalar güvenilirliğini yitirir.

### Faz 1: Çalışma Kapasitesi ve P-T Eğrileri (`run_phase1_curves.py`)
* **Ne Yapar?**: Sıcaklık ve basınca bağlı olarak sistemin teorik maksimum çalışma kapasitesini ($\alpha_{rich} - \alpha_{lean}$) görselleştirir.
* **Nasıl Yorumlanır?**: Absorber ve Stripper arasındaki "ideal" taşıma kapasitesini gösterir. Gerçek operasyonun bu sınırların ne kadar gerisinde kaldığını anlamak için bir "tavan" referansıdır.

### Faz 2: Grid Taraması (`run_phase2_grid.py`)
* **Ne Yapar?**: `config.yaml` dosyasında belirtilen aralıklarda L/G (Sıvı/Gaz) oranı ve $\alpha_{lean}$ (Yalın Yükleme) için yüzlerce senaryoyu tarar.
* **Nasıl Yorumlanır?**: Spesifik Reboiler Görevi (MJ/kg CO2) metriklerini içeren sonuç dosyaları ve ısı haritaları üretir. Hangi işletme koşullarında enerji tüketiminin patladığını veya düştüğünü tespit etmenizi sağlar.

### Faz 3: Hassasiyet Analizi ve Fizibilite Sınırları (`run_phase3_sensitivity.py`)
* **Ne Yapar?**: Özellikle $\alpha_{rich}$'in, stripper'ın termodinamik dengesi olan $\alpha_{lean\_out}$'ın altına düştüğü "imkansız/fizibilitesi olmayan" noktaları tespit eder.
* **Nasıl Yorumlanır?**: DWSIM'in görmezden geldiği en kritik sınır burasıdır. Çıkan raporda "Infeasible noktalar" görürseniz, bu noktaların fiziksel olarak mümkün olmadığını, ancak DWSIM'in burada da sahte sonuç üretebildiğini anlarsınız.

### Faz 4: Optimizasyon (`run_phase4_optimization.py`)
* **Ne Yapar?**: Tüm kısıtları göz önüne alarak, verilen bir CO2 yakalama hedefi (örn. %90) için en az enerji tüketen spesifik $L/G$ ve sıcaklık değerlerini bulur.
* **Nasıl Yorumlanır?**: Tesisin pratikte nasıl çalıştırılması gerektiğine (set-point'lere) dair teorik limitleri ve önerileri sunar. 

### Faz 5: DWSIM vs. KE Model Karşılaştırması (`run_phase5_dwsim.py`)
* **Ne Yapar?**: Sistemin ulaştığı en önemli doğrulama (validation) noktasıdır. DWSIM'i *kendi orijinal* sabit varsayımlarıyla (%90/%95 dönüşüm) çalıştırır ve harcanan Reboiler ısısını okur. Ardından **aynı proses şartlarında** termodinamiği dikkate alan Proxy (KE) modelimizi çalıştırarak aradaki farkı ekrana basar.
* **Nasıl Yorumlanır?**: Çıktıda DWSIM'in enerjisi (~5.6 MW) ile Fiziksel Modelin enerjisini (~10.8 MW) yan yana göreceksiniz. 
   - **Isı Geri Kazanımı (ER-1):** DWSIM'deki enerji, *Lean-Rich Eşanjörünün* geri kazandığı duyulur ısı (sensible heat) nedeniyle çok düşüktür. Proxy modelimiz duyulur ısıyı %100 dışarıdan (harici) hesaplar.
   - **Termodinamik Zorlama:** DWSIM, fiziksel sınırları aşsa bile tepkimeyi ilerlemiş sayarak optimistik enerji rakamları çıkarır. Çıktıdaki rapor bu matematiksel zorlamayı (forcing) açıklar.

---

## 3. Yapılandırma (`config.yaml`)

Projenin tüm kontrol paneli `config.yaml` dosyasıdır. Kodlara müdahale etmeden senaryoları bu dosyadan değiştirebilirsiniz:
* **`nominal`**: Tesisin standart (baseline) operasyon verilerini tutar. Flue gas debisi, sıcaklıklar (absorber: 313.15 K, reboiler: 393.15 K), amin konsantrasyonu (20 wt% MEA) burada tanımlıdır.
* **`physical`**: Reaksiyon ısıları (64 kJ/mol), molar kütleler gibi temel termodinamik veriler buradadır. 
* **`dwsim_map`**: DWSIM içerisindeki akım ve reaktör isimlerinin ID'leri ile nasıl eşleştiğini belirtir (örn. `co2_product: "CO2 Product"`, Reboiler Duty okuması için E-03 vs).
* **`envelope`**: Faz 2 ve Faz 3'teki grid (tarama) operasyonlarının sınır değerlerini (L/G: [1.0, 4.0] vs.) belirler.

---

## 4. Sonuçları Yorumlarken Dikkat Edilmesi Gerekenler

Raporlarda ve bilimsel metinlerde sunum yaparken **iki kavramsal ayrıma** son derece dikkat edilmelidir:

1. **Donanım Verimi vs. Kalibrasyon Katsayısı:** Kodlardaki $\eta_{abs}$ (0.85) ve $\eta_{reg}$ (0.90) değerleri, dolgu malzemesinin veya kolonun "fiziksel verimi" değildir. Bunlar, DWSIM'in *sabit dönüşüm modelini*, fiziksel gerçekliğe (kütle-etki dengesine) bağlamak için kullanılan **tesise özgü kalibrasyon sabitleridir**.
2. **"DWSIM Yanlış Çalışıyor" Demek Yerine:** DWSIM'in hesaplamaları hatalı değildir; kullandığı *Reaksiyon Reaktörü* modeli (sabit %95 dönüşüm) basitleştirilmiştir. Teziniz, "DWSIM'i çürütmek" yerine, "sabit dönüşüm gibi güçlü basitleştirmelerin termodinamik fizibiliteyi nasıl göz ardı ettiğini ve Kütle-Etki (KE) ile desteklenmezse nasıl tehlikeli iyimserliklere yol açtığını nicelleştirmek" üzerine kuruludur. Faz 5 çıktısındaki ~5 MW'lık fark tam olarak bu nicelleştirmenin kendisidir.
