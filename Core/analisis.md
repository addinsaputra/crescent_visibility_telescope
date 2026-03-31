# Prosedur Evaluasi Model Visibilitas Hilal
## Kerangka Metodologis Pengujian Model Prediksi Biner
### (Revisi 2 — Disesuaikan dengan Desain Eksperimen Hierarchical)

---

## Latar Belakang Desain Riset

Model visibilitas hilal yang dikembangkan dalam skripsi ini berbeda
secara fundamental dari model-model klasik (Yallop, Odeh, Sultan)
karena secara eksplisit memperhitungkan faktor atmosfer lokal
(kelembapan relatif dan temperatur yang berdampak ke penyerapan cahaya oleh partikel debu dan uap air di atmosfer, yang diwakili oleh koefisien ekstingsi k_V)
di samping geometri bulan. Hipotesis sentral riset ini adalah:

> **Faktor atmosfer lokal berperan signifikan dalam menentukan
> keterlihatan hilal, sehingga dua lokasi dengan geometri bulan
> yang hampir identik dapat menghasilkan visibilitas yang berbeda
> akibat perbedaan kondisi atmosfer.**

Desain pengumpulan data secara sadar mengikuti prinsip ini:
- **Blocking by event**: Beberapa lokasi diamati pada satu tanggal
  yang sama, sehingga geometri bulan (elongasi, phase angle,
  semidiameter) menjadi variabel terkontrol secara alami.
  Variasi antar lokasi dalam satu event murni mencerminkan
  perbedaan faktor lokal (RH, T, elevasi, airmass).
- **Blocking by season**: tiga event disebar di musim berbeda
  sepanjang tahun (Juli 2022, Maret 2023, April 2024, Oktober 2024)
  untuk menangkap variasi musiman RH dan T di wilayah tropis
  Indonesia.

Desain ini dalam terminologi statistik disebut **nested/hierarchical
experimental design** atau **randomized complete block design (RCBD)**,
di mana event berfungsi sebagai blocking factor. Konsekuensinya,
evaluasi model harus dilakukan pada dua level:
1. **Level intra-event** (within-block): Apakah model mampu
   membedakan lokasi Y vs N dalam satu event berdasarkan atmosfer?
   Ini adalah uji inti hipotesis riset.
2. **Level antar-event** (between-block): Apakah model robust
   terhadap variasi geometri bulan dan musim yang berbeda?

---

## Struktur Dataset

| Event | Tanggal    | Bulan Hijri       | Musim* | n_lok | Y | N |
|-------|------------|-------------------|--------|-------|---|---|
| 1     | 2022-07-29 | Muharram 1444     | Kemarau| 6     | 1 | 5 |
| 2     | 2023-03-22 | Ramadhan 1444     | Hujan  | 8     | 3 | 5 |
| 3     | 2024-04-09 | Syawal 1445       | Transisi| 7    | 1 | 6 |
| 4     | 2024-10-03 | Rabiul Akhir 1446 | Kemarau| 5     | 1 | 4 |
| **Total** |        |                   |        | **26**| **6** | **20** |

*) Musim untuk Indonesia secara umum; variasi lokal signifikan

Prevalence kelas positif: P(Y) = 6/26 = 23.1%
Imbalance ratio: IR = 20/6 = 3.33
Baseline majority classifier (selalu prediksi N): 20/26 = 76.9%

---

## TAHAP 1: Karakterisasi Dataset dan Verifikasi Desain

### 1.1 Analisis Distribusi Kelas (Class Distribution Analysis)

**Tujuan**: Mengidentifikasi ketidakseimbangan kelas dan implikasinya
terhadap pemilihan metrik evaluasi.

**Prosedur**:
1. Hitung frekuensi absolut dan relatif kelas Y dan N
2. Hitung prevalence kelas positif: P(Y) = n_Y / n_total
3. Hitung baseline accuracy dari majority classifier:
   Acc_naive = n_N / n_total = 76.9%
4. Hitung imbalance ratio: IR = n_majority / n_minority = 3.33

**Output**: Tabel distribusi kelas, prevalence, baseline accuracy

**Catatan**: Karena IR > 3, accuracy sebagai metrik tunggal
menyesatkan. Metrik yang robust terhadap imbalance (MCC, balanced
accuracy, AUC) wajib digunakan sebagai pelengkap.


