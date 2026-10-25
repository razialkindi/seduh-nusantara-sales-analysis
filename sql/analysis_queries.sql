-- ============================================================================
-- analysis_queries.sql  |  Seduh Nusantara 2025  |  SQLite
-- Database: data/seduh.db  (tabel: sales, master_outlet, master_produk)
-- Satu baris sales = satu item dalam satu order. Hitung order dengan
-- COUNT(DISTINCT order_id), BUKAN COUNT(*).
-- Hasil setiap query sama dengan scripts/03_analysis.py (cek: 04_verify_sql.py)
-- ============================================================================

-- Query 1: KPI utama
SELECT
  SUM(net_sales)                                        AS net_sales,
  SUM(gross_profit)                                     AS gross_profit,
  ROUND(1.0 * SUM(gross_profit) / SUM(net_sales), 4)    AS margin,
  COUNT(DISTINCT order_id)                              AS orders,
  ROUND(1.0 * SUM(net_sales) / COUNT(DISTINCT order_id), 0) AS aov,
  SUM(discount_amount)                                  AS total_discount
FROM sales;

-- Query 2: Tren bulanan (net sales, gross profit, margin, order)
SELECT
  bulan,
  SUM(net_sales)                                      AS net_sales,
  SUM(gross_profit)                                   AS gross_profit,
  ROUND(1.0 * SUM(gross_profit) / SUM(net_sales), 4)  AS margin,
  COUNT(DISTINCT order_id)                            AS orders
FROM sales
GROUP BY bulan
ORDER BY bulan;

-- Query 3: Kinerja outlet dan pertumbuhan H2 vs H1
SELECT
  outlet,
  SUM(net_sales)                                      AS net_sales,
  ROUND(1.0 * SUM(gross_profit) / SUM(net_sales), 4)  AS margin,
  ROUND(1.0 * SUM(CASE WHEN tanggal >= '2025-07-01' THEN net_sales END)
            / SUM(CASE WHEN tanggal <  '2025-07-01' THEN net_sales END) - 1, 4) AS growth_h2_vs_h1
FROM sales
GROUP BY outlet
ORDER BY net_sales DESC;

-- Query 4: Channel (hitung per order dulu supaya order tidak terhitung ganda)
WITH o AS (
  SELECT order_id, channel, SUM(net_sales) AS net, SUM(gross_profit) AS gp
  FROM sales
  GROUP BY order_id, channel
)
SELECT
  channel,
  COUNT(*)                                            AS orders,
  ROUND(1.0 * COUNT(*) / (SELECT COUNT(*) FROM o), 4) AS share,
  ROUND(AVG(net), 0)                                  AS aov,
  ROUND(1.0 * SUM(gp) / SUM(net), 4)                  AS margin
FROM o
GROUP BY channel
ORDER BY orders DESC;

-- Query 5: Porsi order Delivery per bulan, dan margin Delivery vs non-Delivery
SELECT
  bulan,
  ROUND(1.0 * COUNT(DISTINCT CASE WHEN channel = 'Delivery' THEN order_id END)
            / COUNT(DISTINCT order_id), 4)            AS delivery_share,
  ROUND(1.0 * SUM(CASE WHEN channel =  'Delivery' THEN gross_profit END)
            / SUM(CASE WHEN channel =  'Delivery' THEN net_sales END), 4) AS margin_delivery,
  ROUND(1.0 * SUM(CASE WHEN channel <> 'Delivery' THEN gross_profit END)
            / SUM(CASE WHEN channel <> 'Delivery' THEN net_sales END), 4) AS margin_non_delivery
FROM sales
GROUP BY bulan
ORDER BY bulan;

-- Query 6: Ringkasan per promo
SELECT
  promo_name,
  COUNT(DISTINCT order_id)                            AS orders,
  SUM(discount_amount)                                AS discount,
  SUM(net_sales)                                      AS net_sales,
  SUM(gross_profit)                                   AS gross_profit,
  ROUND(1.0 * SUM(gross_profit) / SUM(net_sales), 4)  AS margin
FROM sales
GROUP BY promo_name
ORDER BY discount DESC;

-- Query 7: Kontribusi channel terhadap total penjualan dan total laba kotor
-- (Delivery menyumbang porsi penjualan lebih besar daripada porsi labanya)
SELECT
  channel,
  SUM(net_sales)                                                              AS net_sales,
  SUM(gross_profit)                                                           AS gross_profit,
  ROUND(1.0 * SUM(net_sales)    / (SELECT SUM(net_sales)    FROM sales), 4)  AS sales_share,
  ROUND(1.0 * SUM(gross_profit) / (SELECT SUM(gross_profit) FROM sales), 4)  AS gp_share
FROM sales
GROUP BY channel
ORDER BY sales_share DESC;

-- Query 8: Kopi Susu Gula Aren, Mei vs Juni (unit naik, laba turun)
SELECT
  bulan,
  SUM(qty)                                            AS units,
  SUM(net_sales)                                      AS net_sales,
  SUM(gross_profit)                                   AS gross_profit,
  ROUND(1.0 * SUM(gross_profit) / SUM(qty), 0)        AS gp_per_unit
FROM sales
WHERE product = 'Kopi Susu Gula Aren'
  AND bulan IN ('2025-05', '2025-06')
GROUP BY bulan
ORDER BY bulan;

-- Query 9: Food attach rate dan nilai order dengan vs tanpa makanan
WITH o AS (
  SELECT
    order_id,
    SUM(net_sales) AS net,
    MAX(CASE WHEN category = 'Makanan' THEN 1 ELSE 0 END) AS has_food
  FROM sales
  GROUP BY order_id
)
SELECT
  has_food,
  COUNT(*)                                            AS orders,
  ROUND(1.0 * COUNT(*) / (SELECT COUNT(*) FROM o), 4) AS share,
  ROUND(AVG(net), 0)                                  AS aov
FROM o
GROUP BY has_food
ORDER BY has_food DESC;

-- Query 10: Retensi member, kembali order dalam <= 60 hari setelah order pertama
-- Hanya member yang order pertamanya cukup lama (>= 60 hari sebelum 31 Des 2025).
WITH mo AS (
  SELECT DISTINCT customer_id, order_id, tanggal
  FROM sales
  WHERE is_member = 1
),
first_order AS (
  SELECT customer_id, MIN(tanggal) AS first_date
  FROM mo
  GROUP BY customer_id
),
elig AS (
  SELECT * FROM first_order
  WHERE julianday(first_date) + 60 <= julianday('2025-12-31')
),
returned AS (
  SELECT DISTINCT e.customer_id
  FROM elig e
  JOIN mo m
    ON m.customer_id = e.customer_id
   AND m.tanggal > e.first_date
   AND julianday(m.tanggal) <= julianday(e.first_date) + 60
)
SELECT
  COUNT(*)                                                        AS eligible_members,
  (SELECT COUNT(*) FROM returned)                                 AS returned_members,
  ROUND(1.0 * (SELECT COUNT(*) FROM returned) / COUNT(*), 4)      AS return_60d
FROM elig;
