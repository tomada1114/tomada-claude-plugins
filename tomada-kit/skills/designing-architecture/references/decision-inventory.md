# Decision inventory

Walk this list against the requirements before asking anything. A row applies when the
requirements or the template force a choice on it; skip rows the template already
decides (a repository skill or `AGENTS.md` already settles it) and rows the MVP never
touches. Each applicable row becomes one decision, written in the present tense into the
skill that owns its subject (SKILL.md Contract); the last column names the usual owner in
the user's templates — confirm it against the repository's own Owns lines.

| Decision | Applies when | What the options usually are | Usual home |
|---|---|---|---|
| Design lock | any app with a UI | the direction in `design-direction.md`, written in the template's lock format | `designing-ui` (its lock reference) |
| App shape | desktop apps | windowed app vs menu-bar agent (tray, no Dock icon) vs both | `starting-an-app` (its app-shape section) |
| Sandbox and OS permissions | macOS apps | sandboxed vs not; each TCC permission (Accessibility, Screen Recording, Full Disk Access, notifications, calendars…) is its own decision | `integrating-system-apis` |
| Persistence | the app keeps any state | where (app support dir, browser storage, server DB), format (SQLite, JSON files, key-value), migration story | `persisting-data`, or a new skill of that name |
| Backend and sync | data leaves the device | none (local-only) vs own server vs BaaS; offline behavior; conflict handling | `persisting-data` / the skill that owns the API client |
| Authentication | there are accounts | none vs provider (OAuth, passkeys, magic link) vs the template's default | the skill that owns routes or sessions; a new one if none |
| External services | an API, an LLM, payments | which provider, the port/adapter seam, key handling, cost ceiling | the skill that owns that port (e.g. `calling-models`, `integrating-system-apis`) |
| Key dependencies | a library carries a core feature | candidates with their licence, maintenance, and fit with the template's dependency rules | `managing-dependencies` plus the skill that uses the library |
| Locales | UI text exists | languages at launch, where strings live, the template's i18n mechanism | `localizing-the-app` |
| Template layers kept or removed | the template ships an optional layer (for example an AI layer, a sample, a sidecar) | keep vs remove whole, per the template's `starting-an-app` | `starting-an-app`; layer rules in `AGENTS.md`'s Architecture |
| Distribution | the app ships to users | store vs direct download vs web deploy; signing, notarization, updater; the first release target | the skill that owns releases, or `starting-an-app` |
| Minimum platform version | native or desktop apps | the OS version floor and what it enables | `starting-an-app` / `changing-gates` |

Research every option before presenting it: current versions, licences, and platform
support from primary sources (a library documentation lookup tool where the runtime has
one, the official docs otherwise), with the URL and the date checked written beside
the claim. A claim that could not be checked is written as unchecked, never dated.