### 1.2 Verifikasi Struktur Hierarchical (Block Design Verification)

**Tujuan**: Mendokumentasikan dan memverifikasi bahwa desain blocking
bekerja sebagaimana dirancang — yaitu geometri bulan hampir identik
dalam satu event, sementara atmosfer bervariasi.

**Prosedur**:
1. Per event, hitung range variabel geometris antar lokasi:
   - Elongasi: range dan standar deviasi → harus sangat kecil
   - Phase angle: range dan standar deviasi → harus sangat kecil
   - Altitude bulan: range → boleh bervariasi (karena bergantung
     pada lintang lokasi)
2. Per event, hitung range variabel atmosfer antar lokasi:
   - RH: range dan standar deviasi → harus bervariasi signifikan
   - Temperatur: range dan standar deviasi
   - k_V: range dan standar deviasi
3. Hitung rasio variabilitas:
   - CV_geometri = σ_elongasi / mean_elongasi  (harus ≈ 0)
   - CV_atmosfer = σ_RH / mean_RH  (harus >> CV_geometri)
4. Ini memverifikasi bahwa blocking berhasil: variasi geometris
   terkontrol, variasi atmosfer adalah sumber variasi utama

**Output**: Tabel variabilitas intra-event untuk geometri vs atmosfer

**Catatan**: Jika CV_geometri ≈ 0 dan CV_atmosfer >> 0, maka
desain blocking berhasil mengisolasi efek atmosfer dari efek
geometri. Ini adalah fondasi validitas seluruh analisis selanjutnya.


### 1.3 Dokumentasi Variasi Musiman (Seasonal Coverage)

**Tujuan**: Mendokumentasikan bahwa 4 event mencakup variasi musiman
yang cukup untuk menunjukkan robustness model.

**Prosedur**:
1. Catat musim klimatologis setiap event (kemarau, hujan, transisi)
2. Hitung statistik RH dan T per event:
   - Mean, std, min, max RH dan T di semua lokasi per event
3. Bandingkan rentang RH/T antar event:
   - Apakah ada perbedaan signifikan (Kruskal-Wallis test)?
   - Apakah rentang cukup lebar untuk menangkap variasi realistis?

**Output**: Tabel RH/T per event per musim, visualisasi box plot


### 1.4 Statistik Deskriptif Δm per Kelompok

**Teknik**: Statistik Deskriptif + Shapiro-Wilk Normality Test

**Tujuan**: Karakterisasi distribusi skor kontinu Δm.

**Prosedur**:
1. Hitung mean, median, std, min, max, IQR untuk Δm per kelompok (Y vs N)
2. Hitung statistik yang sama per event
3. Uji normalitas distribusi Δm per kelompok menggunakan
   Shapiro-Wilk test (karena n < 50)
4. Visualisasi: box plot atau violin plot Δm per kelompok,
   dengan titik-titik individual ditampilkan (strip plot)

**Output**: Tabel statistik deskriptif, box plot Δm

---

## TAHAP 2: Evaluasi Performa Klasifikasi

### 2.1 Confusion Matrix dan Metrik Klasifikasi (F = 2.0)

**Teknik**: Binary Classification Evaluation

**Tujuan**: Menyajikan performa baseline model sebelum kalibrasi.

**Prosedur**:
1. Untuk setiap observasi: Δm > 0 → prediksi Y, Δm ≤ 0 → prediksi N
2. Konstruksi confusion matrix 2×2
3. Hitung metrik lengkap:

   | Metrik              | Formula                                 | Interpretasi dalam konteks rukyat |
   |---------------------|-----------------------------------------|-----------------------------------|
   | Accuracy            | (TP+TN)/n                               | Proporsi prediksi benar keseluruhan |
   | Sensitivity (Recall)| TP/(TP+FN)                              | Kemampuan model mendeteksi hilal yang memang terlihat |
   | Specificity         | TN/(TN+FP)                              | Keandalan model saat mengatakan "tidak terlihat" |
   | Precision (PPV)     | TP/(TP+FP)                              | Jika model bilang "terlihat", seberapa sering benar |
   | F1 Score            | 2×Prec×Rec/(Prec+Rec)                   | Harmonic mean precision dan recall |
   | MCC                 | (TP×TN−FP×FN)/√((TP+FP)(TP+FN)(TN+FP)(TN+FN)) | Metrik paling robust terhadap imbalance, range [-1,+1] |
   | Balanced Accuracy   | (Sensitivity+Specificity)/2             | Rata-rata akurasi per kelas |

