#!/usr/bin/env python3
"""
02_clean_data.py
Membersihkan data/raw_sales.csv menjadi:
  data/clean_sales.csv        data bersih untuk Looker Studio / Power BI
  data/data_quality_log.csv   catatan setiap perbaikan (apa, berapa baris, tindakan)
  data/seduh.db               SQLite: tabel sales, master_outlet, master_produk

Aturan: baris DIPERBAIKI jika nilai yang benar bisa dipastikan dari data lain,
baris DIBUANG jika tidak bisa dipastikan.

Jalankan: python scripts/02_clean_data.py
"""
import re
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
COMMISSION = 0.20
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

master_outlet = pd.read_csv(DATA / "master_outlet.csv")
master_produk = pd.read_csv(DATA / "master_produk.csv")

log = []


def add(step, issue, rows, action):
    log.append({"langkah": step, "masalah": issue, "baris_terdampak": int(rows), "tindakan": action})


df = pd.read_csv(DATA / "raw_sales.csv", dtype=str, keep_default_na=True)
n_raw = len(df)
add(1, "Jumlah baris data mentah", n_raw, "Titik awal")

# ---- 1. Duplikat persis -----------------------------------------------------
dup = df.duplicated().sum()
df = df.drop_duplicates().reset_index(drop=True)
add(2, "Baris duplikat persis (ekspor ganda)", dup, "Dibuang, sisakan satu")

# ---- 2. Spasi berlebih ------------------------------------------------------
str_cols = ["outlet", "channel", "product", "product_id", "customer_id", "promo_name", "is_member"]
changed = 0
for c in str_cols:
    before = df[c].copy()
    df[c] = df[c].str.strip().str.replace(r"\s+", " ", regex=True)
    changed += int((before.notna() & (before != df[c])).sum())
add(3, "Spasi di awal/akhir/ganda pada kolom teks", changed, "Dirapikan (strip)")

# ---- 3. Outlet: samakan penulisan, isi yang kosong dari order yang sama ------
name_map = {n.lower(): n for n in master_outlet["outlet"]}
norm = df["outlet"].str.lower()
fixed_case = int((df["outlet"].notna() & (df["outlet"] != norm.map(name_map))).sum())
df["outlet"] = norm.map(name_map)
add(4, "Nama outlet beda huruf besar/kecil", fixed_case, "Diseragamkan ke nama di master_outlet")

miss_outlet = int(df["outlet"].isna().sum())
fill = df.groupby("order_id")["outlet"].transform(lambda s: s.dropna().iloc[0] if s.notna().any() else np.nan)
df["outlet"] = df["outlet"].fillna(fill)
recovered = miss_outlet - int(df["outlet"].isna().sum())
add(5, "Outlet kosong", miss_outlet, f"{recovered} dipulihkan dari baris lain di order yang sama")
still = int(df["outlet"].isna().sum())
if still:
    df = df[df["outlet"].notna()].reset_index(drop=True)
add(6, "Outlet kosong dan tidak bisa dipulihkan", still, "Dibuang")

# ---- 4. Channel ---------------------------------------------------------------
def std_channel(v):
    key = re.sub(r"[^a-z]", "", str(v).lower())
    return {"dinein": "Dine-in", "takeaway": "Takeaway", "delivery": "Delivery"}.get(key, np.nan)


ch = df["channel"].map(std_channel)
add(7, "Penulisan channel tidak seragam", int((ch != df["channel"]).sum()), "Diseragamkan: Dine-in / Takeaway / Delivery")
df["channel"] = ch
bad_channel = int(df["channel"].isna().sum())
df = df[df["channel"].notna()].reset_index(drop=True)
add(8, "Channel tidak dikenali", bad_channel, "Dibuang")

