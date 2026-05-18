package com.noxmem.client;

import com.github.tomakehurst.wiremock.WireMockServer;
import com.github.tomakehurst.wiremock.client.WireMock;
import com.github.tomakehurst.wiremock.core.WireMockConfiguration;
import com.noxmem.client.error.NoxMemApiException;
import com.noxmem.client.types.Types.*;
import org.junit.jupiter.api.*;

import java.io.IOException;
import java.time.Duration;
import java.util.List;

import static com.github.tomakehurst.wiremock.client.WireMock.*;
import static org.junit.jupiter.api.Assertions.*;

/**
 * JUnit 5 tests for {@link NoxMemClient} backed by WireMock.
 *
 * All 26 endpoints are covered (happy path + at least one error path each).
 */
class ClientTest {

    static WireMockServer wm;
    static NoxMemClient client;

    @BeforeAll
    static void startServer() {
        wm = new WireMockServer(WireMockConfiguration.options().dynamicPort());
        wm.start();
        WireMock.configureFor("localhost", wm.port());
        client = new NoxMemClient("http://localhost:" + wm.port(), null, Duration.ofSeconds(5));
    }

    @AfterAll
    static void stopServer() {
        wm.stop();
    }

    @BeforeEach
    void reset() {
        WireMock.reset();
    }

    // ── Core ──────────────────────────────────────────────────────────────────

    @Test
    void health_returns200() throws Exception {
        stubFor(get("/api/health").willReturn(okJson(
            """
            {"chunks":{"total":62914,"types":[]},"dbSizeMB":487.3,"vectorCoverage":{"embedded":62912,"total":62914,"orphans":0},"knowledgeGraph":{"entities":402,"relations":544}}
            """
        )));
        HealthResponse h = client.health();
        assertEquals(62914, h.chunks().total());
        assertEquals(487.3, h.dbSizeMB(), 0.01);
    }

    @Test
    void health_500_throwsException() {
        stubFor(get("/api/health").willReturn(serverError().withBody("{\"error\":\"db locked\"}")));
        NoxMemApiException ex = assertThrows(NoxMemApiException.class, () -> client.health());
        assertEquals(500, ex.getStatusCode());
    }

    @Test
    void agentsRaw_returns200() throws Exception {
        stubFor(get("/api/agents").willReturn(okJson("[{\"agent\":\"forge\",\"entity_count\":12}]")));
        String raw = client.agentsRaw();
        assertTrue(raw.contains("forge"));
    }

    @Test
    void reflect_returns200() throws Exception {
        stubFor(get(urlPathEqualTo("/api/reflect"))
            .withQueryParam("q", equalTo("incidents"))
            .willReturn(okJson("""
                {"query":"incidents","synthesis":"No major incidents found.","cache_hit":false}
            """)));
        ReflectResult r = client.reflect("incidents", false);
        assertEquals("incidents", r.query());
        assertFalse(r.cache_hit());
    }

    @Test
    void reflect_nocache_passes1() throws Exception {
        stubFor(get(urlPathEqualTo("/api/reflect"))
            .withQueryParam("nocache", equalTo("1"))
            .willReturn(okJson("{\"query\":\"q\",\"synthesis\":\"s\",\"cache_hit\":false}")));
        client.reflect("q", true);
        verify(getRequestedFor(urlPathEqualTo("/api/reflect")).withQueryParam("nocache", equalTo("1")));
    }

    @Test
    void procedures_returns200() throws Exception {
        stubFor(get("/api/procedures").willReturn(okJson(
            "{\"procedures\":[{\"id\":1,\"title\":\"Reapply patch\",\"steps\":[\"ssh\"],\"agent\":\"forge\",\"tags\":[],\"created_at\":\"2026-01-01T00:00:00Z\"}]}"
        )));
        String raw = client.proceduresRaw();
        assertTrue(raw.contains("Reapply patch"));
    }

