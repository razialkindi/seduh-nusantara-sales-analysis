#!/usr/bin/env python3
"""
04_verify_sql.py
Menjalankan 10 query di sql/analysis_queries.sql pada data/seduh.db, lalu
membandingkan hasilnya dengan data/metrics.json (hasil pandas).
Jika ada selisih, skrip berhenti dengan pesan error.

Jalankan: python scripts/04_verify_sql.py
"""
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
M = json.load(open(ROOT / "data" / "metrics.json", encoding="utf-8"))
con = sqlite3.connect(ROOT / "data" / "seduh.db")

text = (ROOT / "sql" / "analysis_queries.sql").read_text(encoding="utf-8")
blocks = re.split(r"^-- Query (\d+):.*$", text, flags=re.M)
queries = {int(blocks[i]): blocks[i + 1] for i in range(1, len(blocks), 2)}
assert sorted(queries) == list(range(1, 11)), "Harus ada 10 query"


def run(n):
    cur = con.execute(queries[n])
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def close(a, b, tol=1e-4, label=""):
    ok = abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))
    assert ok, f"BEDA {label}: SQL={a} pandas={b}"


checks = 0

# Q1
r = run(1)[0]; k = M["kpi"]
close(r["net_sales"], k["net_sales"], label="Q1 net_sales")
close(r["gross_profit"], k["gross_profit"], label="Q1 gross_profit")
close(r["orders"], k["orders"], label="Q1 orders")
close(r["margin"], k["margin"], 1e-3, "Q1 margin")
close(r["aov"], k["aov"], 1e-3, "Q1 aov")
close(r["total_discount"], k["total_discount"], label="Q1 discount")
checks += 6

# Q2
for r in run(2):
    m = M["monthly"][r["bulan"]]
    close(r["net_sales"], m["net_sales"], label=f"Q2 {r['bulan']} net")
    close(r["orders"], m["orders"], label=f"Q2 {r['bulan']} orders")
    close(r["margin"], m["margin"], 1e-3, f"Q2 {r['bulan']} margin")
    checks += 3

# Q3
by_outlet = {o["outlet"]: o for o in M["outlets"]}
for r in run(3):
    o = by_outlet[r["outlet"]]
    close(r["net_sales"], o["net_sales"], label=f"Q3 {r['outlet']} net")
    close(r["growth_h2_vs_h1"], o["growth_h2_vs_h1"], 1e-3, f"Q3 {r['outlet']} growth")
    checks += 2

# Q4
for r in run(4):
    c = M["channel"][r["channel"]]
    close(r["orders"], c["orders"], label=f"Q4 {r['channel']} orders")
    close(r["share"], c["share"], 1e-3, f"Q4 {r['channel']} share")
    close(r["aov"], c["aov"], 1e-3, f"Q4 {r['channel']} aov")
    close(r["margin"], c["margin"], 1e-3, f"Q4 {r['channel']} margin")
    checks += 4

# Q5
for r in run(5):
    close(r["delivery_share"], M["monthly"][r["bulan"]]["delivery_share"], 1e-3, f"Q5 {r['bulan']} share")
    checks += 1
q5 = run(5)
close(q5[0]["delivery_share"], M["delivery_trend"]["share_jan"], 1e-3, "Q5 share Jan")
close(q5[-1]["delivery_share"], M["delivery_trend"]["share_dec"], 1e-3, "Q5 share Des")
checks += 2

# Q6
by_promo = {p["promo"]: p for p in M["promo"]}
for r in run(6):
    p = by_promo[r["promo_name"]]
    close(r["discount"], p["discount"], label=f"Q6 {r['promo_name']} discount")
    close(r["orders"], p["orders"], label=f"Q6 {r['promo_name']} orders")
    close(r["margin"], p["margin"], 1e-3, f"Q6 {r['promo_name']} margin")
    checks += 3

# Q7
for r in run(7):
    c = M["channel"][r["channel"]]
    close(r["net_sales"], c["net_sales"], label=f"Q7 {r['channel']} net")
    close(r["sales_share"], c["sales_share"], 1e-3, f"Q7 {r['channel']} porsi penjualan")
    close(r["gp_share"], c["gp_share"], 1e-3, f"Q7 {r['channel']} porsi laba")
    checks += 3

# Q8
rows = {r["bulan"]: r for r in run(8)}
for key, bulan in (("mei", "2025-05"), ("juni", "2025-06")):
    close(rows[bulan]["units"], M["kopi_susu"][key]["units"], label=f"Q8 {key} units")
    close(rows[bulan]["gross_profit"], M["kopi_susu"][key]["gross_profit"], label=f"Q8 {key} gp")
    checks += 2

# Q9
rows = {r["has_food"]: r for r in run(9)}
close(rows[1]["share"], M["food"]["attach"], 1e-3, "Q9 attach")
close(rows[1]["aov"], M["food"]["aov_with_food"], 1e-3, "Q9 aov makanan")
close(rows[0]["aov"], M["food"]["aov_without_food"], 1e-3, "Q9 aov tanpa makanan")
checks += 3

# Q10
r = run(10)[0]
close(r["eligible_members"], M["member"]["eligible"], label="Q10 eligible")
close(r["return_60d"], M["member"]["return_60d"], 1e-3, "Q10 retensi")
checks += 2

print(f"OK: 10 query SQL cocok dengan pandas ({checks} angka dibandingkan).")