# ---- 5. Tanggal --------------------------------------------------------------
slash = df["order_datetime"].str.contains("/", na=False)
dt = pd.to_datetime(df["order_datetime"].where(~slash), format="%Y-%m-%d %H:%M:%S", errors="coerce")
dt_slash = pd.to_datetime(df["order_datetime"].where(slash), format="%d/%m/%Y %H:%M", errors="coerce")
df["order_datetime"] = dt.fillna(dt_slash)
add(9, "Format tanggal dd/mm/yyyy", int(slash.sum()), "Diubah ke format yyyy-mm-dd hh:mm:ss")
bad_date = int(df["order_datetime"].isna().sum())
df = df[df["order_datetime"].notna()].reset_index(drop=True)
add(10, "Tanggal tidak terbaca", bad_date, "Dibuang")
out_year = int((df["order_datetime"].dt.year != 2025).sum())
df = df[df["order_datetime"].dt.year == 2025].reset_index(drop=True)
add(11, "Tanggal di luar tahun 2025 (tertulis 2026)", out_year,
    "Dibuang: tahun yang benar tidak bisa dipastikan, jumlah sangat kecil")

# ---- 6. Produk -----------------------------------------------------------------
name_to_id = dict(zip(master_produk["product"].str.lower(), master_produk["product_id"]))
miss_pid = int(df["product_id"].isna().sum())
df["product_id"] = df["product_id"].fillna(df["product"].str.lower().map(name_to_id))
still_pid = int(df["product_id"].isna().sum())
add(12, "product_id kosong", miss_pid, f"{miss_pid - still_pid} dipulihkan dari nama produk")
df = df[df["product_id"].notna()].reset_index(drop=True)
add(13, "product_id kosong dan tidak bisa dipulihkan", still_pid, "Dibuang")
df = df.drop(columns=["product"]).merge(
    master_produk[["product_id", "product", "category", "cogs_per_unit", "price"]], on="product_id", how="left"
)

# ---- 7. Harga ------------------------------------------------------------------
as_text = df["unit_price"].str.contains("Rp", na=False)
df["unit_price"] = df["unit_price"].str.replace(r"[^0-9]", "", regex=True).astype(int)
add(14, 'Harga tertulis sebagai teks, mis. "Rp22.000"', int(as_text.sum()), "Diubah menjadi angka")
price_mismatch = int((df["unit_price"] != df["price"]).sum())
add(15, "Harga baris berbeda dari harga master", price_mismatch, "Tidak ada yang perlu diperbaiki" if price_mismatch == 0 else "Perlu ditinjau")

# ---- 8. Qty -----------------------------------------------------------------------
df["qty"] = pd.to_numeric(df["qty"], errors="coerce")
bad_qty = int((df["qty"].isna() | (df["qty"] <= 0)).sum())
df = df[df["qty"] > 0].reset_index(drop=True)
add(16, "Qty nol atau negatif", bad_qty, "Dibuang (bukan transaksi penjualan yang valid)")
out_qty = int((df["qty"] > 10).sum())
df = df[df["qty"] <= 10].reset_index(drop=True)
add(17, "Qty outlier (> 10 unit per item, normalnya 1-3)", out_qty, "Dibuang sebagai salah input")
df["qty"] = df["qty"].astype(int)

# ---- 9. Diskon dan promo -----------------------------------------------------------
df["promo_name"] = df["promo_name"].fillna("")
miss_disc = int(df["discount_amount"].isna().sum())
df["discount_amount"] = pd.to_numeric(df["discount_amount"], errors="coerce")
no_promo = df["promo_name"] == ""
df.loc[df["discount_amount"].isna() & no_promo, "discount_amount"] = 0
unfixable = int(df["discount_amount"].isna().sum())
df = df[df["discount_amount"].notna()].reset_index(drop=True)
df["discount_amount"] = df["discount_amount"].astype(int)
add(18, "discount_amount kosong pada baris tanpa promo", miss_disc - unfixable, "Diisi 0")
add(19, "discount_amount kosong pada baris yang berpromo", unfixable, "Dibuang")
blank_promo = int((df["promo_name"] == "").sum())
df["promo_name"] = df["promo_name"].replace("", "Tanpa Promo")
add(20, "promo_name kosong (tidak ada promo)", blank_promo, 'Diisi "Tanpa Promo"')