4. Bandingkan setiap metrik secara eksplisit dengan majority classifier

**Output**: Confusion matrix, tabel metrik, perbandingan vs naive


### 2.2 Uji Separabilitas Distribusi Δm

**Teknik**: Mann-Whitney U Test (Wilcoxon Rank-Sum Test)

**Tujuan**: Menguji secara formal apakah distribusi Δm kelompok Y
secara signifikan lebih tinggi dari kelompok N.

**Prosedur**:
1. Hipotesis:
   - H₀: Distribusi Δm kelompok Y = distribusi Δm kelompok N
   - H₁: Δm kelompok Y secara stokastik lebih besar dari kelompok N
2. Gunakan Mann-Whitney U test (non-parametrik) karena:
   - Sampel kecil (n_Y = 6, n_N = 20)
   - Distribusi kemungkinan tidak normal
   - Tidak memerlukan asumsi homogenitas varians
3. Hitung U statistic dan p-value (one-tailed, arah: Y > N)
4. Signifikansi pada α = 0.05

**Ukuran efek (Effect Size)**:
- Rank-biserial correlation: r_rb = 1 − 2U/(n₁×n₂)
  Interpretasi: |r| < 0.3 kecil, 0.3–0.5 sedang, > 0.5 besar
- Cohen's d = (mean_Y − mean_N) / s_pooled
  Interpretasi: d < 0.2 kecil, 0.2–0.8 sedang, > 0.8 besar

**Output**: U statistic, p-value, effect size, interpretasi

**Catatan**: Uji ini menjawab pertanyaan fundamental: "Apakah model
menangkap perbedaan fisik antara kondisi hilal terlihat vs tidak,
meskipun threshold absolutnya belum tepat?" Bahkan jika accuracy
rendah, Mann-Whitney yang signifikan membuktikan model memiliki
discriminative power nyata.


### 2.3 Kemampuan Diskriminatif Keseluruhan

**Teknik**: Receiver Operating Characteristic (ROC) Curve + AUC

**Tujuan**: Mengukur kemampuan model membedakan kelas Y dan N
secara keseluruhan, tidak bergantung pada satu threshold tunggal.

**Prosedur**:
1. Gunakan Δm sebagai decision function (skor kontinu)
2. Variasikan threshold dari −∞ hingga +∞
3. Pada setiap threshold, hitung TPR dan FPR
4. Plot TPR vs FPR → kurva ROC
5. Hitung AUC menggunakan trapezoidal rule
6. Hitung 95% CI untuk AUC menggunakan bootstrap (B = 2000)

**Interpretasi AUC**:
- 0.5 = random, 0.5–0.7 = lemah, 0.7–0.8 = acceptable,
  0.8–0.9 = baik, > 0.9 = sangat baik

**Output**: Plot ROC curve dengan diagonal referensi, AUC ± 95% CI


### 2.4 Analisis Kalibrasi Skor

**Teknik**: Calibration Plot (Reliability Diagram)

**Tujuan**: Menguji apakah magnitude Δm bermakna monoton — Δm lebih
tinggi berkorelasi dengan probabilitas terlihat yang lebih tinggi.

**Prosedur**:
1. Bagi Δm ke dalam bin (misal 4 bin berbasis kuartil)
2. Per bin: hitung jumlah total, jumlah Y, fraksi Y
3. Plot fraksi Y vs midpoint Δm per bin
4. Periksa monotonisitas: fraksi Y harus naik seiring Δm naik

**Output**: Tabel kalibrasi per bin, plot

**Catatan**: Dengan n = 26, bin sangat kasar. Pola monoton vs
non-monoton sudah cukup sebagai bukti kualitatif.

---

## TAHAP 3: Kalibrasi Parameter dan Validasi Generalisasi

### 3.1 Grid Search Field Factor F

**Teknik**: Exhaustive Grid Search (Hyperparameter Tuning)

**Tujuan**: Mencari nilai F yang memaksimalkan performa klasifikasi.

**Prosedur**:
1. Grid: F ∈ [0.5, 5.0], step = 0.1 (46 titik)
2. Untuk setiap F, transformasi Δm menggunakan relasi analitik:
   Δm(F) = Δm(F_ref) + 2.5 × log₁₀(F_ref / F)