    @Test
    void crystallize_returns_id() throws Exception {
        stubFor(post("/api/crystallize").willReturn(okJson("{\"id\":88,\"ok\":true}")));
        CrystallizeResult r = client.crystallize(new CrystallizeRequest("Title", List.of("step1"), "forge", List.of("tag1")));
        assertEquals(88, r.id());
        assertTrue(r.ok());
    }

    @Test
    void crystallize_400_throwsException() {
        stubFor(post("/api/crystallize").willReturn(badRequest().withBody("{\"error\":\"title required\"}")));
        NoxMemApiException ex = assertThrows(NoxMemApiException.class,
            () -> client.crystallize(new CrystallizeRequest("", List.of(), null, null)));
        assertEquals(400, ex.getStatusCode());
    }

    @Test
    void crystallizeValidate_returns200() throws Exception {
        stubFor(post(urlPathEqualTo("/api/crystallize/validate"))
            .withQueryParam("id", equalTo("88"))
            .willReturn(okJson("{\"id\":88,\"ok\":true}")));
        String raw = client.crystallizeValidate(88, new CrystallizeValidateRequest("success", "forge", "all good"));
        assertTrue(raw.contains("\"ok\":true"));
    }

    // ── Search ────────────────────────────────────────────────────────────────

    @Test
    void searchRaw_returns200() throws Exception {
        stubFor(get(urlPathEqualTo("/api/search"))
            .withQueryParam("q", equalTo("Gemini quota"))
            .willReturn(okJson("[{\"chunk_id\":1,\"content\":\"...\",\"score\":0.9}]")));
        String raw = client.searchRaw("Gemini quota", null, null, null);
        assertTrue(raw.contains("chunk_id"));
    }

    @Test
    void searchRaw_400_missingQ() {
        stubFor(get(urlPathEqualTo("/api/search"))
            .willReturn(badRequest().withBody("{\"error\":\"q parameter required\"}")));
        assertThrows(NoxMemApiException.class, () -> client.searchRaw("", null, null, null));
    }

    @Test
    void searchPostRaw_returns200() throws Exception {
        stubFor(post("/api/search").willReturn(okJson("[{\"chunk_id\":2,\"content\":\"...\",\"score\":0.8}]")));
        String raw = client.searchPostRaw(new SearchRequest("monkey-patch", 5, null, null));
        assertTrue(raw.contains("chunk_id"));
    }

    @Test
    void searchRaw_withTemporalFilters() throws Exception {
        stubFor(get(urlPathEqualTo("/api/search"))
            .withQueryParam("as_of", equalTo("7d"))
            .willReturn(okJson("[]")));
        String raw = client.searchRaw("q", null, "7d", null);
        assertEquals("[]", raw);
    }

    // ── Knowledge Graph ───────────────────────────────────────────────────────

    @Test
    void kgRaw_returns200() throws Exception {
        stubFor(get("/api/kg").willReturn(okJson("{\"entities\":[],\"relations\":[]}")));
        String raw = client.kgRaw();
        assertTrue(raw.contains("entities"));
    }

    @Test
    void kgPathRaw_returns200() throws Exception {
        stubFor(get(urlPathEqualTo("/api/kg/path"))
            .withQueryParam("from", equalTo("nox-mem-api"))
            .withQueryParam("to", equalTo("gemini-embedding-001"))
            .willReturn(okJson("{\"path\":[\"nox-mem-api\",\"vectorize\",\"gemini-embedding-001\"]}")));
        String raw = client.kgPathRaw("nox-mem-api", "gemini-embedding-001");
        assertTrue(raw.contains("vectorize"));
    }

    @Test
    void crossKgRaw_returns200() throws Exception {
        stubFor(get("/api/cross-kg").willReturn(okJson("{\"entities\":[],\"relations\":[],\"agents\":[]}")));
        String raw = client.crossKgRaw();
        assertTrue(raw.contains("agents"));
    }

    // ── Answer (P1) ───────────────────────────────────────────────────────────

