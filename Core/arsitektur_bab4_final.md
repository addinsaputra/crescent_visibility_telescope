# Arsitektur Bab 4 — Evaluasi Model Visibilitas Hilal
## Panduan Final Pengujian dan Analisis

---

## Informasi Dataset

- **Total observasi**: 31 (3 event rukyat, teleskop best time)
- **Distribusi kelas**: 5 Y (terlihat), 26 N (tidak terlihat)
- **Prevalence**: P(Y) = 16.1%
- **Imbalance ratio**: IR = 5.2
- **Baseline majority classifier**: 26/31 = 83.9%
- **Field factor file Excel**: F = 1.5 (sudah terkalibrasi, tanpa bias)
- **Sumber atmosfer utama**: ERA5
- **Sumber atmosfer pembanding**: MERRA-2 (sub-bagian 4.5)
- **File data**: `data_hilal_clean.csv` (31 baris × 32 kolom)
- **Tool analisis statistik**: R/RStudio
- **Tool komputasi fisika**: Python (pipeline Schaefer-Kastner-Crumey)

| Event | Tanggal    | Bulan Hijri   | n   | Y | N |
|-------|------------|---------------|-----|---|---|
| 1     | 2022-07-29 | Muharram 1444 | 10  | 1 | 9 |
| 2     | 2023-03-22 | Ramadhan 1444 | 10  | 3 | 7 |
| 3     | 2024-04-09 | Syawal 1445   | 11  | 1 | 10|
| Total |            |               | 31  | 5 | 26|

---

## Alur Argumentasi

```
4.1 "Ini datanya, baseline F=2.0 buruk"
  ↓
4.2 "Kalibrasi F, validasi dengan LOOCV → F terkunci"
  ↓
4.3 "Evaluasi lengkap pada F optimal — model bermakna"
  ↓
4.4 "Bukti bahwa atmosfer berperan — kontribusi riset"
  ↓
4.5 "Sumber ketidakpastian, sensitivitas, MERRA-2"
```

---

## 4.1 — Presentasi Hasil Model dan Karakterisasi Dataset

### Tujuan
Menyajikan data, memverifikasi desain eksperimen, dan menunjukkan
bahwa baseline F=2.0 setara dengan majority classifier.

### Isi

#### 4.1.1 Tabel Hasil Model (31 observasi)
- Sajikan tabel lengkap: No, Tanggal, Lokasi, Moon Alt, Elongasi,
  W (lebar sabit), Phase Angle, kV, RH, T, Δm Teleskop BT,
  Prediksi, Observasi
- Pisahkan per event untuk menunjukkan struktur blocking

#### 4.1.2 Distribusi Kelas dan Baseline
- Frekuensi: 5 Y vs 26 N
- Prevalence: P(Y) = 16.1%
- Imbalance ratio: 5.2
- Baseline majority classifier: 83.9%
- **Pesan kunci**: accuracy mentah menyesatkan pada dataset ini

#### 4.1.3 Verifikasi Blocking Design
- Per event: hitung std elongasi (harus ≈ 0) vs std RH (harus >> 0)
- Ini membuktikan bahwa geometri terkontrol dan variasi
  antar lokasi murni atmosfer
- **Data sudah menunjukkan**: elongasi range < 1.25° intra-event,
  RH range 10-36 pp intra-event → blocking berhasil

#### 4.1.4 Statistik Deskriptif Δm
- Mean, median, std, min, max, IQR per kelompok Y vs N
- Shapiro-Wilk test per kelompok
- Box plot / strip plot Δm per kelompok
- **Sajikan sekilas**: mean Y = -3.02, mean N = -3.91 →
  arah benar tapi overlap substansial

#### 4.1.5 Confusion Matrix Baseline (F=2.0)
- Hitung Δm pada F=2.0 menggunakan relasi analitik:
  Δm(F=2.0) = Δm(F=1.5) + 2.5 × log₁₀(1.5/2.0) = Δm(F=1.5) − 0.3107
- Sajikan confusion matrix: kemungkinan semua prediksi N
  (sensitivity 0%, specificity 100%, accuracy = 83.9%)
- **Pesan**: F=2.0 identik dengan majority classifier → perlu kalibrasi

### R packages
- `readxl` atau `read.csv()` untuk baca data
- `shapiro.test()` (base R)
- `table()`, `summary()` (base R)
- `ggplot2` untuk box plot

### Estimasi panjang: 3-5 halaman

---

## 4.2 — Kalibrasi Field Factor dan Validasi Generalisasi

### Tujuan
Menemukan F optimal, memvalidasi dengan LOOCV, dan "mengunci" F
untuk seluruh analisis berikutnya.

