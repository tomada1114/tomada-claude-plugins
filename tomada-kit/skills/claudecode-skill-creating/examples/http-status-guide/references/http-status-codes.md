# HTTP Status Codes: Contested Cases

Read when the SKILL.md table leaves two codes both defensible. Codes with an unambiguous meaning are not repeated here.

## Contents

- [401 vs 403](#401-vs-403)
- [403 vs 404](#403-vs-404)
- [400 vs 422](#400-vs-422)
- [409 vs 422](#409-vs-422)
- [200 vs 204 on write](#200-vs-204-on-write)
- [301 vs 308, 302 vs 307](#301-vs-308-302-vs-307)
- [500 vs 502 vs 503 vs 504](#500-vs-502-vs-503-vs-504)
- [Error body shape](#error-body-shape)
- [Headers that are part of the code](#headers-that-are-part-of-the-code)

## 401 vs 403

401 means *who are you* — the credential is absent, malformed, or expired, and retrying with a good one would work. 403 means *I know who you are and the answer is still no*; retrying with the same identity is pointless.

The practical test: would a fresh login change the outcome? Yes → 401. No → 403.

An expired JWT is 401, not 403, even though the token was present. Clients key their refresh logic off 401.

## 403 vs 404

When the caller lacks permission on a resource whose *existence* is itself confidential — another tenant's record, a private repo — return 404. A 403 confirms the ID is real, which is an enumeration oracle.

Return 403 only when the caller is already entitled to know the resource exists: their own org's record under a role they lack, a feature gated by plan.

## 400 vs 422

400 is for requests the server could not parse or route: broken JSON, wrong `Content-Type`, a path parameter that is not the declared type. The request never reached your domain logic.

422 is for requests that parsed cleanly and then failed a semantic rule: `end_date` before `start_date`, a quantity above the per-order cap, a currency your account does not support.

If your framework's validation layer rejects it before your handler runs, that is usually 400; if your handler rejects it, usually 422. Whichever line you draw, draw it once and document it — clients branch on this.

## 409 vs 422

409 is reserved for conflicts with *current server state* that the client could resolve by re-reading and retrying: a duplicate unique key, a stale `If-Match` ETag, concurrent edits to the same row.

422 is a rule violation that no amount of retrying fixes without changing the payload.

"Email already registered" is 409. "Email is not a valid address" is 422.

## 200 vs 204 on write

204 promises an empty body, so the client must not attempt to parse one. Use it when the client already holds the resulting state — a PUT that echoes what was sent, a DELETE.

Prefer 200 with the updated resource when the server computed anything the client cannot predict: server-set timestamps, derived totals, a version counter. Saving a few bytes here costs a follow-up GET.

## 301 vs 308, 302 vs 307

301 and 302 historically let clients rewrite a POST into a GET on the redirect, and real clients still do. 308 and 307 forbid the method change.

Permanent moves of an API endpoint: 308. Temporary: 307. Reserve 301/302 for browser-facing HTML routes where the method rewrite is what you want (post-login landing, canonical host redirect).

## 500 vs 502 vs 503 vs 504

- **500** — your own code raised something unhandled. Never return it for a condition you anticipated.
- **502** — an upstream you proxy to returned a response you could not use.
- **503** — you are deliberately not serving right now: deploy in progress, dependency down, load shedding. The only one of the four that should carry `Retry-After`.
- **504** — an upstream did not answer within your timeout.

A client can retry 503 and 504 safely. Retrying 500 usually reproduces the bug.

## Error body shape

Every 4xx and 5xx should carry a body a client can branch on without parsing prose. A stable machine-readable code is the load-bearing field; the human message is not.

```json
{
  "error": {
    "code": "email_already_registered",
    "message": "That email is already in use.",
    "field": "email"
  }
}
```

Keep `code` stable across releases once shipped — clients match on it. Reword `message` freely.

## Headers that are part of the code

Some codes are incomplete without a header, and clients degrade badly when it is missing:

| Code | Required header |
|---|---|
| 201 | `Location` — URI of the created resource |
| 401 | `WWW-Authenticate` — the scheme to retry with |
| 405 | `Allow` — methods this path does accept |
| 429 | `Retry-After` — seconds or an HTTP date |
| 503 | `Retry-After` |
