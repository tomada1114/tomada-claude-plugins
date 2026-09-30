# App-type questions

These are worked examples used in Round 4 (app type) of the question rounds defined in `questions-core.md`; do not reuse them verbatim. The question-design rules are in SKILL.md § "Asking questions". For an app type not listed here, build 2–3 equivalent questions from the "Best practices" and "Patterns to avoid" of the matching section in `app-type-ux-patterns.md` or `app-type-ux-patterns-verticals.md`, choosing only points whose answer changes an implementation value.

## Table of contents

- [Conversation / voice apps](#conversation--voice-apps)
- [E-commerce / shopping](#e-commerce--shopping)
- [Dashboards / admin panels](#dashboards--admin-panels)
- [AI assistant / agent](#ai-assistant--agent)

## Conversation / voice apps

For session-based products (start → conversation → evaluation). If the product does not evaluate after a session, drop the score display and ending transition questions.

### In-conversation UI

```json
{
  "question": "Which style should the in-conversation UI use?",
  "header": "Convo UI",
  "options": [
    { "label": "Minimal (Recommended)", "description": "Waveform animation and status only. Keeps focus on the conversation, but there is no way to check an utterance the user missed" },
    { "label": "Chat bubbles", "description": "Shows utterances as text in real time. Checkable, but attention shifts to reading and users speak less" },
    { "label": "Hybrid", "description": "Minimal by default; tap to open the transcript. Gets both, but adds open/closed state management and re-render design" }
  ]
}
```

### Status display

```json
{
  "question": "What should the in-conversation status display include?",
  "header": "Status",
  "options": [
    { "label": "Waveform + status text (Recommended)", "description": "Puts \"Listening\" / \"Thinking\" into words. Less likely to look frozen during silence, but needs translation and screen-reader support for the copy" },
    { "label": "Waveform only", "description": "Language-independent and uncluttered. But waiting and unresponsive are hard to tell apart" },
    { "label": "Waveform + turns left", "description": "Shows progress like \"3/10\". Seeing the end reassures, but awareness of the count makes utterances shorter" }
  ]
}
```

### Intro UI (before the session)

```json
{
  "question": "What should the pre-session intro UI be?",
  "header": "Intro",
  "options": [
    { "label": "Simple (Recommended)", "description": "Scenario description and a start button only. Returning users start fastest, but a first-time mic problem is only noticed after the conversation starts" },
    { "label": "Briefing", "description": "Introduces the counterpart role and today's topic. Conveys context, but reading it every time becomes an obstacle from the second session on" },
    { "label": "Warm-up", "description": "Adds a mic test or short vocal warm-up. Reduces failed sessions, but adds steps before starting" }
  ]
}
```

### Ending transition (after the session)

```json
{
  "question": "How should the session end transition work?",
  "header": "Ending",
  "options": [
    { "label": "Smooth transition", "description": "Fades into the feedback screen. A natural break, but hiding the scoring wait needs separate design" },
    { "label": "Summary modal", "description": "Shows a result overview in a modal; tap for details. Users can finish after the highlights, but more users leave just by closing the modal" },
    { "label": "Immediate display", "description": "Shows the feedback screen with no transition. Fastest path to results, but cuts off the afterglow of the conversation" }
  ]
}
```

### Score / feedback display

```json
{
  "question": "Which visual format should the score display use?",
  "header": "Score view",
  "options": [
    { "label": "Circular gauges", "description": "One circular gauge per axis. Strengths and weaknesses are clear at a glance, but more than five axes do not fit a narrow screen" },
    { "label": "Bar chart", "description": "Compares axes with horizontal bars. Extends vertically as axes grow, but conveys less sense of achievement than circles" },
    { "label": "Overall score only", "description": "One large number with an expandable breakdown. Unambiguous to read, but the first screen does not show what to improve" }
  ]
}
```

### Feedback density

```json
{
  "question": "How dense should the feedback screen be?",
  "header": "FB density",
  "options": [
    { "label": "Compact (Recommended)", "description": "Score and highlights only, details expandable. Easy to return to the next session, but thin for users who want deep review" },
    { "label": "Detailed", "description": "Shows every utterance and alternative phrasing at once. High review value, but the volume overwhelms and more of it goes unread" },
    { "label": "Cards", "description": "Reviews one utterance per card. Raises focus on each item, but takes longer to grasp the whole" }
  ]
}
```

## E-commerce / shopping

### Product list density

```json
{
  "question": "How should the product list be presented?",
  "header": "Listing",
  "options": [
    { "label": "Image-first grid", "description": "Large image + price only. Strong for goods chosen by look, but spec-compared goods need more round trips to detail pages" },
    { "label": "Info cards", "description": "Image + price + reviews + key attributes. Easy to compare, but cards grow taller and fewer fit per screen" },
    { "label": "Row list (table)", "description": "Aligns attributes in columns. Best for comparing model-numbered goods, but conveys little brand character and needs horizontal scroll on mobile" }
  ]
}
```

### Checkout shape

```json
{
  "question": "Which shape should the checkout flow take?",
  "header": "Checkout",
  "options": [
    { "label": "Step-by-step (Recommended)", "description": "Shipping → payment → review with a progress indicator. Less input per screen and drop-off points are identifiable, but more screen transitions" },
    { "label": "Single page", "description": "All fields on one screen. The total effort is visible and backtracking is rare, but it feels heavy at first and errors require long scrolling" },
    { "label": "Accordion single page", "description": "Sections open and close within one page. No transitions and progress is visible, but open state and validation combine into complexity" }
  ]
}
```

Include shipping and fees in the total from the first step. Why: if the total first rises at final review, that becomes the biggest drop-off point.

## Dashboards / admin panels

### Metric hierarchy

```json
{
  "question": "How should metric priority be shown on screen?",
  "header": "KPI layout",
  "options": [
    { "label": "Top KPI strip + detail sections (Recommended)", "description": "Pins key metrics at the top with details below. Reads from overview to detail, but five or more KPIs erase the priority" },
    { "label": "Single primary metric + supporting", "description": "One large number with others as support. The screen's purpose is clear, but it does not suit screens used by several roles" },
    { "label": "Uniform card grid", "description": "Same-size cards. Easy to add and reorder, but the UI does not say what matters, so every visit needs interpretation" }
  ]
}
```

### Drill-down method

```json
{
  "question": "How should users drill down from overview to detail?",
  "header": "Drill-down",
  "options": [
    { "label": "Inline expand", "description": "Opens the row in place to show the breakdown. Keeps context, but beyond two levels the screen breaks vertically" },
    { "label": "Separate screen", "description": "Room for full detail and shareable by URL, but returning to the overview takes an action every time" },
    { "label": "Side panel / sheet", "description": "Shows detail while keeping the list. Strong for checking items in sequence, but takes width, so list columns must be cut" }
  ]
}
```

## AI assistant / agent

### Streaming display

```json
{
  "question": "How should output be shown while generating?",
  "header": "Streaming",
  "options": [
    { "label": "Token-by-token (Recommended)", "description": "Shortest perceived wait. Code blocks and tables must be held until they close or broken intermediate states show, so that branch is needed" },
    { "label": "Render per block", "description": "Outputs per paragraph or code block. No broken display, but long blocks look unresponsive" },
    { "label": "All at once on completion", "description": "Most stable layout. But the wait is invisible and long tasks are easily judged as stalled" }
  ]
}
```

Whichever is chosen, always show a stop control during generation, and stop auto-scroll when the user scrolls up. Why: the feeling of losing control translates directly into distrust of AI products.

### Tool execution visibility

```json
{
  "question": "How much of the tool-call, search, and file-read process should be shown?",
  "header": "Tool trace",
  "options": [
    { "label": "One line per step live + collapsible details (Recommended)", "description": "Users see what is happening while it runs, and only those who need it open the contents. Lines keep growing, so collapsing after completion needs design" },
    { "label": "Always fully expanded", "description": "Best for verification and debugging, but buries the actual output in normal use" },
    { "label": "Results only", "description": "The quietest screen, but the wait has no visible reason and users cannot catch a wrong premise mid-task" }
  ]
}
```

### Citations and confidence

```json
{
  "question": "How should evidence and sources be shown?",
  "header": "Sources",
  "options": [
    { "label": "Inline numbers + source links (Recommended)", "description": "Maps each sentence to its evidence. Extra markers in the text slightly reduce readability" },
    { "label": "Reference list at the end", "description": "Body text reads easily. But sentences cannot be matched to evidence, so it is weak for verification" },
    { "label": "No sources", "description": "Only for purely generative uses. When external information is involved, do not choose it: only assertive tone remains, with no way to verify" }
  ]
}
```

Never show confidence as a number alone. Why: a standalone number is misread as a guarantee of accuracy and invites overconfidence.
