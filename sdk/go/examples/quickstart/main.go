// Quickstart example for the memoria-nox Go client.
//
// Usage:
//
//	NOX_API_TOKEN=<token> go run ./sdk/go/examples/quickstart
package main

import (
	"context"
	"fmt"
	"os"
	"time"

	noxmem "github.com/totobusnello/memoria-nox/sdk/go"
)

func main() {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	client := noxmem.New(noxmem.Config{
		BaseURL:   getenv("NOX_API_URL", "http://127.0.0.1:18802"),
		AuthToken: os.Getenv("NOX_API_TOKEN"),
	})

	// ── Health check ──────────────────────────────────────────────────────────
	health, err := client.Health(ctx)
	if err != nil {
		fatalf("health: %v", err)
	}
	if health.Chunks != nil {
		fmt.Printf("Chunks total: %d\n", health.Chunks.Total)
	}
	if health.VectorCoverage != nil {
		vc := health.VectorCoverage
		fmt.Printf("Vector coverage: %d/%d (orphans: %d)\n", vc.Embedded, vc.Total, vc.Orphans)
	}

	// ── Hybrid search ─────────────────────────────────────────────────────────
	limit := 5
	results, err := client.Search(ctx, "Gemini quota exceeded nightly cron", &noxmem.SearchOptions{Limit: &limit})
	if err != nil {
		fatalf("search: %v", err)
	}
	fmt.Printf("\nTop search results (%d):\n", len(results))
	for _, r := range results {
		snippet := r.Content
		if len(snippet) > 80 {
			snippet = snippet[:80]
		}
		typ := r.ChunkType
		if typ == "" {
			typ = "?"
		}
		fmt.Printf("  [%.3f] %s (%s)\n", r.Score, snippet, typ)
	}

	// ── Knowledge graph ───────────────────────────────────────────────────────
	kg, err := client.KG(ctx)
	if err != nil {
		fatalf("kg: %v", err)
	}
	fmt.Printf("\nKG: %d entities, %d relations\n", len(kg.Entities), len(kg.Relations))

	// ── Reflect ───────────────────────────────────────────────────────────────
	fmt.Println("\nReflection query: 'what are recurring production incidents?'")
	reflection, err := client.Reflect(ctx, "what are recurring production incidents?", false)
	if err != nil {
		apiErr, ok := err.(*noxmem.APIError)
		if ok && apiErr.IsFeatureDisabled() {
			fmt.Println("(reflect feature disabled)")
		} else {
			fatalf("reflect: %v", err)
		}
	} else {
		fmt.Printf("Reflect result keys: %d\n", len(reflection))
	}

	fmt.Println("\nDone.")
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func fatalf(format string, args ...interface{}) {
	fmt.Fprintf(os.Stderr, "ERROR: "+format+"\n", args...)
	os.Exit(1)
}
