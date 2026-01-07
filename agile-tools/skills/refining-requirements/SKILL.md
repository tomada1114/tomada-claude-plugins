---
name: refining-requirements
description: Clarify ambiguous requirements through structured questioning and produce detailed, implementation-ready specifications. Acts as PdM to identify unclear points and resolve them via AskUserQuestion. Use PROACTIVELY when user mentions requirements, specs, PRD, refine, detail, clarify requirements, or asks to detail/refine app ideas. Examples: <example>Context: User has rough idea user: 'Help me refine this app spec' assistant: 'I will use refining-requirements skill' <commentary>Triggered by spec refinement request</commentary></example> <example>Context: Planning phase user: 'Let me detail the requirements' assistant: 'I will use refining-requirements skill' <commentary>Triggered by requirements detailing</commentary></example>
---

# Requirements Refiner

Clarify ambiguous requirements through structured questioning and produce detailed, implementation-ready specifications.

## When to Use This Skill

Use PROACTIVELY when:
- User has a rough product idea or feature memo to refine
- Requirements contain ambiguous or unclear points
- Specifications need clarification before implementation
- User mentions: requirements, PRD, specs, refine, detail, clarify

**After this skill**: Use `designing-wireframes` for UI/UX visualization, then `planning-tickets` for GitHub Issues.

## Workflow

```
Phase 1: Read & Understand
    |
Phase 2: Identify Ambiguities
    |
Phase 3: Question Rounds (AskUserQuestion)
    |
Output: Detailed requirements document
```

## Phase 1: Read & Understand

1. Read the provided requirements document
2. Understand the core value proposition
3. Identify the target user and their pain points
4. Note the technical stack and constraints

## Phase 2: Identify Ambiguities

Systematically check for ambiguities in these categories:

### UI Components
| Category | Questions to Consider |
|----------|----------------------|
| Layout | Screen structure, section arrangement, navigation |
| Interaction | Tap, swipe, long-press behaviors |
| Feedback | Success/error states, loading indicators |
| Empty States | What to show when no data exists |

### UX Flows
| Category | Questions to Consider |
|----------|----------------------|
| Navigation | How users move between screens |
| Data Entry | Input methods, validation, defaults |
| Edge Cases | What happens at boundaries (100%+, limits) |
| Error Handling | How to handle and display errors |

### Business Logic
| Category | Questions to Consider |
|----------|----------------------|
| Limits | Free vs Pro, numeric limits |
| Defaults | Initial values for settings |
| Calculations | Formulas, timing, thresholds |

### Mobile UX (MUST CHECK for mobile apps)
| Category | Questions to Consider |
|----------|----------------------|
| Thumb-Zone Design | Are primary actions in the bottom zone (easy thumb reach)? |
| Touch Targets | Are all interactive elements >= 44x44pt? |
| Loading States | How to show loading (spinner, skeleton, shimmer)? |
| Haptic Feedback | Use vibration feedback for confirmations/warnings? |
| Animation | iOS standard spring animations or custom? Duration/easing? |

### Accessibility (MUST CHECK)
| Category | Questions to Consider |
|----------|----------------------|
| WCAG Compliance | Target AA or AAA? Contrast ratio 4.5:1? |
| Touch Targets | Minimum 44x44pt for all interactive elements? |
| Screen Reader | accessibilityLabel for all interactive elements? VoiceOver support? |
| Focus Order | Logical tab order? Modal focus trapping? |

### Error Prevention & Recovery
| Category | Questions to Consider |
|----------|----------------------|
| Delete Actions | Immediate / Undo option / Confirmation dialog? |
| Form Validation | Inline real-time / On submit? Specific validation rules? |
| Error Display | Toast / Alert / Inline error message? Auto-dismiss timing? |
| Retry Logic | Auto-retry with exponential backoff? Manual retry button? |

### Visual Design
| Category | Questions to Consider |
|----------|----------------------|
| Dark Mode | Light only (MVP) / System automatic / Manual toggle? |
| Empty States | Simple text / Icon + text / CTA button? |
| Color Scheme | Platform standard colors or custom brand colors? |

## Phase 3: Question Rounds

Use `AskUserQuestion` tool to clarify ambiguities. Group related questions (max 4 per round).

### Question Design Principles

1. **Provide concrete options** - Don't ask open-ended questions
2. **Include trade-offs** - Explain what each option means
3. **Use descriptive headers** - Short, scannable labels (max 12 chars)
4. **Batch related questions** - Group by topic area

### Example Question Categories

**UI Style Questions:**
```
- Size selection UI format?
  -> Bottom Sheet / Modal / Inline Expansion

- Button design?
  -> Icon+Text / Icon only / Text only

- List display format?
  -> Grouped / Flat
```

