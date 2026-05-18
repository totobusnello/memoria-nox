---
title: Vulnerability Reporting
description: Responsible disclosure policy for memoria-nox security vulnerabilities.
sidebar:
  order: 3
---

Full policy: [`SECURITY.md`](https://github.com/totobusnello/memoria-nox/blob/main/SECURITY.md)

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report privately via:
- **GitHub Security Advisories:** [github.com/totobusnello/memoria-nox/security/advisories/new](https://github.com/totobusnello/memoria-nox/security/advisories/new)

## Response timeline

| Step | Target |
|---|---|
| Acknowledgement | Within 48 hours |
| Initial assessment | Within 5 business days |
| Fix timeline communicated | Within 10 business days |
| Coordinated disclosure | Mutually agreed date |

## Scope

In scope: nox-mem CLI, MCP server, HTTP API, SQLite schema, ingest pipeline, embedding provider integrations.

Out of scope: Issues in dependencies not directly affecting nox-mem; DoS via computational exhaustion on localhost.
