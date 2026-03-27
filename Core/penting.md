# Tahapan Pengujian Model untuk Analisis Bab 4 Skripsi

## Deskripsi Tahapan

### Tahap 1: Presentasi Hasil Model (Baseline)

Ini adalah fondasi — tampilkan hasil "apa adanya" sebelum analisis apapun.

- **1a.** Jalankan model untuk 29 observasi pada F = 2.0 (nilai tipikal Crumey). Sajikan tabel lengkap berisi: tanggal, lokasi, altitude bulan, elongasi, phase angle, sky brightness, luminansi hilal, k_V, Δm_naked_eye, Δm_teleskop, prediksi vs observasi.
- **1b.** Hitung confusion matrix awal pada F = 2.0. Ini menjadi baseline performance yang akan dijelaskan dan diperbaiki di tahap-tahap berikutnya.
- **1c.** Kelompokkan hasil per event (4 tanggal rukyat). Ini penting karena geometri bulan (elongasi, phase angle) identik untuk semua lokasi pada tanggal yang sama — jadi variasi antar lokasi murni disebabkan faktor lokal.

### Tahap 2: Analisis Klasifikasi (Error Analysis)

Membedah: di mana model benar, di mana salah, dan seberapa parah.

- **2a.** Identifikasi dan kategorikan setiap observasi ke dalam empat kuadran:
  - True Negative (TN): model bilang N, observasi N — model benar
  - True Positive (TP): model bilang Y, observasi Y — model benar
  - False Negative (FN): model bilang N, observasi Y — model melewatkan yang seharusnya terlihat
  - False Positive (FP): model bilang Y, observasi N — model salah prediksi terlihat
- **2b.** Hitung metrik: accuracy, sensitivity, specificity, precision, F1 score. Interpretasikan artinya masing-masing dalam konteks rukyatul hilal — misalnya specificity tinggi berarti model bisa dipercaya ketika mengatakan "tidak terlihat".
- **2c.** Analisis distribusi Δm: bandingkan rata-rata dan rentang Δm antara kelompok Y dan N. Apakah ada separability — yaitu apakah observasi Y cenderung memiliki Δm lebih tinggi dari N? Jika ya (meskipun keduanya negatif), ini menunjukkan model menangkap tren yang benar meskipun threshold absolutnya belum tepat.

### Tahap 3: Kalibrasi Field Factor

Pertanyaan pertama yang natural: mungkin F = 2.0 bukan nilai yang tepat untuk konteks rukyat hilal di Indonesia?

- **3a.** Lakukan F-scan dari 0.5 sampai 5.0. Untuk setiap F, hitung ulang confusion matrix. Plot accuracy, sensitivity, specificity vs F.
- **3b.** Identifikasi F optimal — nilai F yang memaksimalkan accuracy. Sajikan confusion matrix pada F optimal.
- **3c.** Interpretasi: apakah F optimal masuk akal secara fisik? Crumey menyatakan F = 1 untuk kondisi lab ideal, F ≈ 2 untuk pengamat tipikal, dan F bisa lebih tinggi untuk pengamat yang kurang berpengalaman atau kondisi buruk. Jika F optimal < 1, itu menunjukkan bahwa masalahnya bukan di threshold persepsi — melainkan di input fisik ke model.
- **3d.** Analisis per-observasi: untuk setiap FN, hitung berapa F yang diperlukan agar Δm = 0. Jika sebagian besar membutuhkan F < 1 (apalagi F ≪ 1), maka field factor bukan penyebab utama error — dan analisis harus dilanjutkan ke tahap berikutnya.

### Tahap 4: Diagnosis Input Fisik

Error bukan (hanya) dari field factor. Langkah selanjutnya: periksa setiap komponen input model secara independen.

