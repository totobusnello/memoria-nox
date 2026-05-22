# nox-mem Clients

Official reusable client libraries. Different from `examples/` (those are standalone scripts; these are importable packages developers vendor into their own projects).

- [`python/`](python/) — Python 3.10+ client (`pip install -e python/`)
- [`javascript/`](javascript/) — Node 20+ and browser client (`npm install javascript/`)

## Quick start

The same three calls across both clients:

```python
# Python
from nox_mem import NoxMemClient
c = NoxMemClient()
snap = c.health()
results = c.search("pain-weighted retrieval")
resp = c.answer("What is the salience formula?")
```

```js
// JavaScript (ESM)
import { NoxMemClient } from "@noxmem/client";
const c = new NoxMemClient();
const snap = await c.health();
const results = await c.search("pain-weighted retrieval");
const resp = await c.answer("What is the salience formula?");
```

Both clients:
- Retry 5xx errors automatically (3 attempts, exponential backoff)
- Return typed structures matching the OpenAPI spec at `docs/openapi.yaml`
- Work against any self-hosted nox-mem instance by changing `base_url` / `baseUrl`

## Other languages

Want a Go, Rust, or Ruby client? Open an issue at https://github.com/totobusnello/memoria-nox/issues.

The OpenAPI spec at `docs/openapi.yaml` makes generating clients straightforward via `openapi-generator-cli`:

```bash
openapi-generator-cli generate \
  -i docs/openapi.yaml \
  -g go \
  -o clients/go/
```
