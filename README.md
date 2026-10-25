# Analisis Penjualan Seduh Nusantara 2025

**Di mana laba bocor, dan apa yang bisa diperbaiki?**

Proyek analisis data end-to-end untuk jaringan kedai kopi fiktif *Seduh Nusantara* (6 outlet di Jabodetabek, 1 Januari – 31 Desember 2025): dari data mentah yang kotor, pembersihan dan validasi, analisis dengan Python dan SQL, sampai dashboard dan rekomendasi bisnis. Disusun sebagai proyek Sertifikasi BNSP Skema Data Analyst (SKKNI No. 299 Tahun 2020).

> **Catatan:** seluruh data adalah **data simulasi**. Pola promo, channel, dan perilaku member dirancang saat data dibuat, jadi proyek ini menunjukkan *cara* menganalisis, bukan fakta pasar.

📊 **Dashboard Looker Studio:** [lihat dashboard](https://datastudio.google.com/u/0/reporting/0f9eafb5-d0da-415b-a3a9-4faf974852eb/page/nnzBG)

## Ringkasan

Sepanjang 2025, penjualan naik tetapi margin justru turun.

| KPI 2025 | Nilai |
|---|---|
| Penjualan bersih | Rp2,66 miliar |
| Laba kotor | Rp1,58 miliar |
| Margin laba kotor | 59,2% |
| Jumlah pesanan | 54.428 |
| Rata-rata per pesanan | Rp48.959 |

Penjualan semester 2 tumbuh **28,8%** dibanding semester 1, tetapi margin turun dari **60,6%** (Januari) menjadi **58,3%** (Desember).

## Temuan

**1. Delivery menggerus margin.**
Margin delivery hanya **45,0%**, jauh di bawah dine-in (64,6%) dan takeaway (65,2%), karena komisi aplikasi 20%. Porsi pesanan delivery naik dari 23% menjadi 35% sepanjang tahun. Delivery menyumbang 28,4% penjualan, tetapi hanya 21,6% laba kotor.

**2. Promo menambah volume, bukan laba.**
Saat promo Kopi Susu Gula Aren (diskon 35%) di bulan Juni, unit terjual naik **15,7%**, tetapi laba kotornya turun **46,6%**: dari Rp22,9 juta (Mei) menjadi Rp12,2 juta (Juni). Laba per unit turun dari Rp13.038 menjadi Rp6.015.

## Rekomendasi

| Rekomendasi | Perkiraan dampak |
|---|---|
| **Atur harga delivery:** naikkan harga menu di aplikasi delivery 5% untuk menutup komisi | Tambahan laba ±Rp30,3 juta per tahun; tetap untung selama pesanan delivery turun kurang dari 8,2% |
| **Batasi diskon besar:** hindari diskon 35% pada satu produk, ganti dengan paket (bundle) yang menjaga laba per unit | Mencegah hilangnya laba ±Rp10,7 juta per promo serupa |

Perkiraan dampak memakai asumsi sederhana (misalnya volume tetap) dan perlu diuji, bukan janji.

## Alur kerja

```
01_generate_data  →  02_clean_data  →  03_analysis  →  04_verify_sql  →  05_profile_dictionary
  data mentah         data bersih        metrics.json     10 query SQL       profil & kamus data
  (sengaja kotor)     + log 25 langkah                    cocok dgn pandas
```

1. **Mengumpulkan data:** membuat data transaksi simulasi, lalu sengaja disuntik masalah realistis (duplikat, format harga "Rp22.000", tanggal campur, penulisan channel tidak seragam, tahun salah, qty tidak valid).
2. **Membersihkan & memvalidasi:** 108.521 baris mentah → 108.338 baris bersih. Nilai yang bisa dipastikan diperbaiki; hanya 183 baris yang nilainya tidak bisa dipastikan yang dibuang. Setiap langkah tercatat di `data_quality_log.csv`.
3. **Menganalisis:** KPI, tren bulanan, outlet, channel, promo, produk, dan member dengan pandas.
4. **Verifikasi silang:** 10 query SQL (SQLite) menghasilkan angka yang sama dengan pandas (107 angka dibandingkan otomatis).
5. **Menyajikan:** dashboard Looker Studio dan deck presentasi.

## Struktur repository

```
├── notebook_seduh_nusantara.ipynb   # seluruh alur dalam satu notebook, dengan penjelasan & grafik
├── scripts/                         # alur yang sama sebagai skrip terpisah (01 → 05)
├── sql/analysis_queries.sql         # 10 query analisis (SQLite)
├── data/
│   ├── raw_sales.csv                # data mentah (sengaja kotor)
│   ├── clean_sales.csv              # data bersih (sumber dashboard)
│   ├── master_outlet.csv, master_produk.csv
│   ├── seduh.db                     # database SQLite
│   ├── data_quality_log.csv         # log 25 langkah cleaning
│   ├── data_profile.csv, data_summary.json, data_dictionary.csv
│   └── metrics.json                 # semua angka hasil analisis
└── PANDUAN_PROJECT_BNSP.md          # dokumentasi detail: kolom, angka kunci, panduan dashboard
```

## Cara menjalankan

Butuh Python 3.10+.

```bash
pip install -r requirements.txt

python scripts/01_generate_data.py
python scripts/02_clean_data.py
python scripts/03_analysis.py
python scripts/04_verify_sql.py
python scripts/05_profile_dictionary.py
```

Atau buka `notebook_seduh_nusantara.ipynb` lalu jalankan semua sel. Seed acak dibuat tetap, jadi hasilnya selalu sama.

## Alat

Python (pandas, NumPy, Matplotlib) · SQL (SQLite) · Jupyter Notebook · Looker Studio

---

Disusun oleh **Muhammad Razi Al Kindi Nadra**
