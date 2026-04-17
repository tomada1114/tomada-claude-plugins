# Security Checklist (SEC1–SEC6)

This is a checklist for the security specialist sub-agent in `example-code-review`. Each item has a stable ID so findings from multiple sub-agents can be merged mechanically. New items should be appended at the bottom; never renumber.

## SEC1: Authentication on new endpoints

Every newly added route or controller method must enforce authentication. Look for:
- New route definitions without an auth middleware/decorator
- Public-by-default frameworks where the developer forgot to opt in to auth
- Auth bypassed via a debug or test flag that shipped to production

How to verify: grep the diff for new route registrations. Check the surrounding middleware stack.

## SEC2: Authorization / tenant isolation

In multi-tenant systems, every query that touches a tenant-scoped table must filter by the tenant ID (e.g. `account_id`, `org_id`). A new query without this filter is a critical issue.

How to verify: grep for new SQL/ORM queries against tenant tables. Check the WHERE clause.

## SEC3: SQL injection

Any new SQL built via string concatenation or interpolation is a fail. Use parameterized queries / prepared statements / ORM bindings.

How to verify: grep for `f"SELECT`, `f"INSERT`, `"+ user_`, `${...}` inside SQL strings, or `.raw(...)` calls in the ORM with non-constant arguments.

## SEC4: Secret leakage

New code must not log, print, or serialize secrets, tokens, passwords, or API keys. Check both server logs and JSON responses sent to clients.

How to verify: grep the diff for `password`, `token`, `secret`, `api_key`, `Authorization` and trace where those variables go.

## SEC5: Input validation

User-supplied input must be validated before being trusted. New endpoints should declare a schema (Pydantic, Zod, validators, FormRequest) and reject invalid payloads with a 4xx response.

How to verify: for each new endpoint, find the validation step. If absent, FAIL.

## SEC6: Dangerous primitives

Avoid `eval`, `exec`, `pickle.loads` on untrusted input, `child_process` with unsanitized arguments, `dangerouslySetInnerHTML` with user data. Any new use of these in the diff is at minimum a high-severity finding.

How to verify: grep the diff for the relevant primitives.

---

When reporting, use the format:

```
SEC<N> <PASS|FAIL|N-A> [severity]: <one-line justification> (<file>:<line>)
```

Severity for FAIL items: critical / high / medium / low. Use your judgment based on exploitability and blast radius.