### Isi

#### 4.2.1 Grid Search F (In-Sample)
- Grid: F ∈ [0.5, 5.0], step 0.1
- Transformasi analitik: Δm(F) = Δm(F_ref) + 2.5 × log₁₀(F_ref/F)
  di mana F_ref = 1.5 dan Δm(F_ref) = Δm dari CSV
- Untuk setiap F: confusion matrix → MCC, balanced accuracy
- **Kriteria pemilihan F optimal: MCC** (bukan accuracy mentah)
  - MCC dipilih karena paling robust terhadap imbalance
  - Balanced accuracy sebagai metrik pendukung
- Plot: MCC, balanced accuracy, sensitivity, specificity vs F
- Sajikan confusion matrix pada F optimal

#### 4.2.2 Leave-One-Out Cross-Validation (LOOCV)
- 31 iterasi: keluarkan 1 observasi, kalibrasi F dari 30 sisanya
  (cari F yang memaksimalkan MCC pada 30 data), prediksi yang
  dikeluarkan pada F tersebut
- Gabungkan 31 prediksi out-of-sample → confusion matrix LOOCV
- Hitung semua metrik pada prediksi LOOCV
- Analisis stabilitas F: mean, std, min, max dari 31 nilai F_optimal_i
  - Jika std kecil → kalibrasi robust/stabil
  - Jika bervariasi → kalibrasi tidak stabil, interpretasi hati-hati
- **Ini adalah jawaban terhadap kritik data leakage**

#### 4.2.3 Leave-One-Event-Out CV (LOEO-CV) — opsional tapi kuat
- 3 fold: keluarkan seluruh event, kalibrasi dari 2 event lain
- Hanya 3 fold → varians tinggi, tapi secara metodologis
  paling valid karena menghormati blocking
- Sajikan sebagai pelengkap LOOCV

#### 4.2.4 McNemar's Test (Baseline vs Optimal)
- Tabel diskordansi 2×2: prediksi F=2.0 vs F optimal
- Exact binomial test (karena n diskordansi kecil)
- Interpretasi: apakah perbaikan signifikan atau noise?

### R packages
- Base R untuk loop F-scan dan LOOCV
- `caret::confusionMatrix()` di dalam loop
- `exact2x2::mcnemar.exact()` atau `binom.test()`

### Catatan penting
- F yang ditemukan di sini digunakan untuk SELURUH analisis
  di Tahap 4.3, 4.4, dan 4.5
- Jika F optimal dari MCC berbeda dari F=1.5 di Excel,
  semua Δm perlu di-recalculate dengan relasi analitik

### Estimasi panjang: 4-6 halaman

---

## 4.3 — Evaluasi Performa Klasifikasi

### Tujuan
Evaluasi komprehensif performa model pada F optimal (sudah divalidasi).
Semua analisis di sini dilakukan SEKALI, pada F yang sudah terkunci.

### Isi

#### 4.3.1 Confusion Matrix dan Metrik Lengkap
- Confusion matrix 2×2 pada F optimal
- Tabel metrik:

  | Metrik            | Nilai | Interpretasi Rukyat                |
  |-------------------|-------|------------------------------------|
  | Accuracy          | ...   | Proporsi prediksi benar            |
  | Sensitivity       | ...   | Deteksi hilal yang terlihat        |
  | Specificity       | ...   | Keandalan prediksi "tidak terlihat"|
  | Precision (PPV)   | ...   | Jika model bilang Y, seberapa sering benar |
  | F1 Score          | ...   | Harmonic mean precision & recall   |
  | MCC               | ...   | Metrik paling robust [-1, +1]      |
  | Balanced Accuracy | ...   | Rata-rata akurasi per kelas        |

- **Bandingkan eksplisit** dengan majority classifier (semua metrik)
- Tabel perbandingan:

  | Konfigurasi        | Acc   | Sens | Spec | MCC  | B.Acc |
  |--------------------|-------|------|------|------|-------|
  | Majority classifier| 83.9% | 0%   | 100% | 0    | 50%   |
  | Model F=2.0        | ...   | ...  | ...  | ...  | ...   |
  | Model F optimal    | ...   | ...  | ...  | ...  | ...   |
  | Model LOOCV        | ...   | ...  | ...  | ...  | ...   |

#### 4.3.2 Uji Separabilitas: Mann-Whitney U Test
- H₀: Distribusi Δm kelompok Y = kelompok N
- H₁: Δm kelompok Y stokastik lebih besar dari N (one-tailed)
- Hitung U statistic, p-value
- Effect size: rank-biserial correlation + Cohen's d
- **Interpretasi**: bahkan jika accuracy tidak tinggi, Mann-Whitney
  signifikan membuktikan model menangkap perbedaan fisik nyata

