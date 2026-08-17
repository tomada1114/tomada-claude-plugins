# Performance Checklist (PERF1–PERF5)

This is a checklist for the performance specialist sub-agent in `example-code-review`. Each item has a stable ID so findings can be merged with the security sub-agent's output mechanically. New items append at the bottom; never renumber.

## PERF1: N+1 queries

A new loop that issues a database query per iteration is a fail. Look for:
- `for x in items: ... db.query(...)`
- New ORM access inside a list comprehension or `.map(...)`
- Lazy-loaded relationships fetched inside loops

How to verify: scan the diff for new loops, then check whether anything inside touches the database.

## PERF2: Missing index for new query patterns

If the diff adds a query that filters or joins on a column with no index, FAIL. Adding the index in the same PR (via migration) makes it PASS.

How to verify: identify new WHERE / JOIN columns. Check the migrations folder in the diff for matching index additions, or confirm an index already exists in the schema.

## PERF3: Unbounded result sets

Endpoints that return collections must paginate or have a hard cap. A new `SELECT *` with no `LIMIT` returned to the client is a fail.

How to verify: trace the response payload of new endpoints. If it's a list with no pagination, FAIL.

## PERF4: Synchronous I/O on hot paths

Blocking calls inside an async handler (sync HTTP, sync file I/O, sync DB driver in async code) defeats the runtime. Likewise, expensive computation on the request thread that should be offloaded to a queue.

How to verify: in async codebases, check for `requests.get` instead of the async client, sync `open(...)`/`read()`, or CPU-heavy work without offloading.

## PERF5: Repeated work / missing memoization

A new function that recomputes the same expensive value many times in a request lifecycle, or a new computation that could trivially be cached in memory or by an existing cache layer.

How to verify: look at new functions called from request handlers. If the input space is small and the function is pure and expensive, FAIL.

---

When reporting, use the format:

```
PERF<N> <PASS|FAIL|N-A> [severity]: <one-line justification> (<file>:<line>)
```

Severity for FAIL items: critical / high / medium / low. Use your judgment based on the user-visible impact and the frequency the code path runs.
