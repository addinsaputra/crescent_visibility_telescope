## Rangkuman Pekerjaan Bab 4: Hasil dan Pembahasan

### Tahap 1: Presentasi Hasil Model (Baseline)

**Apa yang dilakukan:** Menjalankan model visibilitas hilal (pipeline: Skyfield + Schaefer + Kastner + Crumey) untuk 29 data observasi rukyatul hilal dari 4 event (Juli 2022, Maret 2023, April 2024, Oktober 2024) di berbagai lokasi BMKG Indonesia. Menggunakan sumber atmosfer ERA5, mode optimal (loop dari sunset sampai moonset), teleskop refraktor 66mm ×50, dan field factor F = 2.0.

**Hasil:** Semua 29 observasi menghasilkan Δm negatif pada F = 2.0. Model memprediksi seluruh hilal tidak terlihat, menghasilkan 23 True Negative dan 6 False Negative. Accuracy baseline: 79.3%.

**Tool:** `batch_validation_crumey.py`
**Output:** `Validasi_Crumey_29obs_era5_optimal.xlsx`

---

### Tahap 2: Analisis Klasifikasi (Error Analysis)

**Apa yang dilakukan:** Mengkategorikan setiap observasi ke dalam confusion matrix (TN/FN), menghitung metrik klasifikasi, dan membandingkan distribusi Δm antara kelompok Y dan N.

**Hasil:** Specificity 100% (model tidak pernah salah memprediksi "terlihat"), sensitivity 0% pada F = 2.0 (model melewatkan semua 6 observasi Y). Namun, kelompok Y memiliki Δm rata-rata lebih tinggi (−2.71) dibanding N (−4.01), menunjukkan model menangkap *tren* dengan benar meskipun threshold absolutnya belum tepat.

**Tool:** Sudah terintegrasi di `batch_validation_crumey.py`
**Output:** Sheet "Hasil Observasi" dan "Ringkasan" di Excel

---

### Tahap 3: Kalibrasi Field Factor

**Apa yang dilakukan:** Scanning field factor F dari 0.5 sampai 5.0 (step 0.1) menggunakan relasi analitik Δm(F) = Δm(F_ref) + 2.5 × log₁₀(F_ref / F). Untuk setiap F, dihitung confusion matrix dan metrik klasifikasi.

**Hasil:** F optimal = 1.5, accuracy = 82.8%, sensitivity = 16.7% (hanya 1 dari 6 Y terdeteksi: Kupang), specificity = 100%. Analisis per-FN menunjukkan bahwa 3 dari 6 FN membutuhkan F < 1 (secara fisik tidak mungkin), membuktikan bahwa **field factor bukan penyebab utama error** — masalahnya ada di input fisik ke model.

**Tool:** Sudah terintegrasi di `batch_validation_crumey.py`
**Output:** Sheet "F-Scan Teleskop", plot `F_Scan_Crumey_29obs_era5_optimal.png`

---

### Tahap 4a: Korelasi k_V dengan Akurasi Prediksi

**Apa yang dilakukan:** Membandingkan statistik koefisien ekstingsi (k_V) dan RH antara kelompok TN dan FN, serta per event.

**Hasil:** FN memiliki k_V rata-rata lebih rendah (0.661) dibanding TN (0.755) — konsisten karena lokasi Y memang cenderung memiliki atmosfer lebih jernih. Namun, bahkan k_V "rendah" di tropis Indonesia (0.38–0.77) sudah cukup untuk menekan luminansi hilal secara eksponensial.

**Tool:** `analisis_diagnostik_crumey.py`
**Output:** Sheet "4a Korelasi kV"

---

### Tahap 4b: Sensitivitas Δm terhadap Variasi RH

**Apa yang dilakukan:** Untuk setiap 29 observasi, RH divariasikan secara artifisial (−30, −25, −20, −15, −10, −5, 0, +5, +10 pp) sambil menjaga parameter astronomi tetap. Di setiap level, Schaefer dan Kastner dihitung ulang secara penuh, menghasilkan k_V, B_sky, L_hilal, dan Δm baru. Juga dihitung RH kritis — nilai RH yang membuat Δm tepat = 0.

**Hasil:** Tiga kategori FN teridentifikasi. Kategori A (hampir benar): #3 Kupang sudah Δm > 0 pada rekalkukasi, #13 Aceh hanya butuh ΔRH = +0.4pp. Kategori B (bisa diperbaiki): #12 Donggala butuh ΔRH = −4.4pp, #11 Mataram butuh −10.1pp — keduanya dalam range bias ERA5 tropis. Kategori C (tidak bisa diperbaiki hanya oleh RH): #19 dan #26 Manado, RH kritis di luar jangkauan.