3. Tentukan prediksi (Δm > 0 → Y) dan hitung metrik:
   accuracy, sensitivity, specificity, MCC, balanced accuracy
4. Identifikasi F optimal berdasarkan MCC atau balanced accuracy
   (bukan accuracy mentah, karena imbalanced)
5. Sajikan confusion matrix pada F optimal

**Output**: Plot metrik vs F, confusion matrix pada F optimal

**Catatan**: Ini bersifat in-sample. Validasi lewat Tahap 3.2.


### 3.2 Leave-One-Out Cross-Validation (LOOCV)

**Teknik**: LOOCV untuk estimasi performa generalisasi

**Tujuan**: Mengestimasi performa out-of-sample secara jujur,
menghindari data leakage dari kalibrasi F in-sample.

**Prosedur**:
1. Untuk setiap iterasi i = 1, ..., 26:
   a. Keluarkan observasi ke-i (test set)
   b. Dari 25 sisanya (training set), lakukan F-scan dan
      tentukan F_optimal_i (berdasarkan MCC atau balanced accuracy)
   c. Hitung Δm observasi ke-i pada F_optimal_i
   d. Prediksi: Δm > 0 → Y, else → N
   e. Catat prediksi dan F_optimal_i
2. Setelah 26 iterasi:
   a. Hitung confusion matrix dari 26 prediksi out-of-sample
   b. Hitung semua metrik klasifikasi
   c. Analisis stabilitas F_optimal:
      - Mean, std, min, max dari 26 nilai F_optimal_i
      - Jika stabil (std kecil) → kalibrasi robust
      - Jika bervariasi liar → kalibrasi tidak stabil

**Opsi tambahan — Leave-One-Event-Out CV (LOEO-CV)**:
Lebih ketat karena menghormati struktur blocking:
1. Untuk setiap event k = 1, ..., 4:
   a. Keluarkan semua observasi dari event k
   b. Kalibrasi F dari observasi sisa (3 event lain)
   c. Prediksi semua observasi event k
2. Gabungkan 26 prediksi dan hitung metrik
3. Ini hanya menghasilkan 4 fold — varians tinggi, tapi secara
   metodologis paling valid untuk desain hierarchical

**Output**: Confusion matrix LOOCV, metrik out-of-sample,
distribusi F_optimal per fold, perbandingan in-sample vs LOOCV


### 3.3 Uji Signifikansi Perbaikan Model

**Teknik**: McNemar's Exact Test

**Tujuan**: Menguji apakah perubahan klasifikasi setelah kalibrasi F
signifikan secara statistik atau hanya fluktuasi sampling.

**Prosedur**:
1. Konstruksi tabel diskordansi 2×2 antara baseline (F=2.0) dan
   model terkalibrasi (F=F_opt):

   |                     | Terkalibrasi benar | Terkalibrasi salah |
   |---------------------|--------------------|--------------------|
   | Baseline benar      | a                  | b                  |
   | Baseline salah      | c                  | d                  |

2. Uji: apakah b ≠ c? Gunakan exact binomial test karena b+c kecil
3. p-value = binomial test pada min(b,c), n = b+c, p = 0.5

**Output**: Tabel diskordansi, p-value

**Catatan**: Dengan n = 26, perbedaan 1 observasi = 3.8% accuracy.
Jika McNemar tidak signifikan, laporkan secara jujur bahwa
peningkatan tidak dapat dibedakan dari noise statistik.

---

## TAHAP 4: Pembuktian Hipotesis — Peran Atmosfer Lokal

> **Ini adalah tahap inti yang membedakan riset ini dari studi
> visibilitas hilal konvensional. Tahap ini memanfaatkan desain
> hierarchical untuk membuktikan bahwa atmosfer lokal adalah
> faktor determinan keterlihatan hilal.**

### 4.1 Demonstrasi Kegagalan Model Geometris (Benchmarking)

**Teknik**: Model Comparison / Benchmarking vs Kriteria Klasik

**Tujuan**: Menunjukkan secara kuantitatif bahwa model yang hanya
memperhitungkan geometri bulan tidak mampu menjelaskan variasi
keterlihatan antar lokasi pada event yang sama — membuktikan
kebutuhan akan faktor atmosfer.