- **4a. Koefisien Ekstingsi (k_V) sebagai Variabel Kunci** — Bandingkan k_V antara kelompok prediksi benar (TN) dan prediksi salah (FN). Jika FN cenderung memiliki k_V lebih tinggi, ini mengindikasikan bahwa extinction yang terlalu besar menekan luminansi hilal secara berlebihan. Karena k_V dikendalikan oleh RH, ini langsung mengarah ke pertanyaan tentang kualitas data atmosfer.
- **4b. Sensitivitas terhadap RH** — Untuk setiap observasi FN, variasikan RH secara artifisial (misalnya RH_asli, RH-10%, RH-20%, RH-30%) sambil menjaga parameter lain tetap. Catat berapa Δm berubah di setiap level. Ini menunjukkan seberapa sensitif prediksi terhadap ketidakpastian RH. Jika penurunan RH 10-20% sudah cukup mengubah prediksi dari N ke Y, maka ketidakpastian RH dari ERA5 adalah faktor dominan.
- **4c. Dekomposisi Rantai Error** — Untuk setiap observasi FN, dekomposisi kontribusi error dari masing-masing komponen:
  - Rantai sky brightness: RH → k_V → Schaefer → B_sky (nL)
  - Rantai luminansi hilal: phase angle → Kastner magnitude → k_V → airmass → L_hilal (nL)
  - Rantai threshold: B_sky (cd/m²) + luas sabit → Crumey C_th
  - Karena k_V muncul di kedua rantai (mencerahkan langit DAN meredupkan hilal), efeknya berlipat ganda.
- **4d. Perbandingan Antar Lokasi pada Event yang Sama** — Analisis yang sangat kuat karena mengontrol variabel astronomi. Pada tanggal yang sama, elongasi dan phase angle hampir identik untuk semua lokasi. Jadi perbedaan Δm antar lokasi hanya disebabkan oleh: RH (→ k_V), temperatur (→ refraksi), dan altitude bulan (→ airmass). Bandingkan lokasi Y vs N: apa yang berbeda? Apakah lokasi Y selalu memiliki RH lebih rendah?

### Tahap 5: Evaluasi Kualitas Data Reanalisis

Tahap ini menguatkan argumen bahwa data atmosfer adalah bottleneck.

- **5a. Keterbatasan Produk Reanalisis vs Observasi In-Situ** — Jelaskan secara konseptual bahwa ERA5 adalah produk grid ~31 km yang merata-ratakan kondisi atmosfer atas area yang luas. Untuk pengamatan hilal yang sangat sensitif terhadap kondisi lokal saat sunset — terutama di wilayah pesisir dan tropis Indonesia di mana variabilitas RH sangat tinggi — resolusi ini mungkin tidak memadai. Cari dan kutip literatur tentang bias ERA5 untuk RH di wilayah tropis Indonesia.
- **5b. Cross-Validation ERA5 vs MERRA-2** — Jika waktu memungkinkan, jalankan model yang sama dengan MERRA-2 sebagai sumber atmosfer. Bandingkan: apakah hasilnya konsisten? Jika berbeda signifikan, ini membuktikan bahwa data atmosfer memang sumber ketidakpastian utama.
- **5c. Estimasi Magnitude Ketidakpastian** — Berdasarkan literatur bias ERA5 dan hasil sensitivitas RH dari Tahap 4b, estimasi "error bar" pada Δm yang disebabkan oleh ketidakpastian atmosfer. Jika error bar ini mencakup Δm = 0 untuk sebagian besar FN, maka hasil model sebenarnya konsisten dengan observasi dalam batas ketidakpastian.

### Tahap 6: Sintesis dan Kesimpulan

- **6a.** Ringkasan performa model: accuracy, kekuatan (specificity), kelemahan (sensitivity), dan kondisi di mana model paling/kurang akurat.
- **6b.** Hierarki sumber error berdasarkan analisis tahap 3–5. Urutkan dari yang paling berpengaruh: data atmosfer (RH → k_V), model luminansi (Kastner), field factor, dan lainnya.
- **6c.** Rekomendasi konkret untuk penelitian lanjutan, diurutkan berdasarkan dampak yang diharapkan: penggunaan AWS in-situ saat observasi, validasi k_V independen, eksplorasi model luminansi hilal alternatif, dan pengumpulan data F dari pengamat terlatih.

---

## Status Pekerjaan

