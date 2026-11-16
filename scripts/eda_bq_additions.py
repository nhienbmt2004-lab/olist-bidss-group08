"""Additional MySQL EDA aligned with the five business questions."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def read(connection, sql: str) -> pd.DataFrame:
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return pd.DataFrame(cursor.fetchall(), columns=[col[0] for col in cursor.description])


def table(data: pd.DataFrame, out_dir: Path, filename: str) -> None:
    data.to_csv(out_dir / filename, index=False, encoding="utf-8-sig")


def chart(fig_dir: Path, filename: str) -> None:
    plt.tight_layout()
    plt.savefig(fig_dir / filename, dpi=220, bbox_inches="tight")
    plt.close()


def run_bq_eda(connection, out_dir: Path, fig_dir: Path) -> dict[str, object]:
    """Create CSV and PNG evidence. Return counts for a human-readable report."""
    # BQ1: month and customer state at order grain. Small cells remain in the
    # CSV but the heatmap hides cells with fewer than 100 eligible orders.
    state_month = read(connection, """
        SELECT DATE_FORMAT(d.FullDate, '%Y-%m') AS PurchaseMonth,
               COALESCE(g.StateCode, 'Unknown') AS CustomerState,
               COUNT(*) AS EligibleOrders,
               SUM(o.IsOnTime = 0) AS LateOrders,
               ROUND(AVG(o.IsOnTime), 5) AS OnTimeRate,
               ROUND(AVG(CASE WHEN o.IsOnTime = 0 THEN o.DelayDays END), 2) AS AvgLateDays
        FROM FactOrderDelivery o
        JOIN DimDate d ON d.DateKey = o.PurchaseDateKey
        JOIN DimCustomer c ON c.CustomerKey = o.CustomerKey
        LEFT JOIN DimGeography g ON g.GeographyKey = c.GeographyKey
        WHERE o.IsOnTime IS NOT NULL
        GROUP BY PurchaseMonth, CustomerState
        ORDER BY PurchaseMonth, CustomerState
    """)
    state_month['LateRate'] = state_month.LateOrders / state_month.EligibleOrders
    table(state_month, out_dir, 'bq1_late_state_month.csv')
    monthly_delivery = (state_month.groupby('PurchaseMonth', as_index=False)
                        .agg(EligibleOrders=('EligibleOrders', 'sum'),
                             LateOrders=('LateOrders', 'sum')))
    monthly_delivery['LateRate'] = monthly_delivery.LateOrders / monthly_delivery.EligibleOrders
    table(monthly_delivery, out_dir, 'bq1_late_month.csv')
    state_delivery = (state_month.groupby('CustomerState', as_index=False)
                      .agg(EligibleOrders=('EligibleOrders', 'sum'),
                           LateOrders=('LateOrders', 'sum')))
    state_delivery['LateRate'] = state_delivery.LateOrders / state_delivery.EligibleOrders
    table(state_delivery.sort_values('LateOrders', ascending=False), out_dir,
          'bq1_late_state.csv')
    valid_months = monthly_delivery[monthly_delivery.PurchaseMonth.between('2017-01', '2018-08')]
    plt.figure(figsize=(11, 4.8))
    plt.plot(valid_months.PurchaseMonth, valid_months.LateRate * 100,
             marker='o', markersize=3, color='#c65d52')
    plt.xticks(rotation=60, ha='right')
    plt.ylabel('Late orders / eligible delivered orders (%)')
    plt.title('Late delivery by purchase month, Jan 2017–Aug 2018')
    chart(fig_dir, 'late_by_month.png')
    top_states = state_delivery.nlargest(12, 'EligibleOrders').CustomerState.tolist()
    matrix = state_month[
        state_month.CustomerState.isin(top_states) &
        state_month.PurchaseMonth.between('2017-01', '2018-08')
    ].copy()
    matrix.loc[matrix.EligibleOrders < 100, 'LateRate'] = np.nan
    pivot = matrix.pivot(index='CustomerState', columns='PurchaseMonth', values='LateRate')
    pivot = pivot.reindex(top_states)
    fig, ax = plt.subplots(figsize=(12, 6))
    image = ax.imshow(pivot.to_numpy(dtype=float) * 100, cmap='YlOrRd',
                      vmin=0, vmax=40, aspect='auto')
    ax.set_xticks(range(len(pivot.columns)), pivot.columns, rotation=60, ha='right')
    ax.set_yticks(range(len(pivot.index)), pivot.index)
    fig.colorbar(image, ax=ax, label='Late rate (%)')
    ax.set_title('Late rate by state and month (blank: fewer than 100 orders)')
    chart(fig_dir, 'late_state_month_heatmap.png')

    # BQ2: review at mutually exclusive delay buckets, one order per review.
    delay_review = read(connection, """
        SELECT CASE
                 WHEN IsOnTime = 1 THEN 'On time'
                 WHEN DelayDays BETWEEN 1 AND 3 THEN '1–3 days'
                 WHEN DelayDays BETWEEN 4 AND 7 THEN '4–7 days'
                 WHEN DelayDays BETWEEN 8 AND 14 THEN '8–14 days'
                 ELSE '>14 days' END AS DelayBucket,
               COUNT(*) AS EligibleOrders,
               COUNT(ReviewScore) AS ReviewedOrders,
               ROUND(AVG(ReviewScore), 3) AS AvgReview,
               ROUND(AVG(CASE WHEN ReviewScore IS NULL THEN NULL
                              WHEN ReviewScore <= 2 THEN 1 ELSE 0 END), 5) AS LowReviewRate
        FROM FactOrderDelivery WHERE IsOnTime IS NOT NULL
        GROUP BY DelayBucket
    """)
    bucket_order = ['On time', '1–3 days', '4–7 days', '8–14 days', '>14 days']
    delay_review['DelayBucket'] = pd.Categorical(delay_review.DelayBucket,
                                                  categories=bucket_order, ordered=True)
    delay_review = delay_review.sort_values('DelayBucket')
    table(delay_review, out_dir, 'bq2_review_delay_bucket.csv')
    fig, ax = plt.subplots(figsize=(8, 4.8))
    bars = ax.bar(delay_review.DelayBucket.astype(str), delay_review.AvgReview.astype(float),
                  color=['#3f9e81', '#e7b36d', '#e99a66', '#de765c', '#c95450'])
    ax.set_ylim(0, 5)
    ax.set_ylabel('Average latest review score')
    ax.set_title('Review score by delay severity (association)')
    for bar, value in zip(bars, delay_review.AvgReview):
        ax.text(bar.get_x() + bar.get_width()/2, float(value) + .07,
                f'{float(value):.2f}', ha='center')
    chart(fig_dir, 'review_by_delay_bucket.png')

    # BQ3: order-grain seller metrics; GMV stays at item grain.
    sellers = read(connection, """
        WITH sales AS (
            SELECT SellerKey, COUNT(*) AS Items, ROUND(SUM(Price), 2) AS GMV
            FROM FactOrderItem GROUP BY SellerKey
        ), seller_orders AS (
            SELECT DISTINCT SellerKey, OrderId FROM FactOrderItem
        ), quality AS (
            SELECT so.SellerKey, COUNT(*) AS Orders,
                   SUM(o.IsOnTime IS NOT NULL) AS EligibleOrders,
                   SUM(o.IsOnTime = 0) AS LateOrders,
                   COUNT(o.ReviewScore) AS ReviewedOrders,
                   ROUND(AVG(o.ReviewScore), 3) AS AvgReview
            FROM seller_orders so
            JOIN FactOrderDelivery o ON o.OrderId = so.OrderId
            GROUP BY so.SellerKey
        )
        SELECT d.SellerId, q.Orders, s.Items, s.GMV, q.EligibleOrders,
               q.LateOrders, ROUND(q.LateOrders / NULLIF(q.EligibleOrders, 0), 5) AS LateRate,
               q.ReviewedOrders, q.AvgReview
        FROM DimSeller d JOIN sales s ON s.SellerKey = d.SellerKey
        JOIN quality q ON q.SellerKey = d.SellerKey
        ORDER BY s.GMV DESC, d.SellerId
    """)
    table(sellers, out_dir, 'bq3_seller_gmv_quality.csv')
    seller_candidates = sellers[
        (sellers.EligibleOrders >= 100) & (sellers.GMV >= 100000) &
        ((sellers.LateRate >= .10) | (sellers.AvgReview < 4.0))
    ].copy()
    table(seller_candidates, out_dir, 'bq3_seller_candidates.csv')
    sellers['CumulativeGMVShare'] = sellers.GMV.astype(float).cumsum() / sellers.GMV.astype(float).sum()
    table(sellers[['SellerId', 'Orders', 'GMV', 'CumulativeGMVShare']],
          out_dir, 'bq3_seller_pareto.csv')
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.plot(np.arange(1, len(sellers)+1)/len(sellers)*100,
            sellers.CumulativeGMVShare*100, color='#5278af', linewidth=2)
    ax.axhline(80, color='#c95450', linestyle='--', linewidth=1)
    ax.set_xlabel('Top sellers by GMV (% of sellers)')
    ax.set_ylabel('Cumulative GMV (%)')
    ax.set_title('Seller GMV concentration (Pareto)')
    chart(fig_dir, 'seller_gmv_pareto.png')
    eligible_sellers = sellers[sellers.EligibleOrders >= 30]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.scatter(eligible_sellers.LateRate.astype(float)*100,
               eligible_sellers.GMV.astype(float), s=18, alpha=.45, color='#5278af')
    ax.set_xlabel('Late rate (%) — at least 30 eligible orders')
    ax.set_ylabel('GMV (R$)')
    ax.set_title('Seller size versus observed delivery quality')
    chart(fig_dir, 'seller_gmv_late_scatter.png')

    # BQ4: identical Jan–Aug windows for year-on-year growth. Review is one
    # score per order within each category; an order can appear in two categories.
    categories = read(connection, """
        WITH sales AS (
            SELECT c.CategoryName, COUNT(*) AS Items,
                   COUNT(DISTINCT i.OrderId) AS Orders,
                   ROUND(SUM(i.Price), 2) AS GMV,
                   ROUND(SUM(CASE WHEN i.PurchaseDateKey BETWEEN 20170101 AND 20170831
                                  THEN i.Price ELSE 0 END), 2) AS GMV2017JanAug,
                   ROUND(SUM(CASE WHEN i.PurchaseDateKey BETWEEN 20180101 AND 20180831
                                  THEN i.Price ELSE 0 END), 2) AS GMV2018JanAug
            FROM FactOrderItem i
            JOIN DimProduct p ON p.ProductKey = i.ProductKey
            JOIN DimCategory c ON c.CategoryKey = p.CategoryKey
            GROUP BY c.CategoryName
        ), order_review AS (
            SELECT DISTINCT c.CategoryName, i.OrderId, o.ReviewScore, o.PurchaseDateKey
            FROM FactOrderItem i
            JOIN FactOrderDelivery o ON o.OrderId = i.OrderId
            JOIN DimProduct p ON p.ProductKey = i.ProductKey
            JOIN DimCategory c ON c.CategoryKey = p.CategoryKey
            WHERE o.ReviewScore IS NOT NULL
        ), reviews AS (
            SELECT CategoryName, COUNT(*) AS ReviewedOrders,
                   ROUND(AVG(ReviewScore), 3) AS AvgReview,
                   SUM(PurchaseDateKey BETWEEN 20180101 AND 20180831) AS ReviewedOrders2018JanAug,
                   ROUND(AVG(CASE WHEN PurchaseDateKey BETWEEN 20180101 AND 20180831
                                  THEN ReviewScore END), 3) AS AvgReview2018JanAug
            FROM order_review GROUP BY CategoryName
        )
        SELECT s.*, r.ReviewedOrders, r.AvgReview,
               r.ReviewedOrders2018JanAug, r.AvgReview2018JanAug,
               ROUND((s.GMV2018JanAug / NULLIF(s.GMV2017JanAug, 0) - 1)*100, 2)
                   AS GMVGrowthPercent
        FROM sales s LEFT JOIN reviews r ON r.CategoryName = s.CategoryName
        ORDER BY s.GMV2018JanAug DESC, s.CategoryName
    """)
    table(categories, out_dir, 'bq4_category_growth_review.csv')
    overall_review_2018 = read(connection, """
        SELECT ROUND(AVG(ReviewScore), 3) AS AvgReview2018JanAug
        FROM FactOrderDelivery
        WHERE PurchaseDateKey BETWEEN 20180101 AND 20180831
          AND ReviewScore IS NOT NULL
          AND EXISTS (SELECT 1 FROM FactOrderItem i
                      WHERE i.OrderId = FactOrderDelivery.OrderId)
    """).iloc[0, 0]
    overall_growth = read(connection, """
        SELECT ROUND(100 * (
          SUM(CASE WHEN PurchaseDateKey BETWEEN 20180101 AND 20180831
                   THEN Price ELSE 0 END) /
          NULLIF(SUM(CASE WHEN PurchaseDateKey BETWEEN 20170101 AND 20170831
                          THEN Price ELSE 0 END), 0) - 1), 2) AS GMVGrowthPercent
        FROM FactOrderItem
    """).iloc[0, 0]
    table(pd.DataFrame([{'OverallGMVGrowthPercent': overall_growth,
                         'OverallAvgReview2018JanAug': overall_review_2018,
                         'MinimumBaseGMV2017': 10000,
                         'MinimumGMV2018': 20000,
                         'MinimumReviewedOrders2018': 100}]),
          out_dir, 'bq4_screening_baseline.csv')
    meaningful = categories[
        (categories.GMV2017JanAug >= 10000) &
        (categories.GMV2018JanAug >= 20000) &
        (categories.ReviewedOrders2018JanAug >= 100)
    ].copy()
    category_candidates = meaningful[
        (meaningful.GMVGrowthPercent > float(overall_growth)) &
        (meaningful.AvgReview2018JanAug < float(overall_review_2018))
    ].sort_values('GMV2018JanAug', ascending=False)
    table(category_candidates, out_dir, 'bq4_category_candidates.csv')
    fig, ax = plt.subplots(figsize=(10, 5.5))
    sizes = np.sqrt(meaningful.GMV2018JanAug.astype(float)) * .6
    ax.scatter(meaningful.GMVGrowthPercent.astype(float),
               meaningful.AvgReview2018JanAug.astype(float), s=sizes, alpha=.50,
               color='#5278af', edgecolors='white')
    ax.axhline(float(overall_review_2018), color='#c95450', linestyle='--', linewidth=1,
               label=f'Overall review Jan–Aug 2018: {float(overall_review_2018):.3f}')
    ax.axvline(float(overall_growth), color='#8a93a3', linestyle=':', linewidth=1,
               label=f'Overall GMV growth: {float(overall_growth):.1f}%')
    ax.set_xlabel('GMV growth, Jan–Aug 2018 vs Jan–Aug 2017 (%)')
    ax.set_ylabel('Average latest review, Jan–Aug 2018')
    ax.set_title('Category growth and review (minimum base and sample applied)')
    ax.legend(loc='lower right')
    chart(fig_dir, 'category_growth_review.png')

    # BQ5: history for forecasting, including sparse edge months in the CSV.
    monthly_business = read(connection, """
        SELECT DATE_FORMAT(d.FullDate, '%Y-%m') AS PurchaseMonth,
               COUNT(*) AS Orders, ROUND(SUM(o.GMV), 2) AS GMV
        FROM FactOrderDelivery o JOIN DimDate d ON d.DateKey = o.PurchaseDateKey
        GROUP BY PurchaseMonth ORDER BY PurchaseMonth
    """)
    table(monthly_business, out_dir, 'bq5_monthly_orders_gmv_all.csv')
    plot_months = monthly_business[
        monthly_business.PurchaseMonth.between('2017-01', '2018-08')
    ]
    fig, left = plt.subplots(figsize=(11, 5))
    right = left.twinx()
    x = np.arange(len(plot_months))
    left.plot(x, plot_months.Orders, color='#5278af', marker='o', markersize=3,
              label='Orders')
    right.plot(x, plot_months.GMV.astype(float)/1e6, color='#c95450', marker='s',
               markersize=3, label='GMV')
    left.set_xticks(x, plot_months.PurchaseMonth, rotation=60, ha='right')
    left.set_ylabel('Orders', color='#5278af')
    right.set_ylabel('GMV (million R$)', color='#c95450')
    left.set_title('Orders and GMV by month — forecast input window')
    chart(fig_dir, 'monthly_orders_gmv.png')

    # Data feasibility: key uniqueness, repeats, milestone order, missing dates.
    quality = read(connection, """
        SELECT 'review_rows' AS Metric, COUNT(*) AS Value FROM stg_Reviews
        UNION ALL SELECT 'distinct_review_id', COUNT(DISTINCT review_id) FROM stg_Reviews
        UNION ALL SELECT 'distinct_review_id_order_id', COUNT(DISTINCT review_id,order_id) FROM stg_Reviews
        UNION ALL SELECT 'distinct_reviewed_orders', COUNT(DISTINCT order_id) FROM stg_Reviews
        UNION ALL SELECT 'distinct_customer_id', COUNT(DISTINCT customer_id) FROM stg_Customers
        UNION ALL SELECT 'distinct_customer_unique_id', COUNT(DISTINCT customer_unique_id) FROM stg_Customers
        UNION ALL SELECT 'delivered_missing_actual_or_estimate',
            SUM(order_status='delivered' AND
                (order_delivered_customer_date='' OR order_estimated_delivery_date='')) FROM stg_Orders
        UNION ALL SELECT 'delivered_before_purchase',
            SUM(order_delivered_customer_date<>'' AND
                order_delivered_customer_date<order_purchase_timestamp) FROM stg_Orders
        UNION ALL SELECT 'carrier_before_approval',
            SUM(order_delivered_carrier_date<>'' AND order_approved_at<>'' AND
                order_delivered_carrier_date<order_approved_at) FROM stg_Orders
        UNION ALL SELECT 'delivered_before_carrier',
            SUM(order_delivered_customer_date<>'' AND order_delivered_carrier_date<>'' AND
                order_delivered_customer_date<order_delivered_carrier_date) FROM stg_Orders
    """)
    table(quality, out_dir, 'eda_key_time_quality.csv')
    repeat_customers = read(connection, """
        SELECT COUNT(*) AS UniqueCustomers,
               SUM(OrderCount > 1) AS RepeatCustomers,
               SUM(CASE WHEN OrderCount > 1 THEN OrderCount ELSE 0 END) AS OrdersFromRepeatCustomers,
               MAX(OrderCount) AS MaxOrdersPerCustomer
        FROM (
            SELECT c.customer_unique_id, COUNT(*) AS OrderCount
            FROM stg_Orders o JOIN stg_Customers c ON c.customer_id=o.customer_id
            GROUP BY c.customer_unique_id
        ) x
    """)
    table(repeat_customers, out_dir, 'eda_repeat_customers.csv')

    # Promise buffer: enough to inspect whether the estimated date is broad,
    # without claiming that the calendar span equals actual processing effort.
    promise = read(connection, """
        SELECT o.DeliveryDays AS ActualDays,
               DATEDIFF(e.FullDate, p.FullDate) AS PromisedDays,
               DATEDIFF(e.FullDate, a.FullDate) AS DaysEarly
        FROM FactOrderDelivery o
        JOIN DimDate p ON p.DateKey=o.PurchaseDateKey
        JOIN DimDate e ON e.DateKey=o.EstimatedDeliveryDateKey
        JOIN DimDate a ON a.DateKey=o.DeliveredDateKey
        WHERE o.IsOnTime IS NOT NULL
    """)
    promise = promise.apply(pd.to_numeric, errors='coerce')
    promise.describe(percentiles=[.25, .5, .75, .9]).T.to_csv(
        out_dir / 'eda_promise_actual_summary.csv', encoding='utf-8-sig')
    fig, ax = plt.subplots(figsize=(9, 5))
    bins = np.arange(0, 81, 3)
    ax.hist(promise.PromisedDays.clip(0, 80), bins=bins, alpha=.55,
            label='Promised days', color='#5278af')
    ax.hist(promise.ActualDays.clip(0, 80), bins=bins, alpha=.55,
            label='Actual delivery days', color='#e99a66')
    ax.set_xlabel('Days from purchase (values >80 clipped for display)')
    ax.set_ylabel('Orders')
    ax.set_title('Promised versus actual delivery duration')
    ax.legend()
    chart(fig_dir, 'promise_vs_actual_days.png')

    # Distance uses zip-centroid coordinates and single-seller orders only.
    distance = read(connection, """
        SELECT o.OrderId, o.DeliveryDays, o.FreightValue,
               cg.Latitude AS CustomerLat, cg.Longitude AS CustomerLng,
               sg.Latitude AS SellerLat, sg.Longitude AS SellerLng
        FROM FactOrderDelivery o
        JOIN DimCustomer c ON c.CustomerKey=o.CustomerKey
        JOIN DimGeography cg ON cg.GeographyKey=c.GeographyKey
        JOIN (
            SELECT OrderId, MIN(SellerKey) AS SellerKey
            FROM FactOrderItem GROUP BY OrderId HAVING COUNT(DISTINCT SellerKey)=1
        ) one_seller ON one_seller.OrderId=o.OrderId
        JOIN DimSeller s ON s.SellerKey=one_seller.SellerKey
        JOIN DimGeography sg ON sg.GeographyKey=s.GeographyKey
        WHERE o.IsOnTime IS NOT NULL AND o.DeliveryDays >= 0
          AND cg.Latitude IS NOT NULL AND cg.Longitude IS NOT NULL
          AND sg.Latitude IS NOT NULL AND sg.Longitude IS NOT NULL
    """)
    for name in ['DeliveryDays', 'FreightValue', 'CustomerLat', 'CustomerLng',
                 'SellerLat', 'SellerLng']:
        distance[name] = pd.to_numeric(distance[name], errors='coerce')
    rad = np.pi / 180
    lat1, lng1 = distance.CustomerLat*rad, distance.CustomerLng*rad
    lat2, lng2 = distance.SellerLat*rad, distance.SellerLng*rad
    hav = np.sin((lat2-lat1)/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin((lng2-lng1)/2)**2
    distance['ApproxKm'] = 6371 * 2 * np.arcsin(np.sqrt(np.clip(hav, 0, 1)))
    distance = distance[distance.ApproxKm.between(0, 5000)].copy()
    distance['DistanceBand'] = pd.cut(
        distance.ApproxKm, [-1, 100, 300, 600, 1000, 2000, 5000],
        labels=['0–100', '101–300', '301–600', '601–1000', '1001–2000', '>2000'])
    dist_summary = (distance.groupby('DistanceBand', observed=True)
                    .agg(Orders=('OrderId', 'nunique'),
                         MedianApproxKm=('ApproxKm', 'median'),
                         AvgFreightCharged=('FreightValue', 'mean'),
                         AvgDeliveryDays=('DeliveryDays', 'mean'))
                    .reset_index())
    table(dist_summary, out_dir, 'eda_distance_freight_delivery.csv')
    fig, left = plt.subplots(figsize=(9, 5))
    right = left.twinx()
    x = np.arange(len(dist_summary))
    left.plot(x, dist_summary.AvgFreightCharged, color='#5278af', marker='o')
    right.plot(x, dist_summary.AvgDeliveryDays, color='#c95450', marker='s')
    left.set_xticks(x, dist_summary.DistanceBand.astype(str))
    left.set_xlabel('Approximate straight-line km, zip centroids')
    left.set_ylabel('Average freight charged (R$)', color='#5278af')
    right.set_ylabel('Average delivery days', color='#c95450')
    left.set_title('Distance proxy, freight charge and delivery time')
    chart(fig_dir, 'distance_freight_delivery.png')

    assert int(monthly_delivery.LateOrders.sum()) == 6534
    assert int(monthly_delivery.EligibleOrders.sum()) == 96470
    assert int(delay_review.EligibleOrders.sum()) == 96470
    assert int(monthly_business.Orders.sum()) == 99441
    assert abs(float(monthly_business.GMV.sum()) - 13591643.70) < .01
    return {
        'state_month_cells': len(state_month),
        'sellers': len(sellers),
        'categories': len(categories),
        'repeat_customers': int(repeat_customers.RepeatCustomers.iloc[0]),
        'distance_orders': len(distance),
        'promise_median': float(promise.PromisedDays.median()),
        'actual_median': float(promise.ActualDays.median()),
    }
