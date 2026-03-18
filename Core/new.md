## Mengapa Aproksimasi i ≈ 180° − ∠e Tidak Eksak

Untuk memahami ini, bayangkan segitiga Matahari–Bumi–Bulan. Segitiga ini memiliki tiga sudut: elongasi ∠e (sudut di Bumi antara arah Matahari dan Bulan), sudut fase *i* (sudut di Bulan antara arah Matahari dan Bumi), dan sudut ψ (sudut di Matahari antara arah Bumi dan Bulan). Karena jumlah ketiga sudut dalam segitiga planar adalah 180°, kita mendapatkan hubungan **i = 180° − ∠e − ψ**, bukan i = 180° − ∠e.

Sudut ψ di Matahari memang kecil karena jarak Bumi–Bulan (~384.400 km) jauh lebih kecil dari jarak Bumi–Matahari (~149.600.000 km), sehingga rasionya sekitar 1/389. Untuk elongasi kecil (kondisi hilal), ψ berkisar sekitar 0,01°–0,03°. Ini menghasilkan perbedaan fraksi iluminasi sekitar 0,5% — kecil memang, tetapi dalam konteks model visibilitas hilal di mana kita berurusan dengan sabit yang sangat tipis di ambang visibilitas, setiap peningkatan akurasi memiliki makna. Lebih penting lagi, dengan menggunakan Skyfield Anda mendapatkan geometri 3D yang benar-benar riil tanpa asumsi planar, termasuk efek eksentrisitas orbit Bulan, inklinasi, dan librasi — semuanya otomatis terhitung.

## Derivasi Ulang dengan Phase Angle Dinamis

Rumus luas sabit dimulai dari definisi fraksi iluminasi (illuminated fraction) untuk bola sempurna. Jika *i* adalah sudut fase yang tepat (sudut di Bulan antara Matahari dan Bumi), maka fraksi permukaan cakram yang tersinari Matahari adalah **k = ½(1 + cos i)**. Ini memberikan k = 0 saat Bulan baru (i = 180°) dan k = 1 saat Bulan purnama (i = 0°), sesuai harapan.

Luas angular total cakram Bulan yang terlihat dari Bumi adalah πr², di mana *r* adalah semidiameter angular Bulan (yang juga berubah-ubah karena orbit Bulan eliptis). Maka **luas sabit tersinari** secara umum adalah:

**D = πr² × k = ½ π r² (1 + cos i)**

Dengan aproksimasi lama i ≈ 180° − ∠e, kita mendapatkan cos i ≈ cos(180° − ∠e) = −cos ∠e, sehingga D ≈ ½πr²(1 − cos ∠e) — ini adalah rumus yang ada di paper Binta Yunita. Dengan menghilangkan aproksimasi ini dan menggunakan *i* langsung dari Skyfield, rumus menjadi lebih tepat tanpa mengubah struktur fisika di belakangnya.

## Inti Perubahan: Dari Statis ke Dinamis

Perubahan yang terjadi sebenarnya sangat elegan secara matematis. Rumus lama Anda menghitung luas sabit melalui jalur tidak langsung: pertama menghitung elongasi (sudut di Bumi), lalu **mengasumsikan** phase angle = 180° − elongasi, baru menghitung fraksi iluminasi. Modul baru ini memotong jalur tersebut dan langsung menghitung phase angle dari posisi tiga benda langit dalam ruang tiga dimensi, menggunakan dot product vektor dari Bulan menuju Matahari dan dari Bulan menuju Bumi.

Secara rumus, yang berubah hanya satu langkah:

**Lama:** D = ½πr²(1 − cos ∠e), di mana cos ∠e adalah aproksimasi dari −cos(i)

**Baru:** D = ½πr²(1 + cos i), di mana i dihitung langsung dari geometri 3D Skyfield

Hasilnya, seluruh efek yang sebelumnya diabaikan — termasuk sudut paralaks di Matahari (~0,01°–0,03° untuk kondisi hilal), eksentrisitas orbit Bulan, dan geometri non-planar orbit — sekarang ikut terhitung secara otomatis tanpa perlu koreksi tambahan.