| Tahap | Deskripsi | Status | Keterangan |
|-------|-----------|--------|------------|
| **1a** | Jalankan model 29 observasi, F=2.0 | ✅ Selesai | `batch_validation_crumey.py` sudah dijalankan |
| **1b** | Confusion matrix baseline (F=2.0) | ✅ Selesai | Ada di Excel: TP=0, TN=23, FP=0, FN=6, Acc=79.3% |
| **1c** | Pengelompokan per event | ✅ Selesai | Sudah dianalisis dari Excel (4 event) |
| **2a** | Kategorisasi TN/TP/FN/FP | ✅ Selesai | Kolom "Cocok?" di Excel |
| **2b** | Metrik klasifikasi | ✅ Selesai | Ada di sheet F-Scan & Ringkasan |
| **2c** | Distribusi Δm (Y vs N) | ✅ Selesai | Sudah dianalisis: mean Y=-2.71, mean N=-4.01 |
| **3a** | F-scan 0.5-5.0 | ✅ Selesai | Sheet "F-Scan Teleskop" + plot PNG |
| **3b** | F optimal + confusion matrix | ✅ Selesai | F_opt=1.5, Acc=82.8% |
| **3c** | Interpretasi F optimal | ✅ Selesai | Sudah dibahas: F=1.5 masih reasonable |
| **3d** | F diperlukan per FN | ✅ Selesai | Sudah dihitung: range 0.004-1.76 |
| **4a** | k_V sebagai variabel kunci | ✅ Selesai | `analisis_diagnostik_crumey.py` — Sheet "4a Korelasi kV" |
| **4b** | Sensitivitas terhadap RH | ✅ Selesai | `analisis_diagnostik_crumey.py` — Sheet "4b Sensitivitas RH" + "4b RH Kritis" |
| **4c** | Dekomposisi rantai error | ✅ Selesai | `analisis_diagnostik_crumey.py` — Sheet "4c Dekomposisi Error" |
| **4d** | Perbandingan antar lokasi per event | ✅ Selesai | `analisis_diagnostik_crumey.py` — Sheet "4d Per-Event" |
| **5a** | Keterbatasan reanalisis (narasi) | ❌ Belum | Bagian penulisan skripsi, bukan koding |
| **5b** | Cross-validation ERA5 vs MERRA-2 | ❌ Belum | Butuh re-run batch dengan MERRA-2 |
| **5c** | Estimasi error bar Δm | ✅ Selesai | `analisis_diagnostik_crumey.py` — Sheet "5c Error Bar" |
| **6a-6c** | Sintesis & kesimpulan | ❌ Belum | Bagian penulisan akhir |

### Ringkasan Status

**Sudah selesai:** Tahap 1-4 dan 5c secara penuh. Mencakup presentasi hasil, analisis klasifikasi, kalibrasi F, diagnosis input fisik, dan estimasi error bar. Dihasilkan oleh `batch_validation_crumey.py` (Tahap 1-3) dan `analisis_diagnostik_crumey.py` (Tahap 4-5c).

**Belum dikerjakan:**
- **5a** dan **6a-6c** — bagian penulisan skripsi (narasi, bukan koding)
- **5b** — cross-validation ERA5 vs MERRA-2 (opsional, tinggal ganti 1 baris konfigurasi dan re-run batch)

---

## Script Diagnostik (`analisis_diagnostik_crumey.py`)

Script diagnostik yang komprehensif. Membaca output batch sebelumnya dan melakukan semua analisis sensitivitas secara lokal (tanpa API call).

### Cara Pakai

1. Letakkan `analisis_diagnostik_crumey.py` di direktori `Core/`
2. Pastikan file `Validasi_Crumey_29obs_era5_optimal.xlsx` ada di `Core/output/`
3. Jalankan: `python analisis_diagnostik_crumey.py`

Script ini **tidak memerlukan koneksi internet** — semua komputasi dilakukan secara lokal menggunakan data baseline dari batch run sebelumnya.

### Apa yang Dihasilkan

**Excel** (`Analisis_Diagnostik_Crumey.xlsx`) dengan 7 sheet:

| Sheet | Tahap | Isi |
|-------|-------|-----|
| 4a Korelasi kV | 4a | Statistik k_V untuk kelompok TN vs FN |
| 4b Sensitivitas RH | 4b | Δm pada 9 level RH untuk semua 29 observasi |
| 4b RH Kritis | 4b | Berapa RH yang diperlukan agar Δm = 0 |
| 4c Dekomposisi Error | 4c | Kontribusi Kastner vs Schaefer untuk 6 FN |
| 4d Per-Event | 4d | Perbandingan statistik Y vs N per tanggal |
| 5c Error Bar | 5c | Apakah error bar ±5/10/15pp RH mencakup Δm=0 |
| Data Detail Sensitivitas | — | Raw data 29x9 = 261 perhitungan |

