---
name: http-status-guide
description: Pick the HTTP status code an API should return for a given outcome, and settle the cases where two codes both look defensible — 401 vs 403, 400 vs 422, 404 vs 403 for hidden resources, 409 vs 422 for conflicts. Use when designing REST endpoints, reviewing an API's error handling, or debugging a client that mishandles a response.
---

# HTTP Status Guide

Demonstrates progressive disclosure: the body carries the decision, `references/` carries the detail. The reference is read only when the decision needs it.

## Procedure

1. Name the outcome in one sentence — what the server did, not what the client asked for. "Created a row" and "rejected because the email is taken" pick different codes.
2. Map it with the table below.
3. If the outcome is one of the contested pairs, read [references/http-status-codes.md](references/http-status-codes.md) — it resolves each pair and gives the response body shape.

## Table

| Outcome | Code |
|---|---|
| Read succeeded, body attached | 200 |
| Resource created | 201 + `Location` |
| Accepted, work happens later | 202 |
| Succeeded, deliberately no body | 204 |
| Request is malformed — unparseable, wrong content type | 400 |
| Caller is unidentified or the credential expired | 401 + `WWW-Authenticate` |
| Caller is identified and still not permitted | 403 |
| No such resource, and admitting that is safe | 404 |
| Syntax is fine, the values violate a business rule | 422 |
| Rate limited | 429 + `Retry-After` |
| Unhandled server fault | 500 |
| Dependency down or deploy in progress | 503 + `Retry-After` |

Two rules the table cannot show: never return 200 with an error payload, and never leak existence through the status code — an unauthorized read of a resource the caller may not know about returns 404, not 403.
