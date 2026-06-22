---
name: designing-wireframes
description: "Create ASCII wireframes, user flow diagrams, and cross-cutting specifications for UI/UX visualization. Use PROACTIVELY when user mentions wireframe, UI design, UX flow, screen layout, screen design, user flow, or asks to visualize screens. Examples: <example>Context: User needs screen design user: 'Create wireframes for this feature' assistant: 'I will use designing-wireframes skill' <commentary>Triggered by wireframe request</commentary></example> <example>Context: After requirements are detailed user: 'Let me design the screens' assistant: 'I will use designing-wireframes skill' <commentary>Triggered by screen design request</commentary></example>"
---

# Wireframe Designer

Create ASCII wireframes, user flow diagrams, and cross-cutting specifications for UI/UX visualization.

## When to Use This Skill

Use PROACTIVELY when:
- Requirements are detailed and need UI/UX visualization
- Screen layouts need to be designed
- User flows need to be documented
- Cross-cutting concerns need specification (error handling, accessibility, etc.)
- User mentions: wireframe, UI design, UX flow, screen layout, screen design

**Before this skill**: Use `refining-requirements` to clarify ambiguous requirements.
**After this skill**: Use `planning-tickets` for GitHub Issues creation.

## Workflow

```
Input: Detailed requirements document
    |
Step 1: Create wireframes for each screen
    |
Step 2: Document user flows
    |
Step 3: Add cross-cutting sections
    |
Output: Requirements with wireframes & specifications
```

## Step 1: Create ASCII Wireframes

Create ASCII wireframes for each screen in the requirements.

### Thumb-Zone Design (CRITICAL for Mobile)

Primary actions should be placed in the "green zone" (bottom of screen) for easy thumb reach.

```
+----------------------------------+
|                                  |  <- Hard to reach (Red)
|    Settings, destructive         |     Place: Settings, delete
|                                  |
+----------------------------------+
|                                  |  <- Stretch zone (Yellow)
|    Secondary content             |     Place: Secondary actions
|                                  |
+----------------------------------+
|                                  |  <- Natural zone (Green)
|    Primary actions               |     Place: Main CTA, nav
|                                  |
+----------------------------------+
         Thumb position
```

### Recommended: Actions at Bottom

```
+----------------------------------+
|  Title                    [gear] |  <- Settings in hard zone (OK)
+----------------------------------+
|                                  |
|  Content Area                    |  <- Scrollable content
|  (scrollable)                    |
|                                  |
+----------------------------------+
|  [Action 1] [Action 2] [+]       |  <- Primary actions in green zone
+----------------------------------+
|  [Tab 1]  |     [Tab 2]          |  <- Tab bar in green zone
+----------------------------------+
```

### Component Patterns

See [wireframe-patterns.md](templates/wireframe-patterns.md) for:
- Screen structures (basic, with header actions, tab-based)
- Components (progress bars, button grids, lists, settings)
- Modals & overlays (bottom sheet, center modal, alert)
- Onboarding screens
- Feedback (toast notifications)
- Swipe actions
- Empty states

## Step 2: Document User Flows

Document user flows with numbered steps:

```
1. User taps button
2. Bottom Sheet appears with options
3. User selects option
4. Record saved -> Toast notification
5. UI updates with new data
```

### Flow Diagram Format

```
[Start] -> [Screen A] -> [Action] -> [Screen B]
                |
                v
           [Error] -> [Retry]
```

## Step 3: Add Cross-Cutting Sections (REQUIRED)

Based on user decisions from refining-requirements, add these cross-cutting sections:

### Error Handling Section

```markdown
### X.X Error Handling

#### DB Save Error
- **Format**: Toast notification
- **Message**: "Failed to save. Please try again."
- **Retry**: No auto-retry (user re-attempts action)

#### Network Error (e.g., RevenueCat, API)
- **Format**: Alert
- **Message**: "Failed to connect. Check your network."
- **Buttons**: "Retry" / "Cancel"

#### Generic Error
- **Format**: Toast notification
- **Message**: "An error occurred"
- **Auto-dismiss**: 3 seconds
```