**Plot 1** (`Sensitivitas_RH_dan_kV.png`):
- Panel kiri: Δm vs ΔRH untuk 6 kasus FN — menunjukkan seberapa sensitif prediksi terhadap RH
- Panel kanan: k_V vs Δm scatter plot, TN (biru) vs FN (merah) — menunjukkan korelasi

**Plot 2** (`Dekomposisi_Error.png`):
- Bar chart dekomposisi: berapa persen error disebabkan oleh luminansi hilal (Kastner) vs sky brightness (Schaefer) vs interaksi keduanya

### Logika Kunci Script

Untuk **sensitivitas RH**, script mengambil RH baseline dari batch run, lalu memvariasikan RH sebesar -30, -25, -20, -15, -10, -5, 0, +5, +10 percentage points. Di setiap level, Schaefer dan Kastner dihitung ulang secara penuh, menghasilkan k_V, B_sky, L_hilal, dan Δm yang baru.

Untuk **dekomposisi error**, script mengisolasi kontribusi masing-masing komponen dengan teknik "one-at-a-time": menurunkan RH 20pp tapi hanya mengubah k_V di Kastner (luminansi) ATAU hanya di Schaefer (sky brightness), lalu membandingkan dengan perubahan penuh. Ini menunjukkan apakah masalah utama ada di hilal yang terlalu redup atau langit yang terlalu terang.

---

## Rangkuman Hasil Pekerjaan Bab 4

### Tahap 1: Presentasi Hasil Model (Baseline)

**Apa yang dilakukan:** Menjalankan model visibilitas hilal (pipeline: Skyfield + Schaefer + Kastner + Crumey) untuk 29 data observasi rukyatul hilal dari 4 event (Juli 2022, Maret 2023, April 2024, Oktober 2024) di berbagai lokasi BMKG Indonesia. Menggunakan sumber atmosfer ERA5, mode optimal (loop dari sunset sampai moonset), teleskop refraktor 66mm x50, dan field factor F = 2.0.

**Hasil:** Semua 29 observasi menghasilkan Δm negatif pada F = 2.0. Model memprediksi seluruh hilal tidak terlihat, menghasilkan 23 True Negative dan 6 False Negative. Accuracy baseline: 79.3%.

**Tool:** `batch_validation_crumey.py` | **Output:** `Validasi_Crumey_29obs_era5_optimal.xlsx`

---

### Tahap 2: Analisis Klasifikasi (Error Analysis)

**Apa yang dilakukan:** Mengkategorikan setiap observasi ke dalam confusion matrix (TN/FN), menghitung metrik klasifikasi, dan membandingkan distribusi Δm antara kelompok Y dan N.

**Hasil:** Specificity 100% (model tidak pernah salah memprediksi "terlihat"), sensitivity 0% pada F = 2.0 (model melewatkan semua 6 observasi Y). Namun, kelompok Y memiliki Δm rata-rata lebih tinggi (-2.71) dibanding N (-4.01), menunjukkan model menangkap *tren* dengan benar meskipun threshold absolutnya belum tepat.

**Tool:** Terintegrasi di `batch_validation_crumey.py` | **Output:** Sheet "Hasil Observasi" dan "Ringkasan"

---

### Tahap 3: Kalibrasi Field Factor

**Apa yang dilakukan:** Scanning field factor F dari 0.5 sampai 5.0 (step 0.1) menggunakan relasi analitik Δm(F) = Δm(F_ref) + 2.5 x log10(F_ref / F). Untuk setiap F, dihitung confusion matrix dan metrik klasifikasi.

**Hasil:** F optimal = 1.5, accuracy = 82.8%, sensitivity = 16.7% (hanya 1 dari 6 Y terdeteksi: Kupang), specificity = 100%. Analisis per-FN menunjukkan bahwa 3 dari 6 FN membutuhkan F < 1 (secara fisik tidak mungkin), membuktikan bahwa **field factor bukan penyebab utama error** — masalahnya ada di input fisik ke model.

