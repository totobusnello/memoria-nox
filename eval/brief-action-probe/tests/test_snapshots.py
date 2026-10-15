import unittest
from probe.snapshots import parse_snapshot, build_index, snapshot_at, candidate_items, block, turnover

AUTO = ("<!-- AUTO-GERADO por nox-mem-brief-refresh.sh (cron */15) — NÃO EDITAR.\n"
        "     Session Priming Loop F3 — brief por salience do nox-mem.\n"
        "     Detalhe de qualquer item: nox_mem_search por id/título. -->\n\n")


def snap(agent, gen, ids):
    lines = [f"[lesson|pain 0.4|{i % 9}d] lessons — item number {i} text (chk {i})" for i in ids]
    return AUTO + f"# nox-mem brief — scope=global agent={agent} — {gen} — {len(ids)} items\n" + "\n".join(lines) + "\n"


class SnapshotsTest(unittest.TestCase):
    def test_parse_keeps_text_verbatim_and_items(self):
        t = snap("forge", "2026-10-01T02:00:01.500Z", [5, 6])
        s = parse_snapshot(t)
        self.assertEqual(s["text"], t)
        self.assertEqual(s["generated_at"], "2026-10-01 02:00:01")
        self.assertEqual(s["agent_label"], "forge")
        self.assertEqual([i["id"] for i in s["items"]], [5, 6])
        self.assertEqual(s["items"][0]["text"], "lessons — item number 5 text")
        self.assertIsNone(parse_snapshot("no header here"))

    def test_index_dedupes_and_sorts(self):
        a = snap("forge", "2026-10-01T02:00:00.000Z", [1])
        b = snap("forge", "2026-10-02T02:00:00.000Z", [2])
        idx = build_index([("forge", b), ("forge", a), ("forge", a), ("forge", "garbage")])
        self.assertEqual([s["generated_at"] for s in idx["forge"]], ["2026-10-01 02:00:00", "2026-10-02 02:00:00"])

    def test_snapshot_at_is_latest_not_after_t(self):
        idx = build_index([("forge", snap("forge", "2026-10-01T02:00:00.000Z", [1])),
                           ("forge", snap("forge", "2026-10-02T02:00:00.000Z", [2]))])
        self.assertEqual(snapshot_at(idx, "forge", "2026-10-01 18:00:00")["items"][0]["id"], 1)
        self.assertEqual(snapshot_at(idx, "forge", "2026-10-02 02:00:00")["items"][0]["id"], 2)
        self.assertIsNone(snapshot_at(idx, "forge", "2026-09-30 00:00:00"))

    def test_candidates_exclude_owner_pair_future_and_old(self):
        idx = build_index([
            ("main", snap("nox", "2026-10-05T02:00:00.000Z", [10])),
            ("nox", snap("nox", "2026-10-05T02:00:00.000Z", [11])),
            ("boris", snap("boris", "2026-10-05T02:00:00.000Z", [20])),
            ("boris", snap("boris", "2026-10-04T02:00:00.000Z", [21])),
            ("boris", snap("boris", "2026-10-06T02:00:00.000Z", [22])),   # after t
            ("forge", snap("forge", "2026-09-30T02:00:00.000Z", [30])),   # older than 3 d
            ("forge", snap("forge", "2026-10-03T02:00:00.000Z", [31])),
        ])
        ids = [i["id"] for i in candidate_items(idx, "main", "2026-10-05 12:00:00", seed=1)]
        self.assertNotIn(10, ids)
        self.assertNotIn(11, ids)
        self.assertNotIn(22, ids)
        self.assertNotIn(30, ids)
        self.assertEqual(ids.index(20) + 1, ids.index(21))  # nearest snapshot first within an agent
        self.assertIn(31, ids)
        self.assertEqual(ids, [i["id"] for i in candidate_items(idx, "main", "2026-10-05 12:00:00", seed=1)])

    def test_block_matches_served_shape(self):
        t = snap("forge", "2026-10-01T02:00:01.500Z", [5, 6])
        s = parse_snapshot(t)
        self.assertEqual(block("forge", "global", "2026-10-01T02:00:01.500Z", [i["line"] for i in s["items"]]), t)

    def test_turnover(self):
        a = parse_snapshot(snap("forge", "2026-10-01T02:00:00.000Z", [1, 2, 3, 4]))
        b = parse_snapshot(snap("forge", "2026-10-02T02:00:00.000Z", [1, 2, 3, 9]))
        self.assertAlmostEqual(turnover(a, b), 0.25)


if __name__ == "__main__":
    unittest.main()