#### 4.3.3 Kemampuan Diskriminatif: ROC Curve + AUC
- Δm sebagai skor kontinu (decision function)
- Plot ROC curve dengan diagonal referensi
- AUC ± 95% CI (bootstrap, B = 2000)
- Interpretasi: 0.5 = random, >0.7 = acceptable, >0.8 = baik
- **Catatan**: AUC tidak bergantung pada threshold atau F —
  ia mengukur kemampuan intrinsik Δm memisahkan Y dan N

#### 4.3.4 Calibration Plot
- Bagi Δm ke 4 bin (kuartil)
- Per bin: hitung fraksi Y
- Plot fraksi Y vs midpoint Δm
- Periksa monotonisitas: fraksi Y naik seiring Δm naik?
- Dengan n=31 ini bukti kualitatif, bukan kuantitatif

### R packages
- `caret::confusionMatrix(pred, obs, positive="Y")`
- `wilcox.test(Dm ~ Obs, alternative="less")`
- `effectsize::rank_biserial()`, `effectsize::cohens_d()`
- `pROC::roc()`, `pROC::ci.auc()`, `pROC::plot.roc()`
- `ggplot2` untuk calibration plot

### Estimasi panjang: 5-7 halaman

---

## 4.4 — Pembuktian Peran Atmosfer Lokal

### Tujuan
Membuktikan hipotesis sentral: faktor atmosfer lokal berperan
signifikan dalam menentukan keterlihatan hilal, melebihi apa yang
bisa dijelaskan oleh geometri bulan saja.

### Isi

#### 4.4.1 Benchmarking vs Kriteria Yallop dan Odeh
- **Kriteria Yallop (1997)**:
  - ARCV = Moon Altitude (pada sunset atau best time)
  - W = lebar sabit (arcmin, dari kolom W_arcmin di CSV)
  - q = ARCV − (11.8371 − 6.3226W + 0.7319W² − 0.1018W³)
  - Klasifikasi: q > +0.216 → Y, q < −0.014 → N
  - Zona intermediat: perlu keputusan (dokumentasikan pilihan)
- **Kriteria Odeh (2004)**:
  - V = ARCV − (7.1651 − 6.3226W + 0.7319W² − 0.1018W³)
  - Klasifikasi sesuai threshold Odeh
- Untuk kedua kriteria:
  - Confusion matrix + metrik lengkap
  - **Analisis per event**: apakah prediksi HOMOGEN (semua Y atau N)?
- **Argumen kunci**: model geometris memprediksi semua lokasi
  dalam satu event SAMA — tidak bisa membedakan kasus Y dan N
  yang terjadi pada geometri identik. Model Crumey bisa (karena
  memperhitungkan atmosfer).
- Tabel perbandingan 3 model:

  | Model   | Acc   | Sens | Spec | MCC  | Resolving power intra-event |
  |---------|-------|------|------|------|-----------------------------|
  | Yallop  | ...   | ...  | ...  | ...  | Tidak (homogen)             |
  | Odeh    | ...   | ...  | ...  | ...  | Tidak (homogen)             |
  | Crumey  | ...   | ...  | ...  | ...  | Ya (heterogen)              |

#### 4.4.2 Analisis Intra-Event: Atmosfer sebagai Pembeda
- Per event yang punya campuran Y dan N:
  - Bandingkan mean RH, kV, T antara lokasi Y vs N
  - Elongasi dan phase angle harus hampir identik (verifikasi)
  - Arah selisih: apakah lokasi Y punya RH lebih rendah? kV lebih rendah?
- Tabel per event:

  | Event | n_Y | n_N | Mean RH_Y | Mean RH_N | Δ RH  | Arah kV |
  |-------|-----|-----|-----------|-----------|-------|---------|
  | 1     | 1   | 9   | ...       | ...       | ...   | ...     |
  | 2     | 3   | 7   | ...       | ...       | ...   | ...     |
  | 3     | 1   | 10  | ...       | ...       | ...   | ...     |

- Narasi konsistensi arah (deskriptif, bukan sign test karena n=3)

#### 4.4.3 Korelasi Variabel Atmosfer dengan Δm
- Spearman rank correlation: Δm vs RH, kV, T, Moon Alt, Elongasi
- Point-biserial: Observasi (Y/N) vs setiap variabel kontinu
- Ranking variabel berdasarkan |ρ|
- Scatter plot: Δm vs kV (dengan warna Y/N), Δm vs RH