### Accessibility Section

```markdown
### X.X Accessibility

#### Requirements (WCAG 2.1 AA)
- **Contrast ratio**: Text 4.5:1 or higher
- **Touch targets**: 44x44pt minimum
- **accessibilityLabel**: Required for all interactive elements

#### VoiceOver/TalkBack Support
- Proper accessibilityRole (button, text, header, etc.)
- State change announcements (record saved, error occurred)

#### Focus Order
- Logical tab order
- Modal focus trapping
```

### Loading & Feedback Section

```markdown
### X.X Loading & Feedback

#### Loading States
- **Format**: Spinner / Skeleton / Shimmer
- **Position**: Center of screen / Inline
- **Overlay**: Semi-transparent (for blocking operations)

#### Success Feedback
- **Format**: Toast notification
- **Position**: Top of screen (below nav bar)
- **Duration**: 2-3 seconds auto-dismiss
- **Haptic**: Light impact (optional)

#### Warning Feedback
- **Format**: Alert dialog
- **Buttons**: Confirm action / Cancel
- **Haptic**: Warning notification (optional)
```

### Form Validation Section

```markdown
### X.X Form Validation

#### Validation Timing
- **When**: Inline real-time / On blur / On submit

#### Error Display
- **Format**: Red text below input field
- **Style**: Semantic error color

#### Example Rules

| Field | Rule | Error Message |
|-------|------|---------------|
| Name | Required, 1-20 chars | "Enter 1-20 characters" |
| Amount | 0-1000 range | "Enter 0-1000" |
| Email | Valid format | "Enter valid email" |

#### Keyboard Types
- Text fields: Default keyboard
- Numbers: Numeric keyboard
- Email: Email keyboard
```

## Best Practices

### Wireframes
- Use ASCII art for quick visualization
- Keep wireframes simple but complete
- Show key UI elements and their positions
- Annotate with arrows and comments
- Always consider Thumb-Zone for mobile

### Cross-Cutting Sections
- Include all 4 sections for mobile apps:
  1. Error Handling
  2. Accessibility
  3. Loading & Feedback
  4. Form Validation
- Be specific about formats and timings
- Include example error messages

### Documentation
- Cross-reference related sections
- Use consistent formatting
- Include default values
- Document all edge cases

## Templates

- [wireframe-patterns.md](templates/wireframe-patterns.md) - Common UI patterns for ASCII wireframes

## AI Assistant Instructions

When this skill is activated:

### DO:
1. **Create wireframes** - Use ASCII art for all screens
2. **Consider Thumb-Zone** - Place primary actions at bottom for mobile
3. **Document flows** - Show step-by-step user journeys
4. **Add cross-cutting sections** - All 4 sections for mobile apps
5. **Use templates** - Reference wireframe-patterns.md for consistency
6. **Update document** - Edit requirements document section by section

### MUST INCLUDE (for mobile apps):
1. **Thumb-Zone optimized layouts** - Primary actions at bottom
2. **Error Handling section** - All error types with formats
3. **Accessibility section** - WCAG requirements, VoiceOver support
4. **Loading & Feedback section** - Loading states, success/warning feedback
5. **Form Validation section** - Timing, display format, rules

### DON'T:
1. Skip wireframe creation
2. Ignore Thumb-Zone design for mobile
3. Leave cross-cutting sections incomplete
4. Use complex graphics instead of ASCII
5. Forget empty states in wireframes
6. Skip edge case documentation

### When Uncertain:
- Refer to wireframe-patterns.md for component examples
- Ask user about specific UI decisions
- Default to platform conventions (iOS/Android)

### After Completion:
Suggest using `planning-tickets` skill to create implementation tickets from the detailed requirements.