**Prosedur**:
1. Terapkan kriteria Yallop (1997) pada 26 observasi:
   - Parameter input: ARCV (arc of vision), W (topocentric
     crescent width)
   - Rumus Yallop: q = ARCV − (11.8371 − 6.3226W + 0.7319W²
     − 0.1018W³)
   - Klasifikasi: q > +0.216 → terlihat (A), q < −0.014 → tidak (D/E/F)
   - Zona B/C: intermediat (perlu keputusan threshold)
2. Terapkan kriteria Odeh (2004) pada 26 observasi:
   - Parameter input: ARCV, W
   - Rumus Odeh: V = ARCV − (7.1651 − 6.3226W + 0.7319W²
     − 0.1018W³)
3. Untuk setiap kriteria:
   a. Hitung confusion matrix dan metrik lengkap
   b. Identifikasi prediksi per event — apakah semua lokasi
      dalam satu event mendapat prediksi yang SAMA?
4. Analisis kunci — per event yang memiliki campuran Y dan N:
   a. Prediksi Yallop/Odeh: homogen (semua Y atau semua N)?
   b. Prediksi model Crumey: heterogen (membedakan Y dan N)?
   c. Jika Yallop/Odeh homogen tapi kenyataannya heterogen,
      ini membuktikan bahwa geometri saja tidak cukup.

**Output**: Tabel perbandingan metrik (Crumey vs Yallop vs Odeh),
tabel prediksi per observasi ketiga model, analisis per event

**Interpretasi kunci**: Jika pada event tertentu (misal Ramadhan 1444)
terdapat 3 lokasi Y dan 5 lokasi N, dan Yallop/Odeh memprediksi
semuanya sama (misal semua "terlihat" atau semua "tidak terlihat"),
sedangkan model Crumey setidaknya membedakan sebagian — maka model
Crumey memiliki *resolving power* yang tidak dimiliki model geometris.

**Catatan**: Ini bukan sekadar perbandingan accuracy. Bahkan jika
accuracy Yallop lebih tinggi secara keseluruhan, model Crumey tetap
memiliki keunggulan unik jika ia mampu membedakan lokasi Y dan N
dalam satu event. Argumennya: model geometris "beruntung" karena
mayoritas data memang N (majority class), tapi ia tidak memiliki
mekanisme untuk membedakan kasus-kasus ambigu.


### 4.2 Analisis Intra-Event: Atmosfer sebagai Pembeda

**Teknik**: Within-Block Paired Comparison (Matched-Group Analysis)

**Tujuan**: Memanfaatkan kontrol alami desain blocking untuk menguji
apakah perbedaan atmosfer secara konsisten menjelaskan perbedaan
keterlihatan antar lokasi pada event yang sama.

**Prosedur per event yang memiliki campuran Y dan N**:
1. Identifikasi lokasi Y dan lokasi N dalam event tersebut
2. Bandingkan distribusi variabel atmosfer (Y vs N):
   - RH: mean_Y vs mean_N, selisih, arah
   - T: mean_Y vs mean_N, selisih, arah
   - k_V: mean_Y vs mean_N, selisih, arah
3. Periksa konsistensi arah antar event:
   - Apakah lokasi Y selalu memiliki RH lebih rendah?
   - Apakah lokasi Y selalu memiliki k_V lebih rendah?
4. Uji statistik per event (jika n per group ≥ 3):
   - Permutation test atau exact Mann-Whitney pada RH_Y vs RH_N
   - Dengan n kecil per event, fokus pada arah konsistensi
     antar event (sign test pada selisih)
5. Agregasi lintas event:
   - Hitung selisih mean RH (Y − N) per event → 4 nilai
   - Uji apakah selisih ini konsisten negatif: sign test
     (H₀: P(selisih < 0) = 0.5, H₁: P(selisih < 0) > 0.5)

**Output**: Tabel perbandingan atmosfer Y vs N per event, arah
konsistensi, hasil sign test

**Interpretasi**: Jika di 3 dari 4 event lokasi Y memiliki RH lebih
rendah, sign test memberikan p = 0.3125 (tidak signifikan, karena
hanya 4 event). Jika 4 dari 4 konsisten, p = 0.0625 (marginal).
Hasil ini harus diinterpretasikan secara hati-hati: arah konsistensi
lebih informatif daripada signifikansi formal, mengingat n = 4 event.


