# Project BNSP Data Analyst: Seduh Nusantara 2025

Studi kasus: kedai kopi fiktif "Seduh Nusantara", 6 outlet Jabodetabek, 1 Jan–31 Des 2025.
Pertanyaan utama: **penjualan tumbuh, tetapi di mana laba bocor?**
Semua data adalah **simulasi**. Pola promo, channel, dan member dirancang saat data dibuat, jadi project ini menunjukkan cara analisis, bukan fakta pasar.

## 1. Isi paket file

| File | Fungsi |
|---|---|
| `scripts/01_generate_data.py` | Membuat data simulasi (raw_sales.csv sengaja kotor) |
| `scripts/02_clean_data.py` | Membersihkan data, membuat `clean_sales.csv`, `data_quality_log.csv`, `seduh.db` |
| `scripts/03_analysis.py` | Analisis dan ekspor `metrics.json` |
| `scripts/04_verify_sql.py` | Menjalankan 10 query SQL dan membandingkannya dengan pandas |
| `scripts/05_profile_dictionary.py` | Membuat profil data, kamus data, dan ringkasan statistik deskriptif |
| `sql/analysis_queries.sql` | 10 query SQL (SQLite) |
| `data/clean_sales.csv` | Data bersih untuk Looker Studio atau Power BI |
| `data/raw_sales.csv` | Data mentah (bukti proses cleaning) |
| `data/master_outlet.csv`, `master_produk.csv` | Tabel master |
| `data/data_quality_log.csv` | Catatan 25 langkah cleaning |
| `data/metrics.json` | Semua angka yang dipakai di deck |
| `notebook_seduh_nusantara.ipynb` | Seluruh alur (01–05) dalam satu notebook, lengkap dengan penjelasan dan grafik |
| `data/data_profile.csv` | Profil tiap kolom (tipe, nilai kosong, nilai unik) sebelum dan sesudah cleaning |
| `data/data_dictionary.csv` | Kamus data: 32 kolom di 3 tabel, arti, tipe, asal kolom, aturan |
| `data/data_summary.json` | Ringkasan profil dan statistik deskriptif |

Urutan menjalankan ulang: `01` → `02` → `03` → `04` → `05` (butuh `pandas numpy`). Seed tetap, jadi hasilnya selalu sama.

## 2. Kolom tabel `clean_sales.csv`

Satu baris = satu item dalam satu order.
`order_id, order_datetime, outlet_id, outlet, channel, customer_id, product_id, product, category, qty, unit_price, discount_amount, promo_name, gross_sales, net_sales, cogs, delivery_commission, gross_profit, is_member, tanggal, bulan, jam, hari, is_promo`

Definisi KPI:
- Net sales = qty × harga − diskon
- Gross profit = net sales − HPP (cogs) − komisi delivery (20% dari net sales delivery)
- Margin = gross profit ÷ net sales
- Nilai order (AOV) = net sales ÷ order unik (jangan `COUNT(*)`, karena satu order punya banyak baris)

## 3. Angka kunci (harus sama di semua tool)

| KPI | Nilai |
|---|---|
| Baris data mentah → bersih | 108.521 → 108.338 (183 dibuang) |
| Net sales | Rp2.664.750.400 |
| Gross profit | Rp1.577.622.040 |
| Margin | 59,2% |
| Order unik | 54.428 |
| Nilai order (AOV) | Rp48.959 |
| Total diskon | Rp56.459.600 (Gajian Rp40.813.200 + Kopi Susu Juni Rp15.646.400; Gajian tidak dianalisis tersendiri) |
| Margin Dine-in / Takeaway / Delivery | 64,6% / 65,2% / 45,0% |
| Porsi order Delivery | 29,0% (23,0% Jan → 35,0% Des) |
| Komisi delivery 2025 | Rp151.338.060 |
| Pertumbuhan H2 vs H1 | Net sales +28,8%, gross profit +26,6% |
| Margin H1 → H2 | 59,8% → 58,8% (Jan 60,6%, Des 58,3%) |
| Kontribusi Delivery | 28,4% net sales, tetapi hanya 21,6% gross profit (Query 7) |
| Kopi Susu, Mei → Juni | unit 1.756 → 2.032 (+15,7%); gross profit Rp22,9 jt → Rp12,2 jt (−46,6%, hilang Rp10,7 jt); laba per unit Rp13.038 → Rp6.015; diskon Juni Rp15,6 jt |
| Rekomendasi harga delivery +5% | tambahan laba ±Rp30,3 jt/tahun; tetap untung selama order delivery turun < 8,2% |
| Food attach *(analisis tambahan, tidak di deck)* | 33,8%; nilai order Rp66.219 (dengan makanan) vs Rp40.156 (tanpa) |
| Member kembali ≤ 60 hari *(analisis tambahan, tidak di deck)* | 79,9% (1.785 member eligible); kohort H1 80,8% vs H2 77,5% |