### R packages
- Base R untuk implementasi rumus Yallop/Odeh (5-10 baris)
- `caret::confusionMatrix()` untuk metrik
- `cor.test(method="spearman")`
- `ggplot2` untuk scatter plot

### Estimasi panjang: 5-7 halaman

---

## 4.5 — Analisis Sensitivitas dan Ketidakpastian

### Tujuan
Mengidentifikasi dan mengukur sumber ketidakpastian utama,
memberikan "error bar" pada prediksi model.

### Isi

#### 4.5.1 Sensitivitas OAT terhadap RH
- Variasikan RH: ΔRH ∈ {−30, −25, −20, −15, −10, −5, 0, +5, +10} pp
- Jalankan rantai fisika lengkap per level (Python)
- Plot Δm vs ΔRH per observasi (terutama FN dan FP)
- Hitung RH kritis per FN: nilai RH di mana Δm = 0
- Kategorisasi FN:
  - A (near-miss): RH kritis ≤ 5 pp dari baseline
  - B (correctable): RH kritis 5-20 pp → dalam range bias ERA5
  - C (structural): RH kritis > 20 pp → masalah bukan hanya atmosfer

#### 4.5.2 Dekomposisi Jalur Error
- Dua jalur pengaruh kV:
  - Jalur Kastner: kV → ekstingsi → luminansi hilal
  - Jalur Schaefer: kV → sky brightness
- Teknik one-at-a-time: ubah kV hanya di satu jalur
- Hitung persentase kontribusi masing-masing
- **Temuan yang diharapkan**: Kastner mendominasi (~100%+)

#### 4.5.3 Error Bar dari Ketidakpastian ERA5
- σ_RH dari literatur validasi ERA5 tropis: ±5, ±10, ±15 pp
- Per observasi: Δm_low, Δm_high → error bar
- Per FN: apakah interval mencakup Δm = 0?
- Fraksi FN konsisten per level σ_RH
- **Argumen kunci**: jika mayoritas FN konsisten dalam ±15 pp,
  masalah utama bukan model fisika tapi kualitas data input

#### 4.5.4 Sensitivitas terhadap Sumber Data Atmosfer (ERA5 vs MERRA-2)
- Re-run batch model dengan MERRA-2 (Python)
- Bandingkan per observasi:
  - Scatter plot: Δm(ERA5) vs Δm(MERRA-2)
  - Korelasi Pearson/Spearman
  - Selisih RH dan kV antara kedua sumber
- Confusion matrix MERRA-2 pada F optimal yang sama
- **Interpretasi**:
  - Jika hasil berbeda signifikan → data atmosfer memang bottleneck
  - Jika hasil mirip → model konsisten, data cukup reliabel
- Ini bukan evaluasi ulang lengkap — cukup perbandingan output

### R packages (untuk bagian statistik)
- Bagian 4.5.1-4.5.3 dikerjakan di Python (komputasi fisika)
- Hasilnya di-export ke CSV, dibaca di R untuk visualisasi
- `ggplot2` untuk plot sensitivitas dan error bar
- `cor.test()` untuk korelasi ERA5 vs MERRA-2

### Estimasi panjang: 5-7 halaman

---

## 4.6 — Sintesis (opsional sebagai penutup Bab 4 atau awal Bab 5)

### Tabel Ringkasan Performa

| Konfigurasi          | Acc   | Sens | Spec | MCC  | B.Acc | AUC   |
|----------------------|-------|------|------|------|-------|-------|
| Majority classifier  | 83.9% | 0%   | 100% | 0    | 50%   | 0.500 |
| Model F=2.0          | ...   | ...  | ...  | ...  | ...   | ...   |
| Model F optimal (IS) | ...   | ...  | ...  | ...  | ...   | ...   |
| Model LOOCV (OOS)    | ...   | ...  | ...  | ...  | ...   | ...   |
| Kriteria Yallop      | ...   | ...  | ...  | ...  | ...   | N/A   |
| Kriteria Odeh        | ...   | ...  | ...  | ...  | ...   | N/A   |
| Model + MERRA-2      | ...   | ...  | ...  | ...  | ...   | ...   |

### Hierarki Sumber Error
1. Data atmosfer (RH → kV → luminansi) — dari 4.5.1-4.5.3
2. Model luminansi Kastner pada elongasi rendah — dari FN kategori C
3. Field factor F — dari 4.2
4. Model sky brightness Schaefer — dari 4.5.2