# ---- 10. Customer dan member -----------------------------------------------------------
member_flag = df["is_member"].str.lower().map(
    {"ya": 1, "y": 1, "1": 1, "member": 1, "tidak": 0, "n": 0, "0": 0, "non-member": 0}
)
add(21, "Penulisan is_member tidak seragam (Ya/Y/member/Tidak/N ...)",
    int((~df["is_member"].isin(["1", "0"])).sum()), "Diseragamkan menjadi 1 / 0")
df["is_member"] = member_flag.astype(int)
blank_cust = int(df["customer_id"].isna().sum())
df["customer_id"] = df["customer_id"].fillna("WALKIN")
add(22, "customer_id kosong (non-member)", blank_cust, 'Diisi "WALKIN"')
inconsistent = int(((df["is_member"] == 1) != df["customer_id"].str.startswith("M")).sum())
add(23, "Status member tidak cocok dengan customer_id", inconsistent, "Tidak ada" if inconsistent == 0 else "Perlu ditinjau")

# ---- 11. Kolom turunan ---------------------------------------------------------------------
df = df.merge(master_outlet[["outlet_id", "outlet"]], on="outlet", how="left")
df["gross_sales"] = df["qty"] * df["unit_price"]
df["net_sales"] = df["gross_sales"] - df["discount_amount"]
df["cogs"] = df["qty"] * df["cogs_per_unit"]
df["delivery_commission"] = np.where(df["channel"] == "Delivery", (df["net_sales"] * COMMISSION).round(), 0).astype(int)
df["gross_profit"] = df["net_sales"] - df["cogs"] - df["delivery_commission"]
df["tanggal"] = df["order_datetime"].dt.strftime("%Y-%m-%d")
df["bulan"] = df["order_datetime"].dt.strftime("%Y-%m")
df["jam"] = df["order_datetime"].dt.hour
df["hari"] = df["order_datetime"].dt.dayofweek.map(dict(enumerate(HARI)))
df["is_promo"] = (df["promo_name"] != "Tanpa Promo").astype(int)

neg_net = int((df["net_sales"] < 0).sum())
add(24, "Net sales negatif", neg_net, "Tidak ada" if neg_net == 0 else "Perlu ditinjau")

cols = [
    "order_id", "order_datetime", "outlet_id", "outlet", "channel", "customer_id",
    "product_id", "product", "category", "qty", "unit_price", "discount_amount",
    "promo_name", "gross_sales", "net_sales", "cogs", "delivery_commission",
    "gross_profit", "is_member", "tanggal", "bulan", "jam", "hari", "is_promo",
]
df = df[cols].sort_values(["order_datetime", "order_id", "product_id"]).reset_index(drop=True)

# ---- 12. Simpan -----------------------------------------------------------------------------
n_clean = len(df)
removed = n_raw - n_clean
add(25, "Jumlah baris akhir (clean_sales.csv)", n_clean, f"Total baris dibuang: {removed}")
pd.DataFrame(log).to_csv(DATA / "data_quality_log.csv", index=False)
df.to_csv(DATA / "clean_sales.csv", index=False)

db_path = DATA / "seduh.db"
if db_path.exists():
    db_path.unlink()
con = sqlite3.connect(db_path)
df.assign(order_datetime=df["order_datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")).to_sql("sales", con, index=False)
master_outlet.to_sql("master_outlet", con, index=False)
master_produk.to_sql("master_produk", con, index=False)
con.execute("CREATE INDEX idx_sales_order ON sales(order_id)")
con.execute("CREATE INDEX idx_sales_tanggal ON sales(tanggal)")
con.commit()
con.close()

print(pd.DataFrame(log).to_string(index=False))
print(f"\nBaris mentah {n_raw:,} -> bersih {n_clean:,} (dibuang {removed})")
print(f"Order unik: {df['order_id'].nunique():,}")