### 4.3 Korelasi Variabel Atmosfer dengan Δm

**Teknik**: Korelasi Rank Spearman + Point-Biserial Correlation

**Tujuan**: Mengidentifikasi variabel atmosfer mana yang paling kuat
berkorelasi dengan skor visibilitas model dan dengan keberhasilan
prediksi.

**Prosedur**:
1. Korelasi Spearman antara Δm dan setiap variabel input:
   - RH, T, k_V, moon altitude, elongation, phase angle
   - Spearman dipilih karena non-parametrik dan robust terhadap
     outlier serta hubungan non-linear monoton
2. Point-biserial correlation antara variabel biner "correct"
   (1 = prediksi benar, 0 = salah) dan setiap variabel kontinu
3. Ranking variabel berdasarkan |ρ| (korelasi terkuat → sumber
   variasi terpenting)

**Output**: Matriks korelasi, ranking variabel, scatter plot
Δm vs variabel teratas (k_V, RH)

---

## TAHAP 5: Analisis Sensitivitas dan Ketidakpastian

### 5.1 Analisis Sensitivitas OAT (One-at-a-Time)

**Teknik**: OAT Sensitivity Analysis pada RH

**Tujuan**: Mengukur seberapa sensitif Δm terhadap perturbasi RH.

**Prosedur**:
1. Untuk setiap observasi, variasikan RH:
   ΔRH ∈ {−30, −25, −20, −15, −10, −5, 0, +5, +10} pp
2. Pada setiap level, jalankan rantai fisika lengkap:
   RH → k_V (Schaefer) → L_hilal (Kastner) → Δm (Crumey)
3. Catat Δm pada setiap level → kurva respons Δm(ΔRH)
4. Hitung sensitivity coefficient: S ≈ ΔΔm / ΔRH
5. Identifikasi RH kritis: nilai RH di mana Δm tepat = 0

**Kategorisasi FN berdasarkan RH kritis**:
- Kategori A (near-miss): RH kritis ≤ 5pp dari baseline
  → model hampir benar, error dalam noise atmosfer
- Kategori B (correctable): RH kritis 5–20pp dari baseline
  → error bisa dijelaskan oleh bias ERA5
- Kategori C (structural): RH kritis > 20pp atau di luar range
  → masalah bukan hanya atmosfer, mungkin model Kastner

**Output**: Kurva Δm vs ΔRH per observasi (terutama FN),
tabel RH kritis, kategorisasi FN

**Catatan**: OAT mengasumsikan pengaruh RH dekat-linear. Jika ada
interaksi non-linear kuat, OAT bisa under-estimate total uncertainty.


### 5.2 Dekomposisi Jalur Error (Pathway Ablation Study)

**Teknik**: One-Factor-at-a-Time Pathway Decomposition

**Tujuan**: Mengisolasi kontribusi masing-masing jalur fisika (Kastner
vs Schaefer) terhadap total perubahan Δm saat RH berubah.

**Prosedur**:
1. Dua jalur di mana k_V memengaruhi Δm:
   - Jalur A: k_V → Kastner → L_hilal (luminansi hilal)
   - Jalur B: k_V → Schaefer → B_sky (sky brightness)
2. Untuk setiap FN, hitung tiga skenario (ΔRH = −20pp):
   - Full change: ubah k_V di kedua jalur → Δm_full
   - Only-L: ubah k_V hanya di Kastner → Δm_L
   - Only-B: ubah k_V hanya di Schaefer → Δm_B
3. Dekomposisi:
   - Kontribusi_L = Δm_L − Δm_baseline
   - Kontribusi_B = Δm_B − Δm_baseline
   - Interaksi = Δm_full − Kontribusi_L − Kontribusi_B − Δm_baseline
4. Persentase kontribusi masing-masing jalur

**Output**: Tabel dekomposisi per FN, bar chart kontribusi

**Catatan**: Total kontribusi bisa > 100% karena interaksi. Ini
adalah versi sederhana dari Sobol first-order indices.


### 5.3 Estimasi Interval Ketidakpastian

**Teknik**: Input Uncertainty Propagation (Error Bar Estimation)

**Tujuan**: Mengestimasi "error bar" pada Δm akibat ketidakpastian
data atmosfer reanalisis ERA5.

