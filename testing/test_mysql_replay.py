"""Check historical event ordering and source snapshot safeguards."""

import sys
import unittest
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from replay_olist_mysql import prepare_events  # noqa: E402


class MySQLReplaySourceTests(unittest.TestCase):
    def test_orders_become_time_ordered_events_without_future_state(self):
        rows = [
            {"order_id": "b" * 32, "order_purchase_timestamp": "2018-07-02 09:00:00",
             "order_approved_at": "2018-07-02 10:00:00",
             "order_delivered_carrier_date": "2018-07-02 08:00:00",
             "order_delivered_customer_date": "2018-07-04 11:00:00",
             "order_estimated_delivery_date": "2018-07-05 00:00:00"},
            {"order_id": "a" * 32, "order_purchase_timestamp": "2018-07-01 09:00:00",
             "order_approved_at": "2018-07-01 10:00:00",
             "order_delivered_carrier_date": "2018-07-03 08:00:00",
             "order_delivered_customer_date": "2018-07-06 11:00:00",
             "order_estimated_delivery_date": "2018-07-05 00:00:00"},
        ]
        events, signature, skipped, count = prepare_events(rows, date(2018, 7, 1), date(2018, 7, 31))
        self.assertEqual((count, len(events), skipped["carrier"]), (2, 7, 1))
        self.assertEqual(events[0][0:2], ("a" * 32, "purchased"))
        self.assertEqual([event[2] for event in events], sorted(event[2] for event in events))
        self.assertTrue(all(event[2] <= datetime(2018, 7, 6, 11) for event in events))
        self.assertEqual(signature, prepare_events(rows, date(2018, 7, 1), date(2018, 7, 31))[1])
        changed = [dict(row) for row in rows]
        changed[0]["order_estimated_delivery_date"] = "2018-07-07 00:00:00"
        self.assertNotEqual(signature, prepare_events(changed, date(2018, 7, 1), date(2018, 7, 31))[1])


if __name__ == "__main__":
    unittest.main()