Kalau angka di dashboard Looker Studio atau Power BI tidak sama, cek: (1) tipe kolom, (2) apakah memakai `COUNT_DISTINCT(order_id)`, (3) apakah ada filter tanggal yang menyala.

Tabel di atas menjadi acuan: jika hasil rumus Looker Studio atau DAX di bawah berbeda, yang diperbaiki adalah rumusnya, bukan angkanya.

## 4. Looker Studio

**Memuat data.** Buka Looker Studio → Create → Data source → **File Upload** → pilih `clean_sales.csv` (batas ukuran file 100 MB; file ini sekitar 20 MB). Alternatif: unggah ke Google Sheets lalu hubungkan.

**Tipe kolom** (di editor data source):
- `order_datetime`: Date Hour; `tanggal`: Date (YYYY-MM-DD)
- `net_sales, gross_profit, discount_amount, delivery_commission, cogs, gross_sales`: Number, aggregation Sum (format Currency IDR)
- `order_id, customer_id`: Text; `bulan`: Text (urut alfabet = urut waktu)

**Calculated fields** (Add a field):

| Nama | Rumus |
|---|---|
| Margin | `SUM(gross_profit) / SUM(net_sales)` |
| Orders | `COUNT_DISTINCT(order_id)` |
| AOV | `SUM(net_sales) / COUNT_DISTINCT(order_id)` |
| Share Delivery | `COUNT_DISTINCT(CASE WHEN channel = "Delivery" THEN order_id END) / COUNT_DISTINCT(order_id)` |
| Food Attach | `COUNT_DISTINCT(CASE WHEN category = "Makanan" THEN order_id END) / COUNT_DISTINCT(order_id)` |
| Member | `COUNT_DISTINCT(CASE WHEN is_member = 1 THEN customer_id END)` |

**Tata letak (3 halaman):**
1. *Ringkasan*: 6 scorecard (Net sales, Gross profit, Margin, Orders, AOV, total diskon), bar chart net sales per `bulan`, tabel outlet (net sales, margin). Kontrol: date range, dropdown `outlet`, dropdown `channel`.
2. *Channel dan promo*: tabel channel (Orders, Share, AOV, Margin), tabel `promo_name` (diskon, net sales, margin), bar chart gross profit Kopi Susu per bulan (filter `product = Kopi Susu Gula Aren`).
3. *Produk dan member*: tabel `category`, scorecard Food Attach, scorecard Member.

Tips: beri judul tiap grafik berupa kalimat temuan ("Delivery menggerus margin"), bukan nama tabel. Pakai 1 warna utama dan 1 warna peringatan (merah) untuk margin yang rendah.

**Berbagi:** Share → Manage access, atau Get report link. Pastikan tautan bisa dibuka tanpa login.

## 5. Power BI Desktop

**Memuat data.** Get data → Text/CSV → `clean_sales.csv` (nama tabel `sales`), `master_outlet.csv`, `master_produk.csv`. Di Power Query: `order_datetime` → Date/Time, `tanggal` → Date, kolom uang → Whole number.

**Tabel kalender** (Modeling → New table):
```
Calendar = CALENDAR(DATE(2025,1,1), DATE(2025,12,31))
```
Tambahkan kolom `Bulan = FORMAT([Date], "yyyy-mm")`. Hubungkan `Calendar[Date]` ke `sales[tanggal]` (many-to-one). Hubungkan `outlet_id` dan `product_id` ke tabel master.

**Measures** (Modeling → New measure):
```
Net Sales    = SUM(sales[net_sales])
Gross Profit = SUM(sales[gross_profit])
Margin %     = DIVIDE([Gross Profit], [Net Sales])
Orders       = DISTINCTCOUNT(sales[order_id])
AOV          = DIVIDE([Net Sales], [Orders])
Delivery Share = DIVIDE(CALCULATE([Orders], sales[channel] = "Delivery"), [Orders])
Food Attach  = DIVIDE(CALCULATE([Orders], sales[category] = "Makanan"), [Orders])
Net Sales H1 = CALCULATE([Net Sales], Calendar[Date] < DATE(2025,7,1))
Net Sales H2 = CALCULATE([Net Sales], Calendar[Date] >= DATE(2025,7,1))
Growth H2 vs H1 = DIVIDE([Net Sales H2], [Net Sales H1]) - 1
Members      = CALCULATE(DISTINCTCOUNT(sales[customer_id]), sales[is_member] = 1)
```
Retensi 60 hari dihitung di SQL (Query 10), bukan di DAX; cukup tampilkan sebagai angka dari analisis.

**Visual (3 halaman, sama seperti Looker Studio):** kartu KPI; clustered column `Calendar[Bulan]` × `Net Sales`; tabel outlet (Net Sales, Margin %, Growth H2 vs H1); tabel channel; slicer `outlet`, `channel`, `Calendar[Date]`. Aktifkan conditional formatting merah untuk Margin % di bawah 50%.

**Berbagi:** simpan `.pbix`; ekspor PDF dari File → Export jika perlu lampiran.
