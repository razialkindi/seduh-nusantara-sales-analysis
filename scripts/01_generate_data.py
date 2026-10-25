#!/usr/bin/env python3
"""
01_generate_data.py
Membuat data SIMULASI kedai kopi "Seduh Nusantara" (6 outlet Jabodetabek,
1 Jan - 31 Des 2025).

Keluaran (folder data/):
  raw_sales.csv      data mentah, SENGAJA kotor (bukti proses cleaning)
  master_outlet.csv  tabel master outlet
  master_produk.csv  tabel master produk (termasuk HPP per unit)

PENTING: semua pola (promo Gajian, promo Kopi Susu Juni, naiknya porsi
delivery, perilaku member) dirancang di skrip ini. Jadi analisis di tahap
berikutnya menunjukkan CARA menganalisis, bukan fakta pasar.
Catatan: Diskon Gajian tetap ada di data (bagian dari total diskon), tetapi
tidak lagi dianalisis sebagai temuan tersendiri. Fokus promo = Kopi Susu Juni.

Jalankan: python scripts/01_generate_data.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 2025
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
rng = np.random.default_rng(SEED)

# --------------------------------------------------------------------------
# 1. Tabel master
# --------------------------------------------------------------------------
# share = porsi order outlet, growth = kenaikan relatif Des vs Jan di luar tren umum
OUTLETS = pd.DataFrame(
    [
        ("SN01", "Seduh Nusantara Kemang", "Jakarta Selatan", 0.22, 0.06),
        ("SN02", "Seduh Nusantara BSD", "Tangerang Selatan", 0.19, 0.12),
        ("SN03", "Seduh Nusantara Summarecon Bekasi", "Bekasi", 0.18, 0.15),
        ("SN04", "Seduh Nusantara Margonda", "Depok", 0.16, 0.10),
        ("SN05", "Seduh Nusantara Sentul", "Bogor", 0.13, 0.02),
        ("SN06", "Seduh Nusantara Kelapa Gading", "Jakarta Utara", 0.12, -0.04),
    ],
    columns=["outlet_id", "outlet", "kota", "share", "growth"],
)

# weight = peluang dipilih di dalam grup (minuman atau makanan)
PRODUCTS = pd.DataFrame(
    [
        ("P01", "Kopi Susu Gula Aren", "Kopi", 22000, 7500, 0.200),
        ("P02", "Americano", "Kopi", 20000, 5200, 0.070),
        ("P03", "Cafe Latte", "Kopi", 28000, 9300, 0.100),
        ("P04", "Cappuccino", "Kopi", 28000, 9000, 0.080),
        ("P05", "Cold Brew", "Kopi", 30000, 9800, 0.050),
        ("P06", "Matcha Latte", "Non-Kopi", 30000, 11500, 0.100),
        ("P07", "Teh Tarik", "Non-Kopi", 18000, 4600, 0.100),
        ("P08", "Cokelat Panas", "Non-Kopi", 26000, 9800, 0.080),
        ("P09", "Lemon Tea", "Non-Kopi", 18000, 4300, 0.080),
        ("P10", "Croissant Butter", "Makanan", 24000, 10800, 0.200),
        ("P11", "Roti Bakar Cokelat", "Makanan", 20000, 8200, 0.180),
        ("P12", "Nasi Goreng Kampung", "Makanan", 32000, 15000, 0.140),
        ("P13", "Kentang Goreng", "Makanan", 20000, 7200, 0.180),
        ("P14", "Pisang Goreng", "Makanan", 16000, 6300, 0.150),
        ("P15", "Brownies", "Makanan", 24000, 10400, 0.150),
    ],
    columns=["product_id", "product", "category", "price", "cogs_per_unit", "weight"],
)

DRINK_IDX = np.where(PRODUCTS["category"] != "Makanan")[0]
FOOD_IDX = np.where(PRODUCTS["category"] == "Makanan")[0]
KOPI_SUSU_IDX = 0  # P01

# --------------------------------------------------------------------------
# 2. Parameter simulasi
# --------------------------------------------------------------------------
DAYS = pd.date_range("2025-01-01", "2025-12-31")
BASE_WALKIN = 90             # order non-member per hari (seluruh outlet) pada tren 1.0
DOW_FACTOR = [0.92, 0.92, 0.95, 0.98, 1.08, 1.22, 1.15]  # Senin..Minggu
N_MEMBERS = 2000
HOUR_W = np.array([3, 7, 9, 6, 5, 8, 10, 6, 5, 7, 9, 10, 9, 6, 3, 2], dtype=float)
HOURS = np.arange(7, 23)  # jam buka 07.00-22.59
HOUR_P = HOUR_W / HOUR_W.sum()

COMMISSION = 0.20            # komisi platform delivery dari net sales
GAJIAN_DAYS = (25, 26, 27)   # tanggal promo Gajian
GAJIAN_PCT = 0.15
KOPI_SUSU_JUNE_PCT = 0.35
KOPI_SUSU_JUNE_BOOST = 1.22  # bobot Kopi Susu naik pada Juni (efek promo ke volume)


def month_trend(month: int) -> float:
    """Tren umum: penjualan naik pelan sepanjang tahun."""
    return 0.92 + 0.016 * (month - 1)


# --------------------------------------------------------------------------
# 3. Order non-member (walk-in)
# --------------------------------------------------------------------------
walk_dates, walk_outlets = [], []
for d in DAYS:
    m = d.month
    noise = rng.lognormal(0, 0.05)
    for i, o in OUTLETS.iterrows():
        lam = (
            BASE_WALKIN
            * o.share
            * month_trend(m)
            * (1 + o.growth * (m - 1) / 11)
            * DOW_FACTOR[d.dayofweek]
            * noise
        )
        n = rng.poisson(lam)
        walk_dates += [d] * n
        walk_outlets += [i] * n
walk = pd.DataFrame(
    {"date": walk_dates, "outlet_idx": walk_outlets, "customer_id": "WALKIN", "is_member": 0}
)

# --------------------------------------------------------------------------
# 4. Order member (proses kedatangan per member)
# --------------------------------------------------------------------------
existing = rng.random(N_MEMBERS) < 0.35  # member lama: order pertama di data muncul Januari
join_day = np.where(existing, rng.integers(0, 31, N_MEMBERS), rng.integers(31, 365, N_MEMBERS))
rate = rng.lognormal(np.log(1 / 36), 0.65, N_MEMBERS)  # rata-rata ~1 order per 36 hari
rate = np.where(existing, rate * 1.15, rate)            # kohort awal lebih aktif
rate = np.where(join_day >= 181, rate * 0.80, rate)     # kohort baru (H2) kurang aktif
home = rng.choice(len(OUTLETS), size=N_MEMBERS, p=OUTLETS["share"].to_numpy())

m_dates, m_outlets, m_ids = [], [], []
for k in range(N_MEMBERS):
    t = float(join_day[k])
    while t < 365:
        outlet = home[k] if rng.random() < 0.85 else rng.integers(0, len(OUTLETS))
        m_dates.append(DAYS[int(t)])
        m_outlets.append(outlet)
        m_ids.append(f"M{k + 1:05d}")
        t += rng.exponential(1 / rate[k])
members = pd.DataFrame(
    {"date": m_dates, "outlet_idx": m_outlets, "customer_id": m_ids, "is_member": 1}
)

# --------------------------------------------------------------------------
# 5. Gabungkan jadi order: jam, channel, nomor order
# --------------------------------------------------------------------------
orders = pd.concat([walk, members], ignore_index=True)
n_orders = len(orders)
hour = rng.choice(HOURS, size=n_orders, p=HOUR_P)
orders["order_datetime"] = (
    orders["date"]
    + pd.to_timedelta(hour, unit="h")
    + pd.to_timedelta(rng.integers(0, 60, n_orders), unit="m")
    + pd.to_timedelta(rng.integers(0, 60, n_orders), unit="s")
)
orders = orders.sort_values("order_datetime", kind="stable").reset_index(drop=True)
orders["order_id"] = [f"ORD{i + 1:06d}" for i in range(n_orders)]

# porsi delivery naik linear 22,0% (Jan) -> 34,7% (Des)
month = orders["order_datetime"].dt.month.to_numpy()
p_delivery = 0.22 + (0.347 - 0.22) * (month - 1) / 11
is_delivery = rng.random(n_orders) < p_delivery
dine = rng.random(n_orders) < 0.56
orders["channel"] = np.where(is_delivery, "Delivery", np.where(dine, "Dine-in", "Takeaway"))

# --------------------------------------------------------------------------
# 6. Item per order
# --------------------------------------------------------------------------
P_FOOD = {"Dine-in": 0.42, "Takeaway": 0.27, "Delivery": 0.30}
w_drink_base = PRODUCTS.loc[DRINK_IDX, "weight"].to_numpy()
w_food = PRODUCTS.loc[FOOD_IDX, "weight"].to_numpy()
p_food_items = w_food / w_food.sum()
p_drink = w_drink_base / w_drink_base.sum()
w_drink_june = w_drink_base.copy()
w_drink_june[list(DRINK_IDX).index(KOPI_SUSU_IDX)] *= KOPI_SUSU_JUNE_BOOST
p_drink_june = w_drink_june / w_drink_june.sum()

n_drinks = rng.choice([1, 2, 3], size=n_orders, p=[0.45, 0.40, 0.15])
channel_arr = orders["channel"].to_numpy()
p_food_arr = np.array([P_FOOD[c] for c in channel_arr])
has_food = rng.random(n_orders) < p_food_arr
n_food = np.where(rng.random(n_orders) < 0.8, 1, 2)

item_order, item_prod, item_qty = [], [], []
for i in range(n_orders):
    probs = p_drink_june if month[i] == 6 else p_drink
    picks = rng.choice(DRINK_IDX, size=n_drinks[i], p=probs)
    if has_food[i]:
        picks = np.concatenate([picks, rng.choice(FOOD_IDX, size=n_food[i], p=p_food_items)])
    uniq, cnt = np.unique(picks, return_counts=True)
    for u, c in zip(uniq, cnt):
        item_order.append(i)
        item_prod.append(u)
        item_qty.append(c)

items = pd.DataFrame({"o": item_order, "p": item_prod, "qty": item_qty})
prod = PRODUCTS.iloc[items["p"]].reset_index(drop=True)
o = orders.iloc[items["o"]].reset_index(drop=True)

df = pd.DataFrame(
    {
        "order_id": o["order_id"],
        "order_datetime": o["order_datetime"],
        "outlet": OUTLETS.loc[o["outlet_idx"], "outlet"].to_numpy(),
        "channel": o["channel"],
        "customer_id": o["customer_id"],
        "product_id": prod["product_id"],
        "product": prod["product"],
        "qty": items["qty"].to_numpy(),
        "unit_price": prod["price"].to_numpy(),
        "is_member": o["is_member"],
    }
)

# --------------------------------------------------------------------------
# 7. Promo dan diskon
# --------------------------------------------------------------------------
dom = df["order_datetime"].dt.day
mon = df["order_datetime"].dt.month
gross = df["qty"] * df["unit_price"]

is_gajian = dom.isin(GAJIAN_DAYS)
is_ks_june = (df["product_id"] == "P01") & (mon == 6)

pct = np.where(is_ks_june, KOPI_SUSU_JUNE_PCT, np.where(is_gajian, GAJIAN_PCT, 0.0))
df["discount_amount"] = (gross * pct).round(-2).astype(int)
df["promo_name"] = np.where(
    is_ks_june, "Promo Kopi Susu Juni", np.where(is_gajian, "Diskon Gajian", "")
)

# --------------------------------------------------------------------------
# 8. Simpan master (bersih)
# --------------------------------------------------------------------------
OUTLETS[["outlet_id", "outlet", "kota"]].to_csv(DATA / "master_outlet.csv", index=False)
PRODUCTS[["product_id", "product", "category", "price", "cogs_per_unit"]].to_csv(
    DATA / "master_produk.csv", index=False
)

# --------------------------------------------------------------------------
# 9. Kotori data: ubah ke teks lalu suntikkan masalah realistis
# --------------------------------------------------------------------------
raw = df.copy()
raw["order_datetime"] = raw["order_datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
raw["unit_price"] = raw["unit_price"].astype(str)
raw["qty"] = raw["qty"].astype(str)
raw["discount_amount"] = raw["discount_amount"].astype(str)
raw["is_member"] = np.where(
    raw["is_member"] == 1,
    rng.choice(["Ya", "1", "member", "Y"], size=len(raw)),
    rng.choice(["Tidak", "0", "non-member", "N"], size=len(raw)),
)
raw["customer_id"] = raw["customer_id"].replace("WALKIN", "")  # non-member: kosong
N = len(raw)


def pick(frac=None, n=None):
    """Indeks baris acak (tanpa pengembalian)."""
    k = n if n is not None else int(round(N * frac))
    return rng.choice(N, size=k, replace=False)


# (a) nama outlet tidak seragam: huruf besar/kecil, spasi berlebih
idx = pick(0.04)
raw.loc[idx, "outlet"] = [
    rng.choice([s.upper(), s.lower(), " " + s, s + "  ", s.replace(" ", "  ")])
    for s in raw.loc[idx, "outlet"]
]
# (b) channel tidak seragam
variants = {
    "Dine-in": ["dine in", "Dine In", "DINE-IN", "dine-in"],
    "Takeaway": ["Take Away", "takeaway", "TAKEAWAY"],
    "Delivery": ["delivery", "DELIVERY", "Delivery "],
}
idx = pick(0.06)
raw.loc[idx, "channel"] = [rng.choice(variants[c]) for c in raw.loc[idx, "channel"]]
# (c) harga ditulis sebagai teks "Rp22.000"
idx = pick(0.015)
raw.loc[idx, "unit_price"] = ["Rp" + f"{int(v):,}".replace(",", ".") for v in raw.loc[idx, "unit_price"]]
# (d) format tanggal dd/mm/yyyy HH:MM
idx = pick(0.01)
raw.loc[idx, "order_datetime"] = pd.to_datetime(raw.loc[idx, "order_datetime"]).dt.strftime("%d/%m/%Y %H:%M")
# (e) outlet kosong (bisa dipulihkan dari baris lain di order yang sama)
idx = pick(0.003)
raw.loc[idx, "outlet"] = np.nan
# (f) product_id kosong (bisa dipulihkan dari nama produk)
idx = pick(n=20)
raw.loc[idx, "product_id"] = np.nan
# (g) spasi di nama produk
idx = pick(0.01)
raw.loc[idx, "product"] = raw.loc[idx, "product"] + " "
# (h) discount_amount kosong pada baris tanpa promo
no_promo = np.where(raw["promo_name"] == "")[0]
idx = rng.choice(no_promo, size=int(len(no_promo) * 0.003), replace=False)
raw.loc[idx, "discount_amount"] = np.nan
# (i) tahun salah: 12 baris tertulis 2026 (tahun benar tidak bisa dipastikan)
idx = pick(n=12)
raw.loc[idx, "order_datetime"] = raw.loc[idx, "order_datetime"].str.replace("2025", "2026", regex=False)
# (j) qty tidak valid (0 atau negatif) dan outlier (90)
idx = pick(n=25)
raw.loc[idx, "qty"] = rng.choice(["0", "-1"], size=25)
idx = pick(n=15)
raw.loc[idx, "qty"] = "90"
# (k) baris duplikat persis (hasil ekspor ganda)
dups = raw.iloc[rng.choice(N, size=80, replace=False)]
raw = pd.concat([raw, dups], ignore_index=True)

raw.to_csv(DATA / "raw_sales.csv", index=False)

print(f"Order dasar      : {n_orders:,}")
print(f"Baris raw_sales  : {len(raw):,} (termasuk 80 duplikat sengaja)")
print("File ditulis ke  :", DATA)