### Bukti Pendukung Hipotesis
1. Blocking berhasil mengisolasi efek atmosfer (4.1.3)
2. Model geometris gagal membedakan Y/N intra-event (4.4.1)
3. Lokasi Y konsisten memiliki atmosfer lebih jernih (4.4.2)
4. kV dan RH berkorelasi kuat dengan Δm (4.4.3)
5. Perturbasi RH kecil bisa mengubah prediksi FN → Y (4.5.1)
6. Jalur Kastner (luminansi) mendominasi sensitivitas (4.5.2)
7. Dua sumber reanalisis memberi hasil berbeda (4.5.4)

---

## Pembagian Kerja Python vs R

| Pekerjaan                              | Tool   | Keterangan                    |
|----------------------------------------|--------|-------------------------------|
| Batch run model (Δm, kV, RH, dll.)    | Python | Sudah ada, pipeline existing  |
| Re-run dengan MERRA-2                 | Python | Ganti 1 baris konfigurasi     |
| Sensitivitas OAT, dekomposisi, error bar | Python | analisis_diagnostik_crumey.py |
| Statistik deskriptif                   | R      | summary(), shapiro.test()     |
| Confusion matrix + metrik             | R      | caret::confusionMatrix()      |
| F-scan + LOOCV                        | R      | Loop + confusionMatrix()      |
| Mann-Whitney, McNemar                 | R      | wilcox.test(), mcnemar.test() |
| ROC/AUC                               | R      | pROC::roc()                   |
| Korelasi Spearman                     | R      | cor.test()                    |
| Benchmarking Yallop/Odeh              | R      | Manual (5-10 baris per model) |
| Semua visualisasi untuk skripsi       | R      | ggplot2                       |

---

## Indeks Teknik Analisis (22 teknik)

| No | Teknik                           | Bagian | Peran                           |
|----|----------------------------------|--------|---------------------------------|
| 1  | Distribusi kelas                 | 4.1.2  | Deteksi imbalance               |
| 2  | Verifikasi blocking design       | 4.1.3  | **Fondasi validitas**           |
| 3  | Shapiro-Wilk test                | 4.1.4  | Uji asumsi distribusi           |
| 4  | Statistik deskriptif Δm          | 4.1.4  | Karakterisasi skor              |
| 5  | Grid search F (in-sample)        | 4.2.1  | Optimasi parameter              |
| 6  | LOOCV                            | 4.2.2  | **Validasi generalisasi**       |
| 7  | LOEO-CV                          | 4.2.3  | Validasi respecting blocking    |
| 8  | McNemar's exact test             | 4.2.4  | Signifikansi perbaikan          |
| 9  | Confusion matrix + MCC           | 4.3.1  | Performa klasifikasi            |
| 10 | Mann-Whitney U test              | 4.3.2  | **Separabilitas formal**        |
| 11 | Effect size (r_rb, Cohen's d)    | 4.3.2  | Besarnya perbedaan Y vs N       |
| 12 | ROC curve + AUC                  | 4.3.3  | **Diskriminasi keseluruhan**    |
| 13 | Calibration plot                 | 4.3.4  | Validitas skor kontinu          |
| 14 | Benchmarking Yallop/Odeh         | 4.4.1  | **Bukti kebutuhan atmosfer**    |
| 15 | Analisis intra-event             | 4.4.2  | **Atmosfer sebagai pembeda**    |
| 16 | Spearman + point-biserial corr.  | 4.4.3  | Ranking variabel berpengaruh    |
| 17 | OAT sensitivity analysis         | 4.5.1  | Sensitivitas Δm terhadap RH    |
| 18 | Kategorisasi FN (A/B/C)          | 4.5.1  | Diagnostik error                |
| 19 | Pathway decomposition            | 4.5.2  | Dekomposisi jalur error         |
| 20 | Uncertainty propagation          | 4.5.3  | Error bar dari ERA5             |
| 21 | Perbandingan ERA5 vs MERRA-2     | 4.5.4  | **Bukti bottleneck data**       |
| 22 | Sintesis hierarki error          | 4.6    | Rangkuman kontribusi riset      |

Teknik **bold** langsung menjawab hipotesis riset.

---

## Keterbatasan yang Wajib Dilaporkan

1. Ukuran sampel kecil (n=31, hanya 3 event independen)
2. Class imbalance berat (IR = 5.2)
3. Kalibrasi F bersifat in-sample (dimitigasi LOOCV)
4. OAT sensitivity mengasumsikan linearitas lokal
5. Data ERA5 tidak divalidasi langsung dengan pengukuran in-situ
6. Model Kastner belum divalidasi independen pada elongasi rendah
7. Threshold Crumey berasal dari eksperimen Blackwell (1946)
8. Observasi biner tanpa gradasi kepercayaan
9. MERRA-2 dan ERA5 keduanya produk reanalisis — bukan ground truth
