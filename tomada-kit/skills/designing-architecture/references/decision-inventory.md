# Decision inventory

Walk this list against the requirements before asking anything. A row applies when the
requirements or the template force a choice on it; skip rows the template already
decides (its `docs/architecture.md`, README "Design Philosophy", or `AGENTS.md` settle
them) and rows the MVP never touches. Each applicable row becomes one ADR.

| Decision | Applies when | What the options usually are |
|---|---|---|
| Design lock | any app with a UI | the direction in `design-direction.md`, written in the template's lock format |
| App shape | desktop apps | windowed app vs menu-bar agent (tray, no Dock icon) vs both |
| Sandbox and OS permissions | macOS apps | sandboxed vs not; each TCC permission (Accessibility, Screen Recording, Full Disk Access, notifications, calendars…) is its own ADR |
| Persistence | the app keeps any state | where (app support dir, browser storage, server DB), format (SQLite, JSON files, key-value), migration story |
| Backend and sync | data leaves the device | none (local-only) vs own server vs BaaS; offline behavior; conflict handling |
| Authentication | there are accounts | none vs provider (OAuth, passkeys, magic link) vs the template's default |
| External services | an API, an LLM, payments | which provider, the port/adapter seam, key handling, cost ceiling |
| Key dependencies | a library carries a core feature | candidates with their licence, maintenance, and fit with the template's dependency rules |
| Locales | UI text exists | languages at launch, where strings live, the template's i18n mechanism |
| Template layers kept or removed | the template ships an optional layer (for example an AI layer, a sample, a sidecar) | keep vs remove whole, per the template's `starting-an-app` |
| Distribution | the app ships to users | store vs direct download vs web deploy; signing, notarization, updater; the first release target |
| Minimum platform version | native or desktop apps | the OS version floor and what it enables |

Research every option before presenting it: current versions, licences, and platform
support from primary sources (a library documentation lookup tool where the runtime has
one, the official docs otherwise), with the URL and the date checked written into the
ADR's Sources. A claim that could not be checked is written as unchecked, never dated.

## Overview document skeleton

For the app's own architecture overview — used when the template has no better home,
or appended to the template's architecture document as an app section. Match length to
substance; drop a section with nothing app-specific to say.

```markdown
# <App> architecture

## Principles
3–7 lines. Each names what it rules out, e.g. "Local-first: every feature works offline;
no screen waits on the network." — rules out server-rendered lists.

## Shape
How the app's domains map onto the template's layers (a table: domain → layer → module
path), and what crosses each boundary.

## Data
Entities, their relationships, where each is stored (link the persistence ADR).

## Core flows
One short sequence per core interaction from the Product section: trigger → layers
touched → persisted effect → what the user sees.

## Quality targets
Measurable: launch time, list size it stays smooth at, offline behavior, privacy
guarantees — each with the check that proves it (a test, a smoke run, a gate).

## Decisions
Links to the ADRs, one line each.
```
