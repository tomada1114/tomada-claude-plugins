# Cross-Cutting Section Templates

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

#### Requirements (WCAG 2.2 AA)
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
