import sqlite3
import unittest
from probe.briefs import db_agent, brief_at, brief_by_generated_at, brief_items, candidate_briefs, iso_to_db


def fixture():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE brief_log (id INTEGER PRIMARY KEY, chunk_id INTEGER, scope TEXT, agent TEXT, served_at TEXT, brief_id TEXT)")
    rows = [
        # cycle 1 at 10:07 — refresh order: main (agent=nox), nox, boris
        ("nox", "2026-10-01 10:07:01", "m1", [1, 2]), ("nox", "2026-10-01 10:07:01", "n1", [3, 4]),
        ("boris", "2026-10-01 10:07:02", "b1", [5]),
        # cycle 2 at 10:22
        ("nox", "2026-10-01 10:22:01", "m2", [6]), ("nox", "2026-10-01 10:22:02", "n2", [7]),
        ("boris", "2026-10-01 10:22:02", "b2", [8]), ("forge", "2026-10-03 10:22:02", "f1", [9]),
    ]
    for agent, ts, bid, ids in rows:
        for cid in ids:
            con.execute("INSERT INTO brief_log (chunk_id, scope, agent, served_at, brief_id) VALUES (?,?,?,?,?)",
                        (cid, "global", agent, ts, bid))
    return con


class BriefsTest(unittest.TestCase):
    def test_main_maps_to_nox(self):
        self.assertEqual(db_agent("main"), "nox")
        self.assertEqual(db_agent("boris"), "boris")

    def test_main_gets_earlier_and_nox_later_of_the_pair(self):
        con = fixture()
        self.assertEqual(brief_at(con, "main", "2026-10-01 10:15:00")["brief_id"], "m1")
        self.assertEqual(brief_at(con, "nox", "2026-10-01 10:15:00")["brief_id"], "n1")
        self.assertEqual(brief_at(con, "boris", "2026-10-01 10:30:00")["brief_id"], "b2")
        self.assertIsNone(brief_at(con, "boris", "2026-10-01 09:00:00"))

    def test_items_keep_served_order(self):
        self.assertEqual(brief_items(fixture(), "m1"), [1, 2])

    def test_generated_at_lookup_pairs_main_and_nox(self):
        con = fixture()
        self.assertEqual(brief_by_generated_at(con, "main", "2026-10-01T10:22:01.400Z"), "m2")
        self.assertEqual(brief_by_generated_at(con, "nox", "2026-10-01T10:22:01.900Z"), "n2")

    def test_candidates_exclude_owner_and_respect_window(self):
        con = fixture()
        c = candidate_briefs(con, "boris", "2026-10-01 10:30:00", seed=1)
        self.assertNotIn("b1", c)
        self.assertNotIn("b2", c)
        self.assertIn("m2", c)
        self.assertIn("f1", c)  # 2 days later, inside ±3 d
        self.assertEqual(c, candidate_briefs(con, "boris", "2026-10-01 10:30:00", seed=1))

    def test_iso_to_db(self):
        self.assertEqual(iso_to_db("2026-10-01T10:22:01.400Z"), "2026-10-01 10:22:01")


if __name__ == "__main__":
    unittest.main()