**Behavior Questions:**
```
- Display when over 100%?
  -> Cap at 100% / Show excess in different color / Ring format

- Delete confirmation?
  -> With confirmation / Without confirmation

- Error behavior?
  -> Warn and continue / Block
```

**Navigation Questions:**
```
- Screen access method?
  -> Tab bar / Header icon / In-screen link

- Onboarding steps?
  -> 1 screen / 3 steps / 4 steps
```

**Pro/Free Questions:**
```
- Paywall display timing?
  -> On feature tap / At boundary reached

- Paywall UI?
  -> SDK standard / Custom
```

**Mobile UX Questions (CRITICAL for mobile apps):**
```
- Primary action button placement?
  -> Bottom (Thumb-Zone) fixed / Center / Within content

- Loading display format?
  -> Simple spinner / Skeleton Screen / Content Shimmer

- Haptic Feedback?
  -> Implement (on success, warning) / Don't implement
```

**Accessibility Questions (MUST ASK):**
```
- Accessibility requirements?
  -> WCAG AA compliance / Basic support only / Not in MVP

- VoiceOver/TalkBack support?
  -> Full support / Basic (accessibilityLabel) / Not in MVP
```

**Error Prevention Questions:**
```
- Delete operation UX?
  -> Immediate (no confirmation) / Toast with Undo / Confirmation dialog

- Define detailed validation rules?
  -> Define (specify char count, range, etc.) / Decide at implementation

- Error display format?
  -> Toast / Alert / Inline message
```

**Visual Design Questions:**
```
- Dark mode support?
  -> Light mode only (MVP) / Auto-follow system / Manual toggle

- Empty State display?
  -> Simple text / Icon + text / With CTA
```

### After Questions: Document Update

After gathering all answers, update the requirements document with:

1. **Detailed specifications** for each feature
2. **Edge case handling** definitions
3. **Default values** for all settings
4. **Validation rules** if defined

Use the [requirements-section.md](templates/requirements-section.md) template for consistent formatting.

## Best Practices

### Questioning
- Ask questions in rounds of 3-4 related topics
- Always provide 2-4 concrete options
- Include trade-off descriptions
- Don't ask about obvious decisions
- Skip questions if the document is already clear

### Documentation
- Be specific, not vague
- Include default values
- Document edge cases
- Cross-reference related sections

## Templates

- [requirements-section.md](templates/requirements-section.md) - Feature section template

## AI Assistant Instructions

When this skill is activated:

### DO:
1. **Read first** - Always read the requirements document before asking questions
2. **Use AskUserQuestion** - Proactively clarify ambiguities
3. **Batch questions** - Group related questions (max 4 per round)
4. **Provide options** - Always give concrete choices, not open-ended questions
5. **Update systematically** - Edit the document section by section
6. **Track progress** - Use TodoWrite to track phases

### MUST CHECK (for mobile apps):
1. **Thumb-Zone Design** - Ask about primary action button placement (bottom vs center)
2. **Accessibility** - Ask about WCAG compliance level, touch target sizes
3. **Loading States** - Ask how to display loading (spinner, skeleton, shimmer)
4. **Error Handling UX** - Ask about error display format (Toast, Alert, inline)
5. **Haptic Feedback** - Ask whether to implement vibration feedback
6. **Delete UX** - Ask about confirmation behavior (immediate, undo, dialog)
7. **Form Validation** - Ask about validation rules and error message format
8. **Dark Mode** - Ask about theme support (light-only, auto, manual)
9. **Empty States** - Ask about display format when no data exists

### DON'T:
1. Make assumptions about UI/UX without asking
2. Ask more than 4 questions at once
3. Ask vague, open-ended questions
4. Leave edge cases undefined
5. **Skip Mobile UX checks** - These are often overlooked but critical
6. **Skip Accessibility checks** - WCAG compliance should be decided early
7. **Skip Error Handling UX** - Every app needs clear error feedback

### Question Flow (Recommended Order):
1. **Core UI decisions** - Layout, navigation, basic components
2. **Mobile UX** - Thumb-zone, loading states, haptic feedback
3. **Accessibility** - WCAG level, touch targets, VoiceOver
4. **Error handling & validation** - Delete UX, form validation, error display
5. **Visual design** - Dark mode, empty states, animations
6. **Pro/monetization** - Paywall timing, feature gates

### When Uncertain:
- Always ask the user rather than assume
- Provide 2-4 options with clear trade-offs
- Explain the implications of each choice

### After Completion:
Suggest using `designing-wireframes` skill for UI/UX visualization if screens need to be designed.