**Prosedur**:
1. Tentukan σ_RH dari literatur validasi ERA5 di tropis Indonesia:
   σ_RH ∈ {±5, ±10, ±15} percentage points
2. Untuk setiap observasi dan level σ_RH:
   - Δm_low = Δm pada (RH − σ_RH) → atmosfer lebih kering
   - Δm_high = Δm pada (RH + σ_RH) → atmosfer lebih lembab
   - Error bar = |Δm_low − Δm_high| / 2
3. Untuk setiap FN: apakah interval [Δm_high, Δm_low] mencakup 0?
4. Hitung fraksi FN konsisten per level σ_RH

**Output**: Tabel error bar, fraksi FN konsisten

**Koneksi dengan hipotesis riset**: Jika sebagian besar FN konsisten
dalam batas ketidakpastian RH, ini memperkuat argumen bahwa masalah
utama bukan di model fisika — melainkan di kualitas data atmosfer
input. Ini secara langsung mendukung rekomendasi penggunaan AWS
(Automatic Weather Station) in-situ.

---

## TAHAP 6: Analisis Residual dan Pola Error

### 6.1 Kategorisasi Error

**Teknik**: Error Pattern Analysis / Residual Categorization

**Tujuan**: Mengidentifikasi pola sistematik pada kegagalan prediksi.

**Prosedur**:
1. Identifikasi semua FN dan FP
2. Per FN, catat:
   - Magnitude Δm (jarak ke threshold)
   - Parameter astronomi dan atmosfer
   - Lokasi dan event
3. Kategorisasi berdasarkan severity:
   - Near-miss: −1 < Δm ≤ 0
   - Moderate: −3 < Δm ≤ −1
   - Severe: Δm ≤ −3
4. Cari pola: error terkonsentrasi di event/lokasi/kondisi tertentu?

**Output**: Tabel kategorisasi error, scatter plot Δm vs parameter


### 6.2 Korelasi Feature-Error

**Teknik**: Point-Biserial + Spearman Rank Correlation

**Tujuan**: Ranking variabel berdasarkan korelasi dengan error.

**Prosedur**:
1. Variabel biner "correct" (1 = benar, 0 = salah)
2. Point-biserial correlation "correct" vs setiap variabel kontinu
3. Ranking berdasarkan |r|

**Output**: Ranking variabel, scatter plot variabel teratas vs error

---

## TAHAP 7: Sintesis dan Pelaporan

### 7.1 Tabel Ringkasan Performa Komprehensif

| Konfigurasi             | Acc   | Sens  | Spec  | MCC   | B.Acc | AUC   |
|--------------------------|-------|-------|-------|-------|-------|-------|
| Majority classifier      | 76.9% | 0%    | 100%  | 0     | 50%   | 0.500 |
| Model F=2.0 (baseline)   | ...   | ...   | ...   | ...   | ...   | ...   |
| Model F=F_opt (in-sample) | ...  | ...   | ...   | ...   | ...   | ...   |
| Model F=F_opt (LOOCV)    | ...   | ...   | ...   | ...   | ...   | ...   |
| Kriteria Yallop          | ...   | ...   | ...   | ...   | ...   | N/A   |
| Kriteria Odeh            | ...   | ...   | ...   | ...   | ...   | N/A   |

### 7.2 Hierarki Sumber Error

Berdasarkan Tahap 4–6, susun ranking sumber error:
1. **Data atmosfer** (RH → k_V → luminansi) — bukti dari Tahap 5
2. **Model luminansi Kastner** pada elongasi rendah — dari Tahap 6.1
3. **Field factor F** — dari Tahap 3.1
4. **Model sky brightness Schaefer** — dari Tahap 5.2

### 7.3 Bukti Pendukung Hipotesis Riset

Rangkum bukti dari seluruh analisis yang mendukung peran atmosfer:
1. **Tahap 1.2**: Variabilitas intra-event didominasi atmosfer, bukan geometri
2. **Tahap 4.1**: Model geometris gagal membedakan Y dan N dalam satu event
3. **Tahap 4.2**: Lokasi Y secara konsisten memiliki atmosfer lebih jernih
4. **Tahap 4.3**: k_V dan RH berkorelasi kuat dengan Δm
5. **Tahap 5.1**: Perturbasi RH 10–20pp bisa mengubah prediksi FN → Y
6. **Tahap 5.2**: Jalur luminansi (k_V → Kastner) mendominasi error

