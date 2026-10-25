#!/usr/bin/env python3
"""
05_profile_dictionary.py
Unit kompetensi: Menelaah Data, Menentukan Objek dan Label Data.

Keluaran (folder data/):
  data_profile.csv     profil tiap kolom data mentah dan data bersih
                       (tipe, nilai kosong, nilai unik, contoh nilai)
  data_dictionary.csv  kamus data: tabel, kolom, arti, tipe, asal (asli/turunan), aturan
  data_summary.json    ringkasan angka profil yang dipakai di deck

Jalankan: python scripts/05_profile_dictionary.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

raw = pd.read_csv(DATA / "raw_sales.csv", dtype=str, keep_default_na=True)
clean = pd.read_csv(DATA / "clean_sales.csv")

# ---------------------------------------------------------------- profil kolom
rows = []
for name, df in (("mentah", raw), ("bersih", clean)):
    for c in df.columns:
        s = df[c]
        rows.append({
            "data": name,
            "kolom": c,
            "tipe_terbaca": str(s.dtype),
            "baris": len(s),
            "kosong": int(s.isna().sum()),
            "persen_kosong": round(s.isna().mean() * 100, 2),
            "nilai_unik": int(s.nunique()),
            "contoh": " | ".join(map(str, s.dropna().astype(str).unique()[:3])),
        })
profile = pd.DataFrame(rows)
profile.to_csv(DATA / "data_profile.csv", index=False)

# ---------------------------------------------------------------- ringkasan
o = clean.groupby("order_id")["net_sales"].sum()
summary = {
    "mentah": {
        "baris": int(len(raw)),
        "kolom": int(raw.shape[1]),
        "duplikat_persis": int(raw.duplicated().sum()),
        "kolom_dengan_kosong": {c: int(raw[c].isna().sum()) for c in raw.columns if raw[c].isna().any()},
    },
    "bersih": {
        "baris": int(len(clean)),
        "kolom": int(clean.shape[1]),
        "order_unik": int(clean["order_id"].nunique()),
        "outlet": int(clean["outlet"].nunique()),
        "produk": int(clean["product_id"].nunique()),
        "member": int(clean.loc[clean["is_member"] == 1, "customer_id"].nunique()),
        "tanggal_awal": clean["tanggal"].min(),
        "tanggal_akhir": clean["tanggal"].max(),
        "nilai_kosong_total": int(clean.isna().sum().sum()),
    },
    # statistik deskriptif nilai per order (net sales per order)
    "nilai_order": {
        "rata_rata": float(o.mean()),
        "median": float(o.median()),
        "std": float(o.std()),
        "min": float(o.min()),
        "p25": float(o.quantile(0.25)),
        "p75": float(o.quantile(0.75)),
        "maks": float(o.max()),
    },
}
with open(DATA / "data_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

# ---------------------------------------------------------------- kamus data
S, G, T, M = "mentah", "gabungan", "turunan", "master"
D = [
    # tabel sales (clean_sales.csv), satu baris = satu item dalam satu order
    ("sales", "order_id", "Nomor order. Satu order bisa punya banyak baris item", "teks", S, "Kunci order. Hitung order dengan COUNT DISTINCT"),
    ("sales", "order_datetime", "Waktu order dibuat", "tanggal-waktu", S, "Hanya tahun 2025; format yyyy-mm-dd hh:mm:ss"),
    ("sales", "outlet_id", "Kode outlet (SN01-SN06)", "teks", G, "Kunci penghubung ke master_outlet"),
    ("sales", "outlet", "Nama outlet", "teks", S, "Diseragamkan ke nama di master_outlet"),
    ("sales", "channel", "Cara pelanggan memesan", "kategori", S, "Dine-in, Takeaway, atau Delivery"),
    ("sales", "customer_id", "ID pelanggan; WALKIN jika bukan member", "teks", S, "Member berawalan M"),
    ("sales", "product_id", "Kode produk (P01-P15)", "teks", S, "Kunci penghubung ke master_produk"),
    ("sales", "product", "Nama produk", "teks", S, "Diambil dari master_produk"),
    ("sales", "category", "Kelompok produk", "kategori", G, "Kopi, Non-Kopi, atau Makanan"),
    ("sales", "qty", "Jumlah unit produk pada baris itu", "bilangan bulat", S, "Harus > 0; di atas 10 dianggap salah input"),
    ("sales", "unit_price", "Harga satuan (Rp)", "bilangan bulat", S, "Sama dengan harga di master_produk"),
    ("sales", "discount_amount", "Total diskon pada baris itu (Rp)", "bilangan bulat", S, "0 jika tanpa promo"),
    ("sales", "promo_name", "Nama promo", "kategori", S, "Diskon Gajian, Promo Kopi Susu Juni, atau Tanpa Promo"),
    ("sales", "is_member", "Penanda member", "label 1/0", S, "1 = member, 0 = bukan. Diseragamkan dari Ya/Y/member/Tidak/N"),
    ("sales", "gross_sales", "Penjualan sebelum diskon", "bilangan bulat", T, "qty x unit_price"),
    ("sales", "net_sales", "Penjualan setelah diskon", "bilangan bulat", T, "gross_sales - discount_amount"),
    ("sales", "cogs", "Harga pokok penjualan (HPP)", "bilangan bulat", T, "qty x cogs_per_unit dari master_produk"),
    ("sales", "delivery_commission", "Komisi platform delivery", "bilangan bulat", T, "20% dari net_sales jika channel Delivery, selain itu 0"),
    ("sales", "gross_profit", "Laba kotor", "bilangan bulat", T, "net_sales - cogs - delivery_commission"),
    ("sales", "tanggal", "Tanggal order", "teks", T, "Dari order_datetime, format yyyy-mm-dd"),
    ("sales", "bulan", "Bulan order", "teks", T, "Format yyyy-mm; urut alfabet = urut waktu"),
    ("sales", "jam", "Jam order (7-22)", "bilangan bulat", T, "Dari order_datetime"),
    ("sales", "hari", "Nama hari", "kategori", T, "Senin sampai Minggu"),
    ("sales", "is_promo", "Penanda ada promo", "label 1/0", T, "1 jika promo_name bukan Tanpa Promo"),
    # master
    ("master_outlet", "outlet_id", "Kode outlet", "teks", M, "Kunci utama"),
    ("master_outlet", "outlet", "Nama outlet", "teks", M, "Nama baku"),
    ("master_outlet", "kota", "Kota lokasi outlet", "teks", M, "Jabodetabek"),
    ("master_produk", "product_id", "Kode produk", "teks", M, "Kunci utama"),
    ("master_produk", "product", "Nama produk", "teks", M, "Nama baku"),
    ("master_produk", "category", "Kelompok produk", "kategori", M, "Kopi, Non-Kopi, atau Makanan"),
    ("master_produk", "price", "Harga jual (Rp)", "bilangan bulat", M, "Harga acuan"),
    ("master_produk", "cogs_per_unit", "HPP per unit (Rp)", "bilangan bulat", M, "Dipakai menghitung cogs"),
]
dd = pd.DataFrame(D, columns=["tabel", "kolom", "arti", "tipe", "asal", "aturan"])

# pastikan kamus mencakup semua kolom nyata, dan tidak ada kolom hantu
missing = set(clean.columns) - set(dd.loc[dd["tabel"] == "sales", "kolom"])
extra = set(dd.loc[dd["tabel"] == "sales", "kolom"]) - set(clean.columns)
assert not missing and not extra, f"Kamus tidak cocok: kurang {missing}, lebih {extra}"
dd.to_csv(DATA / "data_dictionary.csv", index=False)

print(json.dumps(summary, ensure_ascii=False, indent=2))
print(f"\nKamus data: {len(dd)} kolom ({(dd['asal'] == T).sum()} turunan). Cocok dengan clean_sales.csv.")
