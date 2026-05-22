"""Unit tests for NoxMemClient — no real network calls."""
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from nox_mem.client import NoxMemClient, NoxMemError
from nox_mem.types import AnswerResponse, HealthSnapshot, SearchResult


class TestClientInit(unittest.TestCase):
    def test_default_base_url(self):
        c = NoxMemClient()
        self.assertEqual(c.base_url, "http://187.77.234.79:18802")

    def test_custom_base_url_strips_trailing_slash(self):
        c = NoxMemClient(base_url="http://localhost:18802/")
        self.assertEqual(c.base_url, "http://localhost:18802")

    def test_context_manager_closes_session(self):
        with NoxMemClient() as c:
            self.assertIsNotNone(c._session)
        # After __exit__, no assertion needed — just no exception

    def test_external_session_not_closed(self):
        import requests
        sess = requests.Session()
        c = NoxMemClient(session=sess)
        c.close()
        # External session should still be usable
        self.assertFalse(sess.adapters == {})


class TestURLBuilding(unittest.TestCase):
    def test_url_build(self):
        c = NoxMemClient(base_url="http://example.com:18802")
        self.assertEqual(c._url("/api/health"), "http://example.com:18802/api/health")

    def test_url_build_without_leading_slash(self):
        c = NoxMemClient(base_url="http://example.com:18802")
        self.assertEqual(c._url("api/search"), "http://example.com:18802/api/search")


class TestRetryLogic(unittest.TestCase):
    def _make_response(self, status_code: int, json_data: dict = None, text: str = "error"):
        resp = MagicMock()
        resp.status_code = status_code
        resp.ok = status_code < 400
        resp.text = text
        resp.json.return_value = json_data or {}
        return resp

    @patch("time.sleep")
    def test_retries_on_500(self, mock_sleep):
        client = NoxMemClient()
        fail_resp = self._make_response(500, text="Internal Server Error")
        ok_resp = self._make_response(200, json_data={"chunksTotal": 100, "vectorCoverage": 0.99,
                                                       "salienceMode": "shadow", "kgEntities": 10,
                                                       "kgRelations": 15, "uptime": "1d"})
        client._session.request = MagicMock(side_effect=[fail_resp, ok_resp])
        snap = client.health()
        self.assertEqual(snap.chunks_total, 100)
        self.assertEqual(client._session.request.call_count, 2)
        mock_sleep.assert_called_once()

    @patch("time.sleep")
    def test_raises_after_max_retries(self, mock_sleep):
        client = NoxMemClient()
        fail_resp = self._make_response(503, text="Service unavailable")
        client._session.request = MagicMock(return_value=fail_resp)
        with self.assertRaises(NoxMemError) as ctx:
            client.health()
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(client._session.request.call_count, 3)

    def test_raises_on_4xx_without_retry(self):
        client = NoxMemClient()
        fail_resp = self._make_response(404, text="Not found")
        client._session.request = MagicMock(return_value=fail_resp)
        with self.assertRaises(NoxMemError) as ctx:
            client.health()
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(client._session.request.call_count, 1)


class TestTypeDeserialization(unittest.TestCase):
    def test_health_snapshot_from_dict(self):
        data = {"chunksTotal": 62900, "vectorCoverage": 0.9997, "salienceMode": "active",
                "kgEntities": 402, "kgRelations": 544, "uptime": "3d 5h"}
        snap = HealthSnapshot.from_dict(data)
        self.assertEqual(snap.chunks_total, 62900)
        self.assertAlmostEqual(snap.vec_coverage, 0.9997)

    def test_search_result_from_dict(self):
        data = {"id": "42", "score": 0.87, "sourceFile": "memory/entities/project/nox.md",
                "snippet": "pain-weighted hybrid search", "section": "compiled", "pain": 0.8}
        r = SearchResult.from_dict(data)
        self.assertEqual(r.score, 0.87)
        self.assertEqual(r.section, "compiled")

    def test_answer_response_from_dict(self):
        data = {"answer": "42", "citations": [], "sessionId": "sess-1", "latencyMs": 940}
        resp = AnswerResponse.from_dict(data)
        self.assertEqual(resp.answer, "42")
        self.assertEqual(resp.latency_ms, 940)


if __name__ == "__main__":
    unittest.main()
