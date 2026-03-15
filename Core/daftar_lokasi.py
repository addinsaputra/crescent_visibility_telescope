# =============================================================================
# DATA LOKASI PENGAMATAN HILAL
# =============================================================================
# Format: Nama Lokasi, Latitude, Longitude, Elevasi (mdpl), adm4_code (BMKG),
#         bias_t (°C), bias_rh (%)
# 
# Catatan:
# - Latitude positif = Utara, negatif = Selatan
# - Longitude positif = Timur, negatif = Barat
# - Elevasi dalam meter di atas permukaan laut (mdpl)
# - adm4_code: Kode wilayah BMKG tingkat kelurahan/desa (format: xx.xx.xx.xxxx)
#   Format: provinsi.kabkota.kecamatan.kelurahan
# - bias_t: Bias suhu ERA5 (°C), definisi: bias = ERA5 - Observasi
#   Koreksi: T_corrected = T_era5 - bias_t
# - bias_rh: Bias kelembapan relatif ERA5 (%), definisi: bias = ERA5 - Observasi
#   Koreksi: RH_corrected = RH_era5 - bias_rh
# - Nilai bias diperoleh dari artikel jurnal bereputasi tinggi
# - Lokasi tanpa data bias: bias_t=0, bias_rh=0 (tidak dikoreksi)
# =============================================================================

import io
import csv
    
# Data lokasi dalam format CSV string 
# Format: nama lokasi, latitude, longitude, elevasi, adm4_code, bias_t, bias_rh
DATA_LOKASI_CSV = """
Tower Hilal Sulamu_BMKG Kupang, -10.14333, 123.62667, 10.42, 53.01.07.2001, -1, -2
Tower Hilal Marana_BMKG Palu, -0.57861, 119.79070, 17.49, 72.03.10.2007, -4, 10
Tower Hilal Meras_MTC Manado_BMKG Manado, 1.48033, 124.83367, 15.14, 71.71.06.1005, -1, 4
Tower Hilal Ternate, -0.79983, 127.29483, 33.61, 82.71.01.1005, -1, 2
Tower Hilal Lhoong_BMKG Aceh Besar, 5.18367, 95.29850, 15.13, 11.06.01.2028, -1, 4
Tower Hilal Cikelet, -7.59367, 107.62350, 7, 32.05.02.2005, -1, 2
Pantai Lhoknga_chiek kuta_BMKG Aceh Besar, 5.46667, 95.24233, 11.65, 11.06.02.2001, -1, 4
POB Cibeas Pel. Ratu, -7.07400, 106.53133, 114, 32.02.02.2003, 0, -2
POB Condrodipo, -7.16967, 112.61733, 61, 35.25.14.2002, 0, -4
Rooftop Observatorium UIN WS, -6.99167, 110.34806, 89, 33.74.15.1010, -1, 2
Gedung BMKG NTT-Kupang, -10.15278, 123.60833, 40, 53.71.06.1007, -1, -2
Pantai Loang Baloq-MATARAM, -8.60408, 116.07440, 5, 52.71.04.1002, -1, 2
Hotel mina tanjung, -8.346986111, 116.149, 6, 52.08.01.2001, -1, 2
pantai lhok keutapang_aceh selatan, 3.26436111, 97.16788889, 7, 11.01.08.2001, 0, -6
Rooftop Stamet RHF_BMKG Tanjungpinang, 0.923611111, 104.5288889, 21, 21.72.02.1005, 2, -4
kantor stageof aceh selatan_BMKG Aceh Selatan, 3.134013889, 97.31178056, 10, 11.01.10.2011, 0, -6
kantor stageof lampung utara_BMKG Lampung Utara, 4.836136111, 104.87005, 33, 18.03.07.1007, -1, 6
Pantai Pondok Bali subang_BMKG Bandung, -6.206944444, 107.7761111, 3, 32.13.01.2001, 0, 0
dsunset hills_BMKG Gorontalo, 0.623888889, 123.0286111, 124, 75.71.01.1001, 0, 0
POB Syekh Bela-Belu, -7.73983, 110.35017, 45, 34.02.04.2005, 0, 0
POB Pedalen Kebumen_BMKG Banjarnegara, -7.731322222, 109.3908778, 9, 33.05.01.2001, 0, 0
Lapangan Tembak Desa Kebutuhjurang_BMKG Banjarnegara, -7.480125, 109.6779306, 496, 33.04.20.2005, 0, 0
kantor gubernur sumatera utara_BMKG Sumatera Utara, 3.580694444, 98.67148333, 28, 12.71.07.1001, 0, 0
Kantor Desa Jenggawur_BMKG Banjarnegara, -7.388730556, 109.6758056, 277, 33.04.11.2004, 0, 0
Pantai Anyer_BMKG Serang, -6.67033, 105.88500, 5, 36.02.19.2001, 0, 0
Pantai Ngliyep Malang_BMKG Malang, -8.35000, 112.43333, 10, 35.07.15.2001, 0, 0
"""


