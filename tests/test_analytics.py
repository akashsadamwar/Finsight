from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.analytics import detect_anomalies, get_merchant_summary, query_transactions
from app.seed import seed_database


class AnalyticsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        seed_database(self.db_path, rows=10_000)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_seeded_data_supports_all_three_tools(self) -> None:
        transactions = query_transactions(limit=5, db_path=self.db_path)
        summary = get_merchant_summary(db_path=self.db_path)
        anomalies = detect_anomalies(
            db_path=self.db_path,
            today=datetime.now(timezone.utc).date(),
        )

        self.assertEqual(len(transactions), 5)
        self.assertEqual(len(summary), 8)
        self.assertEqual(sum(row["transaction_count"] for row in summary), 10_000)
        self.assertIn("m_006", {row["merchant_id"] for row in anomalies})

    def test_query_rejects_unbounded_limit(self) -> None:
        with self.assertRaisesRegex(ValueError, "between 1 and 500"):
            query_transactions(limit=501, db_path=self.db_path)


if __name__ == "__main__":
    unittest.main()