**Tool:** `analisis_diagnostik_crumey.py`
**Output:** Sheet "4b Sensitivitas RH", "4b RH Kritis", plot panel kiri `Sensitivitas_RH_dan_kV.png`

---

### Tahap 4c: Dekomposisi Rantai Error

**Apa yang dilakukan:** Untuk 6 observasi FN, mengisolasi kontribusi masing-masing komponen saat RH dikurangi 20pp. Teknik one-at-a-time: mengubah k_V hanya di Kastner (luminansi), hanya di Schaefer (sky brightness), atau keduanya, lalu membandingkan perubahan Δm.

**Hasil:** Luminansi hilal (Kastner) berkontribusi **107.8%** terhadap perubahan Δm, sky brightness (Schaefer) hanya **7.8%** (negatif — artinya sedikit berlawanan arah). Ini membuktikan bahwa k_V memengaruhi prediksi **hampir seluruhnya melalui jalur ekstingsi luminansi**, bukan melalui kecerahan langit. Sensitifitas eksponensial L ∝ e^{−kX} adalah mekanisme fisik yang menjelaskan ini.

**Tool:** `analisis_diagnostik_crumey.py`
**Output:** Sheet "4c Dekomposisi Error", plot `Dekomposisi_Error.png`

---

### Tahap 4d: Perbandingan Antar Lokasi Per Event

**Apa yang dilakukan:** Membandingkan rata-rata RH, k_V, dan Δm antara lokasi Y dan N pada setiap tanggal rukyat (geometri bulan identik, variasi murni lokal).

**Hasil:** Event Juli 2022 — lokasi Y (Kupang) memiliki RH 20pp lebih rendah dari rata-rata N, kasus ideal di mana atmosfer jernih menjelaskan visibilitas. Event Maret 2023 — selisih RH hanya 2.9pp, menunjukkan faktor selain RH berperan (mungkin awan tipis, transparansi sesaat). Event Oktober 2024 — **anomali**: lokasi Y (Manado) justru memiliki RH 8.5pp lebih tinggi dari rata-rata N, kontradiksi fisik yang mengindikasikan perlu tinjauan ulang data observasi atau adanya faktor non-atmosferik.

**Tool:** `analisis_diagnostik_crumey.py`
**Output:** Sheet "4d Per-Event"

---

### Tahap 5c: Estimasi Error Bar Δm

**Apa yang dilakukan:** Menggunakan ketidakpastian RH ERA5 dari literatur (±5, ±10, ±15 pp) untuk menghitung error bar pada Δm setiap observasi FN. Memeriksa apakah error bar mencakup Δm = 0 (artinya prediksi konsisten dengan observasi dalam batas ketidakpastian).

**Hasil:** Pada ketidakpastian ±15pp: **4 dari 6 FN konsisten** dengan observasi. Dua yang tidak konsisten (#19 dan #26 Manado) memiliki Δm terlalu negatif untuk dijelaskan oleh ketidakpastian RH saja — menunjukkan kemungkinan keterbatasan model Kastner pada elongasi rendah atau masalah pada data observasi itu sendiri.

**Tool:** `analisis_diagnostik_crumey.py`
**Output:** Sheet "5c Error Bar"

---

### Tahap yang Belum Dikerjakan

| Tahap | Deskripsi | Status |
|-------|-----------|--------|
| **5a** | Narasi keterbatasan reanalisis vs observasi in-situ | Penulisan skripsi |
| **5b** | Cross-validation ERA5 vs MERRA-2 | Opsional — tinggal ganti 1 baris konfigurasi dan re-run batch |
| **6a–6c** | Sintesis temuan dan rekomendasi | Penulisan skripsi |

---

### Hierarki Sumber Error (Kesimpulan Sementara)

Berdasarkan seluruh analisis di atas, urutan faktor pembatas akurasi model dari yang paling berpengaruh:

1. **Data atmosfer (RH → k_V → luminansi hilal)** — kontribusi 108%, faktor dominan
2. **Model luminansi Kastner** pada elongasi rendah — 2 dari 6 FN tidak bisa dijelaskan oleh RH saja
3. **Field factor** — bukan penyebab utama, tapi kalibrasi F = 1.5 meningkatkan accuracy dari 79.3% ke 82.8%
4. **Model sky brightness Schaefer** — kontribusi hanya 7.8%, bukan bottleneck