def get_list_lokasi():
    """
    Mengambil daftar lokasi pengamatan sebagai list of dictionaries.
    
    Returns:
    --------
    list[dict]
        List berisi dictionary dengan keys: nama, lat, lon, elevasi, adm4_code,
        bias_t, bias_rh
        Contoh:
        [
            {"nama": "UIN WS", "lat": -6.99, "lon": 110.34, "elevasi": 89,
             "adm4_code": "33.74.10.1003", "bias_t": -1.0, "bias_rh": 2.0},
            ...
        ]
    """
    f = io.StringIO(DATA_LOKASI_CSV.strip())
    reader = csv.reader(f, skipinitialspace=True)
    
    list_lokasi = []
    for row in reader:
        if len(row) >= 7:
            # Format lengkap: nama, lat, lon, elevasi, adm4_code, bias_t, bias_rh
            data = {
                "nama": row[0].strip(),
                "lat": float(row[1]),
                "lon": float(row[2]),
                "elevasi": float(row[3]),
                "adm4_code": row[4].strip(),
                "bias_t": float(row[5]),
                "bias_rh": float(row[6])
            }
            list_lokasi.append(data)
        elif len(row) >= 5:
            # Backward compatibility: tanpa bias data
            data = {
                "nama": row[0].strip(),
                "lat": float(row[1]),
                "lon": float(row[2]),
                "elevasi": float(row[3]),
                "adm4_code": row[4].strip(),
                "bias_t": 0.0,
                "bias_rh": 0.0
            }
            list_lokasi.append(data)
        elif len(row) >= 4:
            # Backward compatibility: tanpa adm4_code dan bias
            data = {
                "nama": row[0].strip(),
                "lat": float(row[1]),
                "lon": float(row[2]),
                "elevasi": float(row[3]),
                "adm4_code": "",
                "bias_t": 0.0,
                "bias_rh": 0.0
            }
            list_lokasi.append(data)
    
    return list_lokasi


def get_lokasi_by_index(index: int):
    """
    Mengambil lokasi berdasarkan index (1-indexed untuk user-friendly).
    
    Parameters:
    -----------
    index : int
        Index lokasi (dimulai dari 1)
        
    Returns:
    --------
    dict or None
        Dictionary lokasi atau None jika index tidak valid
    """
    list_lokasi = get_list_lokasi()
    if 1 <= index <= len(list_lokasi):
        return list_lokasi[index - 1]
    return None


def get_lokasi_by_name(nama: str):
    """
    Mencari lokasi berdasarkan nama (partial match, case-insensitive).
    
    Parameters:
    -----------
    nama : str
        Nama lokasi yang dicari
        
    Returns:
    --------
    dict or None
        Dictionary lokasi pertama yang cocok atau None jika tidak ditemukan
    """
    list_lokasi = get_list_lokasi()
    nama_lower = nama.lower()
    
    for loc in list_lokasi:
        if nama_lower in loc["nama"].lower():
            return loc
    return None


def print_daftar_lokasi():
    """
    Menampilkan daftar lokasi dalam format tabel yang rapi.
    """
    list_lokasi = get_list_lokasi()
    
    print("\n" + "=" * 80)
    print("DAFTAR LOKASI PENGAMATAN HILAL")
    print("=" * 80)
    print(f"{'NO':<4} | {'NAMA LOKASI':<42} | {'LAT':<10} | {'LON':<10} | {'ELV':<5}")
    print("-" * 80)
    
    for i, data in enumerate(list_lokasi, 1):
        print(f"{i:<4} | {data['nama']:<42} | {data['lat']:<10.5f} | {data['lon']:<10.5f} | {data['elevasi']}")
    
    print("=" * 80)
    print(f"Total: {len(list_lokasi)} lokasi")
    return list_lokasi


def pilih_lokasi_interaktif():
    """
    Menampilkan menu interaktif untuk memilih lokasi.
    
    Returns:
    --------
    dict or None
        Dictionary lokasi yang dipilih atau None jika dibatalkan
    """
    list_lokasi = print_daftar_lokasi()
    
    print("\nMasukkan nomor lokasi (1-{}) atau 0 untuk input manual:".format(len(list_lokasi)))
    
    try:
        pilihan = int(input("Pilihan Anda: "))
        
        if pilihan == 0:
            # Input manual
            print("\n--- INPUT LOKASI MANUAL ---")
            nama = input("Nama lokasi: ")
            lat = float(input("Latitude (contoh: -6.9167): "))
            lon = float(input("Longitude (contoh: 110.3480): "))
            elv = int(input("Elevasi (meter): "))
            
            return {
                "nama": nama,
                "lat": lat,
                "lon": lon,
                "elevasi": elv
            }
        
        elif 1 <= pilihan <= len(list_lokasi):
            lokasi = list_lokasi[pilihan - 1]
            print(f"\n✓ Lokasi dipilih: {lokasi['nama']}")
            return lokasi
        
        else:
            print("[!] Nomor tidak valid!")
            return None
            
    except ValueError:
        print("[!] Input harus berupa angka!")
        return None


# --- Testing jika dijalankan langsung ---
if __name__ == "__main__":
    # Test: tampilkan daftar
    print_daftar_lokasi()
    
    # Test: ambil by index
    print("\n--- Test get by index ---")
    lok = get_lokasi_by_index(1)
    print(f"Index 1: {lok}")
    
    # Test: cari by name
    print("\n--- Test get by name ---")
    lok = get_lokasi_by_name("UIN")
    print(f"Cari 'UIN': {lok}")