### 7.4 Keterbatasan yang Wajib Dilaporkan

1. Ukuran sampel kecil (n=26, hanya 4 event independen)
2. Class imbalance (IR = 3.33), metrik accuracy menyesatkan
3. Kalibrasi F bersifat in-sample (dimitigasi LOOCV)
4. OAT sensitivity analysis mengasumsikan linearitas
5. Data ERA5 tidak divalidasi langsung dengan pengukuran in-situ
6. Model Kastner belum divalidasi independen pada elongasi rendah
7. Threshold Crumey dari eksperimen laboratorium (Blackwell 1946)
8. Observasi bersifat binary (terlihat/tidak), tanpa gradasi
   kepercayaan atau metadata kondisi pengamatan detail

---

## Indeks Teknik Analisis

| No | Teknik                              | Tahap | Peran dalam Argumen Riset           |
|----|-------------------------------------|-------|-------------------------------------|
| 1  | Class Distribution Analysis         | 1.1   | Mendeteksi imbalance dataset        |
| 2  | Block Design Verification           | 1.2   | **Memverifikasi kontrol alami**     |
| 3  | Seasonal Coverage Documentation     | 1.3   | **Menunjukkan robustness musiman**  |
| 4  | Shapiro-Wilk Test                   | 1.4   | Uji asumsi distribusi              |
| 5  | Confusion Matrix + MCC              | 2.1   | Performa klasifikasi baseline       |
| 6  | Mann-Whitney U Test                 | 2.2   | **Uji separabilitas formal**       |
| 7  | Effect Size (r_rb, Cohen's d)       | 2.2   | Besarnya perbedaan Y vs N          |
| 8  | ROC Curve + AUC                     | 2.3   | **Diskriminasi keseluruhan**       |
| 9  | Calibration Plot                    | 2.4   | Validitas skor kontinu             |
| 10 | Grid Search F                       | 3.1   | Optimasi parameter                 |
| 11 | Leave-One-Out CV (LOOCV)            | 3.2   | **Validasi generalisasi jujur**    |
| 12 | Leave-One-Event-Out CV              | 3.2   | Validasi respecting blocking       |
| 13 | McNemar's Exact Test                | 3.3   | Signifikansi perbaikan             |
| 14 | Model Benchmarking (Yallop/Odeh)    | 4.1   | **Bukti kebutuhan faktor atmosfer**|
| 15 | Within-Block Paired Comparison      | 4.2   | **Bukti inti: atmosfer as pembeda**|
| 16 | Sign Test (konsistensi antar event) | 4.2   | Konsistensi arah efek atmosfer     |
| 17 | Spearman + Point-Biserial Corr.     | 4.3   | Ranking variabel paling berpengaruh|
| 18 | OAT Sensitivity Analysis            | 5.1   | Sensitivitas Δm terhadap RH       |
| 19 | Pathway Decomposition (Ablation)    | 5.2   | Dekomposisi jalur error            |
| 20 | Uncertainty Propagation             | 5.3   | Error bar dari ketidakpastian ERA5 |
| 21 | Error Pattern Analysis              | 6.1   | Pola kegagalan model               |
| 22 | Feature-Error Correlation           | 6.2   | Variabel penyebab error            |

Teknik yang di-**bold** dalam kolom "Peran" adalah yang langsung
menjawab hipotesis riset tentang peran atmosfer lokal.

---

## Catatan Implementasi

**Tahap 1–3** dan **Tahap 6**: Dapat dilakukan seluruhnya dari data
output batch run yang sudah ada (Δm, RH, T, k_V, elongasi, phase angle
per observasi). Relasi analitik Δm(F) memungkinkan F-scan dan LOOCV
tanpa re-run model.

**Tahap 4**: Benchmarking Yallop/Odeh hanya memerlukan parameter
ARCV dan W yang sudah tersedia dari output batch. Implementasinya
cukup straightforward (<50 baris kode).

**Tahap 5**: Sudah diimplementasikan di `analisis_diagnostik_crumey.py`.
Perlu dipastikan konsistensi dengan dataset 26 observasi (bukan 29).

**Library Python yang diperlukan**:
- scipy.stats: Mann-Whitney U, Shapiro-Wilk, binomial test, spearmanr
- numpy: operasi numerik
- pandas: manipulasi data
- matplotlib: visualisasi