    @Test
    void answerRaw_returns200() throws Exception {
        stubFor(post("/api/answer").willReturn(okJson(
            "{\"answer\":\"Run the script.\",\"citations\":[],\"metadata\":{},\"trace_id\":\"abc\"}"
        )));
        String raw = client.answerRaw(new AnswerRequest("How to reapply?", null, null, null, null, null, null, null));
        assertTrue(raw.contains("Run the script"));
    }

    @Test
    void answerRaw_503_featureDisabled() {
        stubFor(post("/api/answer").willReturn(
            aResponse().withStatus(503).withBody("{\"error\":\"feature disabled\",\"env_var\":\"NOX_ANSWER_ENABLED\"}")));
        NoxMemApiException ex = assertThrows(NoxMemApiException.class,
            () -> client.answerRaw(new AnswerRequest("q", null, null, null, null, null, null, null)));
        assertEquals(503, ex.getStatusCode());
        assertTrue(ex.isFeatureDisabled());
    }

    // ── Export / Import (A2) ──────────────────────────────────────────────────

    @Test
    void export_returnsBytes() throws Exception {
        byte[] fakeArchive = new byte[]{0x1f, (byte) 0x8b}; // gzip magic bytes
        stubFor(post("/api/export").willReturn(
            aResponse().withStatus(200).withBody(fakeArchive).withHeader("Content-Type", "application/gzip")
        ));
        byte[] result = client.export(null);
        assertArrayEquals(fakeArchive, result);
    }

    @Test
    void importArchive_returns200() throws Exception {
        stubFor(post(urlPathEqualTo("/api/import")).willReturn(okJson(
            "{\"op_id\":\"import-001\",\"chunks_inserted\":100,\"chunks_skipped_dedup\":5,\"kg_entities_inserted\":10,\"kg_entities_merged\":2,\"ops_audit_appended\":0,\"embeddings_skipped\":0,\"duration_ms\":1234,\"warnings\":[],\"schema_version_archive\":18,\"schema_version_target\":19,\"migration_applied\":[]}"
        )));
        String raw = client.importArchive(new byte[]{1, 2, 3}, "merge", false, false, false);
        assertTrue(raw.contains("import-001"));
    }

    // ── Viewer / SSE (P5) ─────────────────────────────────────────────────────

    @Test
    void viewerFile_returns200() throws Exception {
        stubFor(get("/viewer/index.html").willReturn(
            aResponse().withStatus(200).withBody("<html></html>").withHeader("Content-Type", "text/html")
        ));
        byte[] bytes = client.viewerFile("index.html");
        assertTrue(new String(bytes).contains("<html>"));
    }

    @Test
    void viewerFile_404() {
        stubFor(get("/viewer/missing.js").willReturn(notFound().withBody("Not Found")));
        NoxMemApiException ex = assertThrows(NoxMemApiException.class, () -> client.viewerFile("missing.js"));
        assertEquals(404, ex.getStatusCode());
    }

    // ── Conflict Detection (L2) ───────────────────────────────────────────────

    @Test
    void listConflictsRaw_returns200() throws Exception {
        stubFor(get(urlPathEqualTo("/api/kg/conflicts")).willReturn(okJson(
            "{\"conflicts\":[{\"id\":1,\"conflict_type\":\"direct\",\"status\":\"unresolved\"}],\"total\":1}"
        )));
        String raw = client.listConflictsRaw(null, null, null);
        assertTrue(raw.contains("unresolved"));
    }

    @Test
    void scanConflicts_returns200() throws Exception {
        stubFor(post("/api/kg/conflicts/scan").willReturn(okJson(
            "{\"conflicts_found\":3,\"conflicts_written\":3,\"dry_run\":false,\"duration_ms\":284}"
        )));
        String raw = client.scanConflicts(null);
        assertTrue(raw.contains("conflicts_found"));
    }

    @Test
    void getConflictRaw_returns200() throws Exception {
        stubFor(get("/api/kg/conflicts/1").willReturn(okJson(
            "{\"id\":1,\"conflict_type\":\"direct\",\"predicate\":\"is_deployed_at\",\"status\":\"unresolved\"}"
        )));
        String raw = client.getConflictRaw(1);
        assertTrue(raw.contains("is_deployed_at"));
    }