**Tool:** Terintegrasi di `batch_validation_crumey.py` | **Output:** Sheet "F-Scan Teleskop", plot `F_Scan_Crumey_29obs_era5_optimal.png`

---

### Tahap 4a: Korelasi k_V dengan Akurasi Prediksi

**Apa yang dilakukan:** Membandingkan statistik koefisien ekstingsi (k_V) dan RH antara kelompok TN dan FN, serta per event.

**Hasil:** FN memiliki k_V rata-rata lebih rendah (0.661) dibanding TN (0.755) — konsisten karena lokasi Y memang cenderung memiliki atmosfer lebih jernih. Namun, bahkan k_V "rendah" di tropis Indonesia (0.38-0.77) sudah cukup untuk menekan luminansi hilal secara eksponensial.

**Tool:** `analisis_diagnostik_crumey.py` | **Output:** Sheet "4a Korelasi kV"

---

### Tahap 4b: Sensitivitas Δm terhadap Variasi RH

**Apa yang dilakukan:** Untuk setiap 29 observasi, RH divariasikan secara artifisial (-30, -25, -20, -15, -10, -5, 0, +5, +10 pp) sambil menjaga parameter astronomi tetap. Di setiap level, Schaefer dan Kastner dihitung ulang secara penuh, menghasilkan k_V, B_sky, L_hilal, dan Δm baru. Juga dihitung RH kritis — nilai RH yang membuat Δm tepat = 0.

**Hasil:** Tiga kategori FN teridentifikasi:
- **Kategori A** (hampir benar): #3 Kupang sudah Δm > 0 pada rekalkulasi, #13 Aceh hanya butuh ΔRH = +0.4pp
- **Kategori B** (bisa diperbaiki): #12 Donggala butuh ΔRH = -4.4pp, #11 Mataram butuh -10.1pp — keduanya dalam range bias ERA5 tropis
- **Kategori C** (tidak bisa diperbaiki hanya oleh RH): #19 dan #26 Manado, RH kritis di luar jangkauan

**Tool:** `analisis_diagnostik_crumey.py` | **Output:** Sheet "4b Sensitivitas RH", "4b RH Kritis", plot `Sensitivitas_RH_dan_kV.png`

---

### Tahap 4c: Dekomposisi Rantai Error

**Apa yang dilakukan:** Untuk 6 observasi FN, mengisolasi kontribusi masing-masing komponen saat RH dikurangi 20pp. Teknik one-at-a-time: mengubah k_V hanya di Kastner (luminansi), hanya di Schaefer (sky brightness), atau keduanya, lalu membandingkan perubahan Δm.

**Hasil:** Luminansi hilal (Kastner) berkontribusi **107.8%** terhadap perubahan Δm, sky brightness (Schaefer) hanya **7.8%** (negatif — artinya sedikit berlawanan arah). Ini membuktikan bahwa k_V memengaruhi prediksi **hampir seluruhnya melalui jalur ekstingsi luminansi**, bukan melalui kecerahan langit. Sensitifitas eksponensial L ∝ e^{-kX} adalah mekanisme fisik yang menjelaskan ini.

**Tool:** `analisis_diagnostik_crumey.py` | **Output:** Sheet "4c Dekomposisi Error", plot `Dekomposisi_Error.png`

---

### Tahap 4d: Perbandingan Antar Lokasi Per Event

**Apa yang dilakukan:** Membandingkan rata-rata RH, k_V, dan Δm antara lokasi Y dan N pada setiap tanggal rukyat (geometri bulan identik, variasi murni lokal).

**Hasil:**
- **Event Juli 2022** — lokasi Y (Kupang) memiliki RH 20pp lebih rendah dari rata-rata N, kasus ideal di mana atmosfer jernih menjelaskan visibilitas
- **Event Maret 2023** — selisih RH hanya 2.9pp, menunjukkan faktor selain RH berperan (mungkin awan tipis, transparansi sesaat)
- **Event Oktober 2024** — **anomali**: lokasi Y (Manado) justru memiliki RH 8.5pp lebih tinggi dari rata-rata N, kontradiksi fisik yang mengindikasikan perlu tinjauan ulang data observasi atau adanya faktor non-atmosferik

**Tool:** `analisis_diagnostik_crumey.py` | **Output:** Sheet "4d Per-Event"

---

### Tahap 5c: Estimasi Error Bar Δm

