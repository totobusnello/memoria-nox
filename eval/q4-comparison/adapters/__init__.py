"""
Q4 COMPARISON adapters — uniform `search()` contract across 6 systems.

Contract (per spec `specs/2026-05-23-Q4-comparison-execution-plan.md` §3):

    def search(query: str, k: int = 10) -> list[dict]:
        # Returns ranked items. Each item: {id, score, text, source}.
        # Latency measured externally (around call).

Each adapter must also expose:

    NAME: str            # display name for output JSON
    VERSION_PIN: str     # exact resolved version (pip/git/docker tag)
    REQUIRES_ENV: list[str]  # mandatory env vars (e.g., ["OPENAI_API_KEY"])
    INSTALL_HINT: str    # one-line install command shown by smoke_test.py

    def validate() -> dict:
        # Returns {ok: bool, error: str | None, version: str | None, notes: str | None}
        # MUST NOT make external network calls (no quota burn during smoke test).
        # Imports + env var checks ONLY.

    def setup() -> None:
        # Idempotent — called by runner before first search.
        # MAY make startup calls (e.g., create Mem0 client, hit /healthz).

    def teardown() -> None:
        # Idempotent — called by runner after the dataset finishes.

Adapter authors: keep `search()` synchronous + side-effect-free beyond the
external system. The runner times the call externally and serializes results
to `output/<system>.json`.
"""

from __future__ import annotations

from typing import Callable, Protocol


class AdapterModule(Protocol):
    """Structural type all adapter modules conform to."""

    NAME: str
    VERSION_PIN: str
    REQUIRES_ENV: list[str]
    INSTALL_HINT: str

    def validate(self) -> dict: ...

    def setup(self) -> None: ...

    def teardown(self) -> None: ...

    def search(self, query: str, k: int = 10) -> list[dict]: ...


SearchFn = Callable[[str, int], list[dict]]

ALL_ADAPTERS: list[str] = [
    "nox_mem",
    "mem0",
    "zep",
    "letta",
    "agentmemory",
    "evermind",
    "hipporag2",
    "lightrag",
]
