/**
 * typescript-quickstart.ts
 *
 * 30-line example: answer + export + viewer SSE stream.
 * Prerequisites: Node 18+, NOX_ANSWER_ENABLED=1, NOX_ARCHIVE_ENABLED=1
 *
 * Run: npx tsx sdk/examples/typescript-quickstart.ts
 */

import { NoxMemClient, NoxMemApiError } from "@nox-mem/client";
import { writeFileSync } from "node:fs";

const client = new NoxMemClient({
  baseUrl: process.env.NOX_API_URL ?? "http://127.0.0.1:18802",
  authToken: process.env.NOX_API_TOKEN,
});

// 1. Health check
const health = await client.health();
console.log(`Chunks: ${health.chunks?.total ?? 0}, DB: ${health.dbSizeMB ?? 0} MB`);

// 2. Hybrid search
const results = await client.search("Gemini quota exceeded cron", { limit: 3 });
for (const r of results) {
  console.log(`  [${r.score?.toFixed(3)}] ${r.content?.slice(0, 80)}...`);
}

// 3. Answer with citations (requires NOX_ANSWER_ENABLED=1)
try {
  const { answer, citations } = await client.answer(
    "What is the correct way to reapply the monkey-patch after upgrading OpenClaw?",
    { top_k: 8 },
  );
  console.log("\nAnswer:", answer.slice(0, 200));
  console.log(`Citations: ${citations.length}`);
} catch (e) {
  if (e instanceof NoxMemApiError && e.isFeatureDisabled) {
    console.log("Answer feature not enabled (NOX_ANSWER_ENABLED=1 required)");
  } else throw e;
}

// 4. Export archive (requires NOX_ARCHIVE_ENABLED=1)
try {
  const archive = await client.export({ format: "tar", exclude_embeddings: true });
  writeFileSync("/tmp/nox-mem-export.tar.gz", Buffer.from(await archive.arrayBuffer()));
  console.log("Exported archive to /tmp/nox-mem-export.tar.gz");
} catch (e) {
  if (e instanceof NoxMemApiError && e.isFeatureDisabled) {
    console.log("Archive feature not enabled (NOX_ARCHIVE_ENABLED=1 required)");
  } else throw e;
}

// 5. SSE viewer stream (requires NOX_VIEWER_ENABLED=1)
try {
  const controller = new AbortController();
  setTimeout(() => controller.abort(), 3000); // listen for 3 seconds

  console.log("Listening to SSE stream for 3 seconds...");
  for await (const event of client.streamEvents(controller.signal)) {
    console.log(`  SSE: ${event.kind} @ ${event.ts}`);
  }
} catch (e) {
  if (e instanceof NoxMemApiError && e.isFeatureDisabled) {
    console.log("Viewer feature not enabled (NOX_VIEWER_ENABLED=1 required)");
  } else if ((e as Error).name === "AbortError") {
    console.log("SSE stream closed after timeout");
  } else throw e;
}