**Apa yang dilakukan:** Menggunakan ketidakpastian RH ERA5 dari literatur (±5, ±10, ±15 pp) untuk menghitung error bar pada Δm setiap observasi FN. Memeriksa apakah error bar mencakup Δm = 0 (artinya prediksi konsisten dengan observasi dalam batas ketidakpastian).

**Hasil:** Pada ketidakpastian ±15pp: **4 dari 6 FN konsisten** dengan observasi. Dua yang tidak konsisten (#19 dan #26 Manado) memiliki Δm terlalu negatif untuk dijelaskan oleh ketidakpastian RH saja — menunjukkan kemungkinan keterbatasan model Kastner pada elongasi rendah atau masalah pada data observasi itu sendiri.

**Tool:** `analisis_diagnostik_crumey.py` | **Output:** Sheet "5c Error Bar"

---

### Tahap yang Belum Dikerjakan

| Tahap | Deskripsi | Status |
|-------|-----------|--------|
| **5a** | Narasi keterbatasan reanalisis vs observasi in-situ | Penulisan skripsi |
| **5b** | Cross-validation ERA5 vs MERRA-2 | Opsional — tinggal ganti 1 baris konfigurasi dan re-run batch |
| **6a-6c** | Sintesis temuan dan rekomendasi | Penulisan skripsi |

---

### Hierarki Sumber Error (Kesimpulan Sementara)

Berdasarkan seluruh analisis di atas, urutan faktor pembatas akurasi model dari yang paling berpengaruh:

1. **Data atmosfer (RH → k_V → luminansi hilal)** — kontribusi 108%, faktor dominan
2. **Model luminansi Kastner** pada elongasi rendah — 2 dari 6 FN tidak bisa dijelaskan oleh RH saja
3. **Field factor** — bukan penyebab utama, tapi kalibrasi F = 1.5 meningkatkan accuracy dari 79.3% ke 82.8%
4. **Model sky brightness Schaefer** — kontribusi hanya 7.8%, bukan bottleneck

---

## Evaluasi 6 Tahapan Pengujian Model

Secara keseluruhan, pekerjaan **sudah sangat kuat** — jauh melebihi standar skripsi biasa. Tapi ada beberapa celah metodologis yang perlu disadari, baik untuk diperbaiki maupun untuk dijelaskan secara jujur di skripsi.

### Yang Sudah Dilakukan dengan Baik

**Confusion Matrix & Metrik Klasifikasi (Tahap 1-2)** adalah fondasi yang tepat. Tidak hanya melaporkan accuracy mentah, tapi juga memisahkan sensitivity dan specificity — ini krusial karena konteks rukyatul hilal sangat asimetris (konsekuensi *false positive* berbeda dari *false negative* secara fikih/astronomi). Ini setara dengan praktik terbaik di data science.

**F-scan (Tahap 3)** adalah analogi langsung dari *hyperparameter tuning* di ML. F tidak dipilih secara subjektif, tapi dicari secara sistematis dengan melihat respons metrik terhadap variasi parameter — ini solid.

**Sensitivitas RH (Tahap 4b)** dan **Dekomposisi Error (Tahap 4c)** adalah yang paling canggih. Tahap 4b setara dengan *sensitivity analysis* dan Tahap 4c setara dengan *ablation study* — dua teknik yang bahkan sering absen di paper ML sekalipun. Temuan bahwa luminansi hilal berkontribusi 107.8% sementara sky brightness hanya 7.8% adalah kontribusi orisinal yang kuat.

**Error Bar & Ketidakpastian (Tahap 5c)** setara dengan *confidence interval estimation* — menunjukkan bahwa tidak sekadar melaporkan angka titik, tapi mengakui batas ketidakpastian model.

### Celah Metodologis yang Perlu Diperhatikan

#### 1. Data Leakage pada Kalibrasi F

Celah paling kritis. F_optimal = 1.5 ditemukan dengan menscan seluruh 29 observasi yang **sama** dengan yang dipakai untuk evaluasi akhir. Dalam terminologi data science, ini adalah **data leakage** — parameter model disetel menggunakan data uji, sehingga skor accuracy 82.8% tidak murni mencerminkan performa generalisasi.

Untuk skripsi, perlu **didiskusikan secara eksplisit** di Bab 4 atau Bab 5. Argumen yang jujur: "Dengan 29 observasi yang terbatas, pemisahan data latih dan data uji tidak praktis. F = 1.5 adalah hasil kalibrasi *in-sample*, bukan validasi *out-of-sample*. Generalisasi ke dataset independen perlu diuji di penelitian lanjutan."

#### 2. Ilusi Accuracy: Model Baseline = Classifier Naif

Dataset memiliki 23 N dan 6 Y dari 29 total. Seorang *dummy classifier* yang **selalu memprediksi "tidak terlihat"** tanpa hitung apapun akan mendapat accuracy = 23/29 = **79.3%** — persis sama dengan baseline model di F = 2.0!

Ini adalah jebakan klasik pada dataset yang tidak seimbang (*imbalanced*). Accuracy saja menyesatkan. Yang membuktikan model *bermakna* sebenarnya bukan accuracy-nya, melainkan:
- Fakta bahwa distribusi Δm kelompok Y (rata-rata -2.71) berbeda dari N (-4.01) secara konsisten — model menangkap *tren fisik* yang benar
- Specificity 100% — model tidak pernah salah memprediksi "terlihat"

Ini perlu dinarasikan dengan hati-hati agar pembaca tidak salah membaca angka 79.3%.

#### 3. Tidak Ada ROC Curve dan AUC

Ada skor kontinu (Δm) untuk setiap observasi, yang artinya bisa mengkonstruksi **ROC curve** dengan memvariasikan threshold Δm = 0 ke nilai-nilai lain. AUC-ROC mengukur kemampuan diskriminasi model secara lebih holistik dibanding accuracy tunggal di satu threshold.

Ini bukan kewajiban, tapi akan sangat memperkuat argumen bahwa model secara statistik lebih baik dari klasifikasi acak. Dengan 29 observasi pun, ROC curve sudah informatif.

#### 4. Tidak Ada Uji Statistik pada Perbedaan Metrik

Ketika dilaporkan accuracy meningkat dari 79.3% ke 82.8% setelah kalibrasi F, apakah peningkatan 3.5% ini **signifikan secara statistik** atau hanya noise dari 1 observasi yang berubah klasifikasi? Dengan n=29, selisih 1 observasi = 3.4% accuracy, jadi "peningkatan" ini hanya setara 1 data point.

Untuk ini bisa digunakan **McNemar's test** — uji statistik khusus untuk membandingkan dua model pada dataset yang sama. Atau cukup nyatakan secara naratif: "Peningkatan sebesar 3.4 pp setara dengan 1 observasi, sehingga interpretasinya harus hati-hati mengingat ukuran dataset yang terbatas."

#### 5. Cross-Validation Tidak Dilakukan

Dengan hanya 29 data point dan 6 kasus positif, **Leave-One-Out Cross-Validation (LOOCV)** sangat relevan. Pada setiap iterasi, satu observasi dikeluarkan, F dikalibrasi dari 28 sisanya, lalu prediksi dilakukan pada observasi yang dikeluarkan. Ini memberikan estimasi performa yang jauh lebih jujur. Tahap 5b (ERA5 vs MERRA-2) yang ditandai opsional sebenarnya *sebagian* menjalankan fungsi ini — cross-validasi sumber data atmosfer.

### Gambaran Evaluasi Menyeluruh

```
Komponen Pengujian                    Status
──────────────────────────────────────────────────────
Pemisahan data (train/test)           ⚠️  Tidak ada — in-sample
Cross-validation                      ❌  Belum (LOOCV cocok)
Metrik klasifikasi lengkap            ✅  Sudah (acc/sens/spec/F1)
ROC curve & AUC                       ❌  Belum
Analisis residual (distribusi Δm)     ✅  Sudah
Hyperparameter tuning (F-scan)        ✅  Sudah (tapi in-sample)
Sensitivity analysis                  ✅  Tahap 4b — sangat kuat
Ablation study                        ✅  Tahap 4c — sangat kuat
Uji statistik antar model             ❌  Belum (McNemar's)
Error bar / uncertainty               ✅  Tahap 5c
Extreme case testing                  ✅  Analisis FN per-kategori
Perbandingan benchmark                ⚠️  Parsial (belum vs Yallop/dll.)
```

