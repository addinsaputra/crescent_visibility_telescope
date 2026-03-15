
# Ringkasan prosedur — implementasi rumus Crumey (extended source) + koreksi teleskop

---

## 1 — Input mentah (dari data / model)

* `B_raw` = sky brightness (pilih satuan; mis. **nanoLambert (nL)** atau  **cd·m⁻²** ).
* `L_t_raw` = luminance hilal (permukaan bercahaya) — sama satuannya seperti `B`.
* `A_raw` = area angular hilal (mis. **arcmin²** atau  **steradian** ).

---

## 2— Hitung faktor-faktor teleskop (Schaefer-style)

* Exit pupil: `D_exit = D_obj / M`.
* Pupil factor:
  `F_p = (D_exit / D_eye)**2` if `D_exit < D_eye` else `F_p = 1`.
* Aperture collecting factor: `F_a = (D_obj / D_eye)**2` (dipakai sesuai skema Anda).
* Throughput/transmission: `F_t = tau` (produk transmisivitas semua elemen).
* Magnification effect on sky surface brightness: `F_m = 1 / M**2` (berlaku pada  *sky* ).
* Warna / photopic–scotopic: `F_c` (aplikasikan pada B dan Lt bila diketahui).
* Faktor-faktor tambahan (seeing, Stiles–Crawford, observer skill) gunakan `F_r, F_sc, F_s` sesuai kebutuhan.

---

## 3— Terapkan koreksi ke luminansi/illuminance

Untuk **extended source (hilal)**:

* `L_t_corr = L_t_raw * F_t * F_p * F_a * F_sc * F_c`
* `B_corr = B_raw * F_t * F_p * F_a * F_sc * F_c * F_m`

(urutan multiplikatif—kecuali faktor-faktor khusus yang hanya berlaku ke objek atau ke sky; sesuaikan sesuai mapping Schaefer yang Anda gunakan).

## 4 — Konversi satuan awal

* selanjutnya L_t_corr dan B_corr ubah satuanya ke cd/m^2
* Jika input dalam **nL** → konversi ke  **cd·m⁻²** :
  `B_cd = nL_to_cd_m2(B_raw)` (di implementasi saya `1 nL = 1e-5/pi cd·m⁻²`).
* Jika area dalam **arcmin²** → konversi ke  **steradian** : `A_sr = arcmin2_to_sr(A_raw)`.

> Gunakan cd·m⁻² untuk semua B/Lt dalam rumus Crumey; A harus dalam sr.

---

## 5 — Sesuaikan area untuk magnifikasi (area efektif pada retina)

* `A_eff = A_sr * M**2` (magnification memetakan area sudut ke retina — gunakan ini pada fungsi Crumey jika Anda memodelkan efek retina).

> Alternatif: beberapa implementasi memasukkan magnifikasi hanya lewat `B` (melalui `F_m`) dan tetap memakai `A_sr` langsung. Pilih pendekatan konsisten dengan asumsi Anda; saya sarankan memakai `A_eff = A_sr * M**2` dan tetap terapkan `F_m` pada `B`.

---

## 6 — Hitung kontras aktual objek

* `C_obj = (L_t_cd - B_cd) / B_cd`
  (ini adalah kontras nyata yang diterima mata setelah koreksi optik)

---

## 7 — Hitung ambang Crumey

* Panggil fungsi Crumey: `C_th = crumey_threshold(A_eff, B_cd)`
  (fungsi menggabungkan R(B), C_inf(B) dan q(B) sesuai persamaan Crumey).

---

## 8 — Keputusan visibilitas

* 
* Standar: `visible = (C_obj > C_th)`
* Opsional konservatif: tambahkan faktor lapangan `F_obs >= 1` → `visible = (C_obj > F_obs * C_th)`.

* Jika   Cobj>Cth  \;C_{\text{obj}} > C_{\text{th}}\;**C**obj>**C**th → **terlihat** (terlampaui ambang).
* Jika   Cobj=Cth  \;C_{\text{obj}} = C_{\text{th}}\;**C**obj=**C**th**** → *marginal* (sangat sensitif ke noise/variabilitas pengamat).
* Jika   Cobj<Cth  \;C_{\text{obj}} < C_{\text{th}}\;**C**obj<**C**th → **tidak terlihat** menurut model.

---

## 9 — Validasi numerik & sanity checks

* Pastikan `B_cd > 0` dan `A_eff > 0` sebelum memanggil Crumey.
* Tampilkan intermediate values untuk debugging: `D_exit, F_p, F_a, F_m, L_t_cd, B_cd, A_eff, C_obj, C_th`.

---

## Tips praktis / pitfalls

* Magnification trade-off: `M ↑` → `A_eff ↑` (bantu visibilitas) **tetapi** `D_exit ↓` → `F_p ↓` (mengurangi illuminance). Cari `M` optimal.
* Jika Anda bekerja dari radiance spectral atau magnitudes, konversi spektral ke luminance memerlukan integrasi spektral + respons mata → gunakan `F_c` kalau data spektral terbatas.
* Untuk publikasi, sertakan sensitivity test: variasi `tau ±10%`, `D_eye ±1 mm`, `F_c ±20%` dan tunjukkan pengaruhnya pada keputusan.
* Tambahkan komentar kode yang jelas soal satuan setiap argumen agar pengguna tidak salah.
