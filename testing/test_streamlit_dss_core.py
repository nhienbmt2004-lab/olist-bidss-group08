"""As-of, one-order GMV and map aggregation checks for the replay DSS."""

import sys
import unittest
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from streamlit_dss_core import (customer_geohash_points, geohash_bounds,
                                geohash_encode, prepare_orders, route_metrics)  # noqa: E402


class ReplayDSSCoreTests(unittest.TestCase):
    def test_customer_coordinate_lies_inside_rendered_geohash_cell(self):
        latitude, longitude = -22.9, -43.2
        south, west, north, east = geohash_bounds(geohash_encode(latitude, longitude))
        self.assertLessEqual(south, latitude)
        self.assertLess(latitude, north)
        self.assertLessEqual(west, longitude)
        self.assertLess(longitude, east)

    def test_only_observed_delivery_counts_in_otd_and_gmv_is_order_grain(self):
        clock = datetime(2018, 7, 15, 12)
        events = pd.DataFrame([
            dict(OrderId="one", PurchaseAt="2018-07-01", ApprovedAt="2018-07-01",
                 CarrierAt="2018-07-02", DeliveredAt="2018-07-10",
                 EstimatedAt="2018-07-09", LastEventAt="2018-07-10",
                 CurrentStage="Delivered"),
            dict(OrderId="two", PurchaseAt="2018-07-10", ApprovedAt="2018-07-10",
                 CarrierAt="2018-07-11", DeliveredAt=None,
                 EstimatedAt="2018-07-13", LastEventAt="2018-07-11",
                 CurrentStage="In transit"),
            dict(OrderId="three", PurchaseAt="2018-07-10", ApprovedAt="2018-07-10",
                 CarrierAt=None, DeliveredAt=None,
                 EstimatedAt="2018-07-25", LastEventAt="2018-07-10",
                 CurrentStage="Awaiting carrier"),
            dict(OrderId="multi", PurchaseAt="2018-07-10", ApprovedAt="2018-07-10",
                 CarrierAt=None, DeliveredAt=None,
                 EstimatedAt="2018-07-25", LastEventAt="2018-07-10",
                 CurrentStage="Awaiting carrier"),
        ])
        lookup = pd.DataFrame([
            dict(OrderId=oid, GMV=100, SellerCount=1, SellerState="SP",
                 SellerId="seller", CustomerState="RJ",
                 CustomerLatitude=-22.9, CustomerLongitude=-43.2)
            for oid in ("one", "two", "three")
        ] + [dict(OrderId="multi", GMV=999, SellerCount=2, SellerState=None,
                  SellerId=None, CustomerState="RJ", CustomerLatitude=-22.9,
                  CustomerLongitude=-43.2)])
        a = pd.DataFrame({"OrderId": ["one", "two", "three"],
                          "Risk": [.1, .2, .9], "Late": [1, 1, 0]})
        h = pd.DataFrame({"OrderId": ["one", "two"],
                          "HandoverRisk": [.3, .8], "Late": [1, 1]})
        orders = prepare_orders(events, lookup, a, h, clock)
        self.assertEqual(len(orders), 4)
        self.assertEqual(orders.loc[orders.OrderId.eq("two"), "AvailableScore"].iloc[0], .8)
        self.assertTrue(orders.loc[orders.OrderId.eq("two"), "Overdue"].iloc[0])
        route = route_metrics(orders, clock, min_delivered=1).iloc[0]
        self.assertEqual(route.Delivered14d, 1)
        self.assertEqual(route.OnTime14d, 0)
        self.assertEqual(route.OpenOrders, 2)
        self.assertEqual(route.OpenGMVAtRisk, 200)
        self.assertEqual(route.OrdersSeen, 3)
        points = customer_geohash_points(orders)
        self.assertEqual(points.Orders.sum(), 3)
        self.assertEqual(len(points), 1)

    def test_future_event_is_rejected(self):
        events = pd.DataFrame([dict(OrderId="x", LastEventAt="2018-07-16",
            PurchaseAt="2018-07-10", ApprovedAt=None, CarrierAt=None,
            DeliveredAt=None, EstimatedAt="2018-07-20", CurrentStage="Awaiting approval")])
        lookup = pd.DataFrame([dict(OrderId="x", GMV=10, SellerCount=1,
            SellerState="SP", SellerId="s", CustomerState="RJ",
            CustomerLatitude=-22, CustomerLongitude=-43)])
        empty_a = pd.DataFrame(columns=["OrderId", "Risk"])
        empty_h = pd.DataFrame(columns=["OrderId", "HandoverRisk"])
        with self.assertRaises(ValueError):
            prepare_orders(events, lookup, empty_a, empty_h, datetime(2018, 7, 15))


if __name__ == "__main__":
    unittest.main()
