package examples;

import com.noxmem.client.NoxMemClient;
import com.noxmem.client.types.Types.*;

import java.util.List;

/**
 * Quick-start example for the noxmem-client Java SDK.
 *
 * Run from the sdk/java directory:
 *   mvn compile exec:java -Dexec.mainClass=examples.QuickStart
 *
 * Environment variables:
 *   NOX_API_URL   — base URL (default http://127.0.0.1:18802)
 *   NOX_API_TOKEN — Bearer token (only required if server has NOX_API_TOKEN set)
 */
public class QuickStart {

    public static void main(String[] args) throws Exception {
        String baseUrl = System.getenv().getOrDefault("NOX_API_URL", "http://127.0.0.1:18802");
        String token   = System.getenv("NOX_API_TOKEN"); // nullable

        try (NoxMemClient client = new NoxMemClient(baseUrl, token)) {

            // ── 1. Health check ──────────────────────────────────────────────
            HealthResponse health = client.health();
            System.out.printf("Chunks: %d | DB: %.1f MB%n",
                health.chunks().total(), health.dbSizeMB());

            // ── 2. Hybrid search ─────────────────────────────────────────────
            String searchRaw = client.searchRaw("Gemini quota exceeded nightly cron", 5, null, null);
            System.out.println("Search results (raw JSON, first 200 chars):");
            System.out.println(searchRaw.substring(0, Math.min(200, searchRaw.length())));

            // ── 3. Reflect ───────────────────────────────────────────────────
            ReflectResult reflect = client.reflect("what are my recurring production incidents?", false);
            System.out.println("Reflection: " + reflect.synthesis());

            // ── 4. Crystallize a procedure ───────────────────────────────────
            CrystallizeResult cr = client.crystallize(new CrystallizeRequest(
                "Example procedure via Java SDK",
                List.of("Step 1: verify env", "Step 2: run script"),
                "forge",
                List.of("example")
            ));
            System.out.printf("Crystallized procedure id=%d ok=%b%n", cr.id(), cr.ok());

            // ── 5. Mark a chunk (L3) ─────────────────────────────────────────
            // MarkResult mark = client.markChunk(41203, "canonical", "Verified correct");
            // System.out.println("Mark applied: " + mark.ok());

            // ── 6. Answer (P1) — requires NOX_ANSWER_ENABLED=1 ──────────────
            // String answer = client.answerRaw(new AnswerRequest(
            //     "How do I reapply the monkey-patch after upgrading OpenClaw?",
            //     8, null, null, null, null, null, null
            // ));
            // System.out.println("Answer: " + answer);

            // ── 7. SSE stream (P5) — requires NOX_VIEWER_ENABLED=1 ───────────
            // try (var events = client.streamEvents()) {
            //     int count = 0;
            //     for (var event : events) {
            //         System.out.println("Event: " + event.kind() + " @ " + event.ts());
            //         if (++count >= 3) break;
            //     }
            // }
        }
    }
}