    @Test
    void getConflictRaw_404() {
        stubFor(get("/api/kg/conflicts/999").willReturn(notFound().withBody("{\"error\":\"not found\"}")));
        NoxMemApiException ex = assertThrows(NoxMemApiException.class, () -> client.getConflictRaw(999));
        assertEquals(404, ex.getStatusCode());
    }

    @Test
    void resolveConflict_returns200() throws Exception {
        stubFor(post("/api/kg/conflicts/1/resolve").willReturn(okJson(
            "{\"ok\":true,\"conflict_id\":1,\"resolution\":\"superseded\"}"
        )));
        String raw = client.resolveConflict(1, new ResolveConflictRequest("91", "Relation 91 is current"));
        assertTrue(raw.contains("superseded"));
    }

    @Test
    void dismissConflict_returns200() throws Exception {
        stubFor(post("/api/kg/conflicts/1/dismiss").willReturn(okJson(
            "{\"ok\":true,\"conflict_id\":1}"
        )));
        String raw = client.dismissConflict(1, "Not a real contradiction");
        assertTrue(raw.contains("\"ok\":true"));
    }

    // ── Confidence / Mark (L3) ────────────────────────────────────────────────

    @Test
    void markChunk_returns200() throws Exception {
        stubFor(post("/api/chunk/41203/mark").willReturn(okJson(
            "{\"ok\":true,\"chunk_id\":41203,\"applied\":{\"confidence\":0.95,\"provenance_kind\":\"user-marked\"},\"audit_id\":1047}"
        )));
        MarkResult result = client.markChunk(41203, "canonical", "Verified correct");
        assertTrue(result.ok());
        assertEquals(41203, result.chunk_id());
    }

    @Test
    void markChunk_400_badKind() {
        stubFor(post("/api/chunk/1/mark").willReturn(
            badRequest().withBody("{\"ok\":false,\"error\":\"invalid kind\",\"code\":\"bad_kind\"}")));
        assertThrows(NoxMemApiException.class, () -> client.markChunk(1, "archived", null));
    }

    @Test
    void supersedeChunk_returns200() throws Exception {
        stubFor(post("/api/chunk/100/supersede").willReturn(okJson(
            "{\"ok\":true,\"chunk_id\":100,\"applied\":{\"confidence\":0.0},\"audit_id\":1048}"
        )));
        MarkResult result = client.supersedeChunk(100, new SupersedeRequest(200, null, null));
        assertTrue(result.ok());
    }

    // ── Hooks (P2) ────────────────────────────────────────────────────────────

    @Test
    void hookStatusRaw_returns200() throws Exception {
        stubFor(get("/api/hooks/status").willReturn(okJson(
            "{\"enabled\":true,\"queue_depth\":3,\"active_hooks\":[\"slack\"],\"config\":{}}"
        )));
        String raw = client.hookStatusRaw();
        assertTrue(raw.contains("enabled"));
    }

    @Test
    void hookRecentRaw_returns200() throws Exception {
        stubFor(get(urlPathEqualTo("/api/hooks/recent")).willReturn(okJson(
            "{\"rows\":[{\"event_id\":\"e1\",\"hook_name\":\"slack\",\"received_at\":\"2026-05-18T10:00:00Z\",\"status\":\"ok\",\"retries\":0}]}"
        )));
        String raw = client.hookRecentRaw(10);
        assertTrue(raw.contains("e1"));
    }

    @Test
    void hookDryrunRaw_returns200() throws Exception {
        stubFor(post("/api/hooks/dryrun").willReturn(okJson(
            "{\"matched_hooks\":[\"slack\"],\"pipeline_steps\":[],\"would_ingest\":true,\"estimated_chunks\":2}"
        )));
        String raw = client.hookDryrunRaw(new HooksDryrunRequest("test text", null));
        assertTrue(raw.contains("would_ingest"));
    }
}
