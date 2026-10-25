#!/usr/bin/env python3
"""
03_analysis.py
Analisis "penjualan tumbuh, di mana laba bocor?" dari data/clean_sales.csv.
Keluaran: data/metrics.json (semua angka yang dipakai di deck dan dashboard).

Definisi KPI:
  net_sales    = qty x harga - diskon
  gross_profit = net_sales - HPP (cogs) - komisi delivery
  margin       = gross_profit / net_sales
  AOV          = net_sales / order unik   (JANGAN COUNT(*): satu order punya banyak baris)

Jalankan: python scripts/03_analysis.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
df = pd.read_csv(DATA / "clean_sales.csv", parse_dates=["order_datetime"])
df["tgl"] = pd.to_datetime(df["tanggal"])


def margin(g):
    return g["gross_profit"].sum() / g["net_sales"].sum()


M = {}

# ---- 1. KPI utama --------------------------------------------------------------
orders = df["order_id"].nunique()
M["kpi"] = {
    "net_sales": int(df["net_sales"].sum()),
    "gross_profit": int(df["gross_profit"].sum()),
    "margin": margin(df),
    "orders": int(orders),
    "aov": df["net_sales"].sum() / orders,
    "total_discount": int(df["discount_amount"].sum()),
    "total_commission": int(df["delivery_commission"].sum()),
    "rows": int(len(df)),
}

# ---- 2. Tren bulanan dan pertumbuhan -----------------------------------------------
mo = df.groupby("bulan").agg(net_sales=("net_sales", "sum"), gross_profit=("gross_profit", "sum"),
                             orders=("order_id", "nunique"))
mo["margin"] = mo["gross_profit"] / mo["net_sales"]
mo["delivery_share"] = df[df["channel"] == "Delivery"].groupby("bulan")["order_id"].nunique() / mo["orders"]
M["monthly"] = {k: v for k, v in mo.reset_index().set_index("bulan").to_dict("index").items()}
h1 = df[df["order_datetime"] < "2025-07-01"]
h2 = df[df["order_datetime"] >= "2025-07-01"]
M["growth"] = {
    "net_sales_h1": int(h1["net_sales"].sum()),
    "net_sales_h2": int(h2["net_sales"].sum()),
    "net_sales_h2_vs_h1": h2["net_sales"].sum() / h1["net_sales"].sum() - 1,
    "gross_profit_h1": int(h1["gross_profit"].sum()),
    "gross_profit_h2": int(h2["gross_profit"].sum()),
    "gross_profit_h2_vs_h1": h2["gross_profit"].sum() / h1["gross_profit"].sum() - 1,
    "margin_h1": margin(h1),
    "margin_h2": margin(h2),
}

# ---- 3. Outlet ------------------------------------------------------------------------
out = []
for name, g in df.groupby("outlet"):
    a, b = g[g["order_datetime"] < "2025-07-01"], g[g["order_datetime"] >= "2025-07-01"]
    out.append({
        "outlet": name,
        "net_sales": int(g["net_sales"].sum()),
        "gross_profit": int(g["gross_profit"].sum()),
        "margin": margin(g),
        "orders": int(g["order_id"].nunique()),
        "delivery_share": g[g["channel"] == "Delivery"]["order_id"].nunique() / g["order_id"].nunique(),
        "growth_h2_vs_h1": b["net_sales"].sum() / a["net_sales"].sum() - 1,
    })
M["outlets"] = sorted(out, key=lambda r: -r["net_sales"])

# ---- 4. Channel -------------------------------------------------------------------------
ch = {}
for name, g in df.groupby("channel"):
    n = g["order_id"].nunique()
    ch[name] = {
        "orders": int(n),
        "share": n / orders,
        "aov": g["net_sales"].sum() / n,
        "net_sales": int(g["net_sales"].sum()),
        "gross_profit": int(g["gross_profit"].sum()),
        "margin": margin(g),
        "commission": int(g["delivery_commission"].sum()),
        # kontribusi channel terhadap total penjualan dan total laba
        "sales_share": g["net_sales"].sum() / df["net_sales"].sum(),
        "gp_share": g["gross_profit"].sum() / df["gross_profit"].sum(),
    }
M["channel"] = ch
jan = df[df["bulan"] == "2025-01"]
dec = df[df["bulan"] == "2025-12"]
M["delivery_trend"] = {
    "share_jan": jan[jan["channel"] == "Delivery"]["order_id"].nunique() / jan["order_id"].nunique(),
    "share_dec": dec[dec["channel"] == "Delivery"]["order_id"].nunique() / dec["order_id"].nunique(),
    "margin_jan": margin(jan),
    "margin_dec": margin(dec),
}

# ---- 5. Promo --------------------------------------------------------------------------------
pr = []
for name, g in df.groupby("promo_name"):
    pr.append({
        "promo": name,
        "discount": int(g["discount_amount"].sum()),
        "net_sales": int(g["net_sales"].sum()),
        "gross_profit": int(g["gross_profit"].sum()),
        "margin": margin(g),
        "orders": int(g["order_id"].nunique()),
    })
M["promo"] = sorted(pr, key=lambda r: -r["discount"])

# 5a. Kopi Susu Gula Aren: Mei vs Juni
ks = df[df["product"] == "Kopi Susu Gula Aren"]


def ks_month(m):
    g = ks[ks["bulan"] == m]
    units = int(g["qty"].sum())
    return {"units": units, "net_sales": int(g["net_sales"].sum()), "gross_profit": int(g["gross_profit"].sum()),
            "gp_per_unit": g["gross_profit"].sum() / units, "discount": int(g["discount_amount"].sum())}


may, jun = ks_month("2025-05"), ks_month("2025-06")
M["kopi_susu"] = {
    "mei": may,
    "juni": jun,
    "unit_change": jun["units"] / may["units"] - 1,
    "gp_change": jun["gross_profit"] / may["gross_profit"] - 1,
    "gp_lost": may["gross_profit"] - jun["gross_profit"],
    "units_needed_to_match_may": may["gross_profit"] / jun["gp_per_unit"],
}

# ---- 6. Makanan dan member -----------------------------------------------------------------------
o = df.groupby("order_id").agg(net=("net_sales", "sum"), gp=("gross_profit", "sum"),
                               food=("category", lambda s: (s == "Makanan").any()),
                               channel=("channel", "first"))
food_gp = df[df["category"] == "Makanan"].groupby("order_id")["gross_profit"].sum()
M["food"] = {
    "attach": float(o["food"].mean()),
    "aov_with_food": float(o.loc[o["food"], "net"].mean()),
    "aov_without_food": float(o.loc[~o["food"], "net"].mean()),
    "avg_food_gp_per_food_order": float(food_gp.mean()),
    "attach_by_channel": {c: float(o.loc[o["channel"] == c, "food"].mean()) for c in ["Dine-in", "Takeaway", "Delivery"]},
}

cat = df.groupby("category").agg(net_sales=("net_sales", "sum"), gross_profit=("gross_profit", "sum"))
cat["margin"] = cat["gross_profit"] / cat["net_sales"]
M["category"] = cat.reset_index().to_dict("records")

mem = df[df["is_member"] == 1].drop_duplicates("order_id")[["order_id", "customer_id", "tgl"]]
first = mem.groupby("customer_id")["tgl"].min().rename("first")
mem = mem.merge(first, on="customer_id")
later = mem[(mem["tgl"] > mem["first"]) & (mem["tgl"] <= mem["first"] + pd.Timedelta(days=60))]
returned = set(later["customer_id"])
elig = first[first <= pd.Timestamp("2025-12-31") - pd.Timedelta(days=60)]
rate = elig.index.isin(returned).mean()
early = elig[elig < "2025-07-01"]
late = elig[elig >= "2025-07-01"]
M["member"] = {
    "members": int(df.loc[df["is_member"] == 1, "customer_id"].nunique()),
    "member_order_share": float(df.loc[df["is_member"] == 1, "order_id"].nunique() / orders),
    "eligible": int(len(elig)),
    "return_60d": float(rate),
    "return_60d_cohort_h1": float(early.index.isin(returned).mean()),
    "return_60d_cohort_h2": float(late.index.isin(returned).mean()),
    "eligible_h1": int(len(early)),
    "eligible_h2": int(len(late)),
}

# ---- 7. Estimasi dampak rekomendasi (TIDAK dijumlahkan: asumsi beda dan tumpang tindih) ------------
dl = df[df["channel"] == "Delivery"]
price_up = 0.05
M["impact"] = {
    # R1: harga menu di aplikasi delivery naik 5%, volume dianggap tetap, komisi tetap 20% dari net sales
    "delivery_price_up_pct": price_up,
    "delivery_price_up_gain": float(dl["net_sales"].sum() * price_up * (1 - 0.20)),
    # titik impas: order delivery boleh turun sekian persen sebelum laba delivery lebih rendah dari sekarang
    "delivery_price_up_breakeven_drop": float(
        dl["net_sales"].sum() * price_up * (1 - 0.20)
        / (dl["gross_profit"].sum() + dl["net_sales"].sum() * price_up * (1 - 0.20))
    ),
    # selisih margin delivery vs dine-in, dikali net sales delivery = "laba yang bocor" di channel ini
    "delivery_margin_gap_loss": float(dl["net_sales"].sum() * (ch["Dine-in"]["margin"] - ch["Delivery"]["margin"])),
    # R2: batasi diskon besar, selisih laba Kopi Susu Juni vs Mei
    "kopi_susu_gp_lost": M["kopi_susu"]["gp_lost"],
    # R3 (tambahan, tidak masuk deck): attach naik 5 poin persentase, pembeli tambahan membeli makanan seperti rata-rata
    "food_attach_up_pts": 0.05,
    "food_attach_gain": float(0.05 * orders * M["food"]["avg_food_gp_per_food_order"]),
}

with open(DATA / "metrics.json", "w", encoding="utf-8") as f:
    json.dump(M, f, ensure_ascii=False, indent=2, default=float)

# ---- ringkas ke layar -------------------------------------------------------------------------------
k = M["kpi"]
print(f"Net sales   Rp{k['net_sales']:,}".replace(",", "."))
print(f"Gross profit Rp{k['gross_profit']:,}".replace(",", "."))
print(f"Margin {k['margin']:.1%} | Order {k['orders']:,} | AOV Rp{k['aov']:,.0f}".replace(",", "."))
for c, v in ch.items():
    print(f"{c:9s} order {v['share']:.1%}  AOV {v['aov']:,.0f}  margin {v['margin']:.1%}".replace(",", "."))
print("Pertumbuhan H2 vs H1 net sales:", f"{M['growth']['net_sales_h2_vs_h1']:.1%}",
      "| gross profit:", f"{M['growth']['gross_profit_h2_vs_h1']:.1%}")
print("Delivery Jan->Des:", f"{M['delivery_trend']['share_jan']:.1%} -> {M['delivery_trend']['share_dec']:.1%}")
print("Delivery: porsi penjualan", f"{ch['Delivery']['sales_share']:.1%}", "| porsi laba", f"{ch['Delivery']['gp_share']:.1%}")
print("Kopi Susu:", M["kopi_susu"])
print("Food:", M["food"])
print("Member:", M["member"])
print("Impact:", M["impact"])
