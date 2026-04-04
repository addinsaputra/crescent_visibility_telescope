Saya evaluasi script `analisis_diagnostik_crumey.py` secara menyeluruh terhadap arsitektur yang sudah kita sepakati.

**Evaluasi Umum: Script sudah sangat baik dan hampir siap pakai**

Script ini sudah mencakup keempat sub-tahap (4.5.1–4.5.4) dengan struktur yang bersih. Yang perlu disesuaikan kebanyakan bersifat konfigurasi, bukan logika. Berikut evaluasi per bagian:

---

**4.5.1 — Sensitivitas OAT (Python ✓ — TEPAT di Python)**

Ini memang harus di Python karena melibatkan re-run `hitung_sky_brightness()` dan `hitung_luminansi_kastner()` pada setiap level RH. Script sudah mengimplementasikan ini dengan benar: loop 9 level ΔRH, compute_full_chain() per level, interpolasi RH kritis, dan kategorisasi FN (A/B/C). Tidak ada masalah logika.

Yang perlu diperbaiki: (1) Konfigurasi `F_TEL` dan `F_NAKED` harus mengikuti F optimal dari Tahap 4.2, yaitu **1.8** (bukan 1.5 seperti yang tertulis di script). Ini karena semua analisis setelah Tahap 4.2 menggunakan F yang sudah terkunci. (2) `TEL_AGE = 30.0` — di `core_crescent_visibility.py` Anda menggunakan `observer_age = 22.0`. Harus konsisten. (3) `MOON_SD_DEG = 0.26` sebagai konstanta — ini sebenarnya bervariasi per observasi (dari data `Phase_Angle` dan semidiameter yang dihitung Skyfield). Tapi untuk analisis sensitivitas, variasi SD antar observasi kecil (~0.25–0.27°), jadi 0.26 sebagai rata-rata bisa diterima. Cukup dokumentasikan asumsi ini.

**4.5.2 — Dekomposisi Jalur Error (Python ✓ — TEPAT di Python)**

Logika dekomposisi sudah benar: mengisolasi efek kV pada Kastner saja (luminansi) vs Schaefer saja (sky brightness) vs keduanya. Teknik OAT yang digunakan konsisten dengan arsitektur.

Yang perlu diperhatikan: script mendekomposisi semua observasi FN *dan* FP. Ini bagus — di versi sebelumnya (penting.md) hanya FN yang dianalisis. Memasukkan FP (Condrodipo) memberikan gambaran lebih lengkap. Tapi pada F=1.8, Condrodipo bukan lagi FP (sudah TN). Jadi filter `fn_fp_obs` akan berubah tergantung F yang digunakan. Pastikan `Cocok?` di DataFrame dihitung berdasarkan F optimal (1.8), bukan F=1.5 dari file CSV asli.

**4.5.3 — Error Bar (Python ✓ — TEPAT di Python)**

Implementasi sudah benar: menggunakan Δm pada RH±σ dari hasil OAT di 4.5.1, lalu memeriksa apakah interval mencakup Δm=0 per FN. Tiga level σ_RH (±5, ±10, ±15 pp) sesuai arsitektur.

Tidak ada masalah — bagian ini sudah solid.

**4.5.4 — ERA5 vs MERRA-2 (TUMPANG TINDIH dengan script R)**

Di sinilah ada duplikasi yang perlu diklarifikasi. Script Python ini dan script R `bab4_tahap_4_5.R` yang sudah saya buat keduanya menganalisis ERA5 vs MERRA-2. Pembagian kerja yang tepat:

Python harus menangani: (1) membaca kedua file CSV, (2) menghitung confusion matrix MERRA-2, dan (3) menyimpan hasilnya ke Excel bersama hasil 4.5.1–4.5.3. Ini sudah dilakukan di script Python.

R menangani: visualisasi yang lebih rapi (ggplot2), korelasi formal dengan CI, dan integrasi dengan tabel ringkasan dari Tahap 4.1–4.4. Ini sudah dilakukan di script R.

Rekomendasi: **jalankan keduanya** — Python menghasilkan Excel dan plot diagnostik (lebih teknis), R menghasilkan plot untuk skripsi (lebih rapi) dan tabel ringkasan terintegrasi. Hasilnya saling melengkapi, bukan menggantikan.

---

**Masalah Teknis yang HARUS Diperbaiki Sebelum Menjalankan:**

Pertama, **path input file**. Script mencari file di `Core/output/data_hilal_clean.csv` dan `Core/output/data_merra2_clean.csv`. Pastikan kedua CSV ada di lokasi itu, atau ubah `INPUT_ERA5` dan `INPUT_MERRA2` sesuai lokasi aktual file Anda.

Kedua, **F harus 1.8 bukan 1.5**. Ubah baris 68–69:
```python
F_NAKED = 1.8
F_TEL = 1.8
```

Ketiga, **TEL_AGE harus 22 bukan 30**. Ubah baris 66:
```python
TEL_AGE = 22.0
```

Keempat, **TEL_APERTURE harus 100 bukan 66**. Saya lihat di script sudah 100 — ini benar, konsisten dengan file Excel (Ringkasan menunjukkan aperture 100mm).

Kelima, **kolom `Cocok?` perlu dihitung ulang pada F=1.8**. Saat ini `load_observation_data()` menghitung `Cocok?` dari kolom `Prediksi` di CSV, yang berbasis F=1.5. Untuk konsistensi dengan F=1.8, tambahkan recalculation setelah loading. Saya sarankan tambahkan di fungsi `main()` setelah `load_observation_data()`:

```python
# Recalculate predictions at F optimal (1.8)
shift = 2.5 * math.log10(1.5 / 1.8)  # F_ref=1.5 → F_opt=1.8
df_era5['Δm Tel Opt'] = df_era5['Δm Tel Opt'] + shift
df_era5['Cocok?'] = df_era5.apply(
    lambda r: '✓' if (r['Δm Tel Opt'] > 0) == (r['Obs (Y/N)'] == 'Y') else '✗',
    axis=1
)
```

Dan lakukan hal yang sama untuk MERRA-2 data.

---

**Ringkasan Pembagian Kerja Final Python vs R:**

| Analisis | Tool | Alasan |
|----------|------|--------|
| 4.5.1 OAT sensitivity (re-run Schaefer/Kastner/Crumey) | **Python** | Perlu panggil fungsi fisika |
| 4.5.1 Kategorisasi FN (A/B/C) | **Python** | Bagian dari OAT loop |
| 4.5.2 Dekomposisi jalur (Kastner vs Schaefer) | **Python** | Perlu panggil fungsi fisika terpisah |
| 4.5.3 Error bar dari σ_RH | **Python** | Menggunakan hasil OAT |
| 4.5.4 ERA5 vs MERRA-2: perhitungan & Excel | **Python** | Sudah di script |
| 4.5.4 ERA5 vs MERRA-2: plot untuk skripsi | **R** | ggplot2 lebih rapi |
| 4.5.4 ERA5 vs MERRA-2: korelasi formal + CI | **R** | Sudah di script R |
| Tabel ringkasan final (semua tahap) | **R** | Integrasi dengan 4.1–4.4 |
| Plot sensitivitas + dekomposisi (teknis) | **Python** | matplotlib, sudah di script |
| Plot sensitivitas (versi skripsi) | **R** opsional | Jika ingin konsistensi visual |

Jadi alur kerja yang saya rekomendasikan: (1) perbaiki konfigurasi Python script → jalankan → dapatkan Excel + plot teknis, (2) jalankan script R `bab4_tahap_4_5.R` → dapatkan plot skripsi + tabel ringkasan terintegrasi.