# Requirements Section Template

Use this template to detail each feature section in the requirements document.

## Template

```markdown
### X.X Feature Name

#### Overview
- **Purpose**: What this feature does
- **Access**: How users access this feature

#### Specifications

| Item | Specification |
|------|---------------|
| [Spec 1] | [Value/Description] |
| [Spec 2] | [Value/Description] |

#### UI Behavior
- **Default state**: Description
- **User action**: What happens when...
- **Feedback**: How the system responds

#### Edge Cases
- **Empty state**: What to show when no data
- **Limit reached**: Behavior at boundaries
- **Error state**: How to handle failures

#### Default Values

| Setting | Default |
|---------|---------|
| [Setting 1] | [Value] |
| [Setting 2] | [Value] |
```

## Example: Home Screen

```markdown
### 4.3 Home Screen

#### Overview
- **Purpose**: Display progress and enable quick recording
- **Access**: Default tab, opens on app launch

#### Specifications

| Item | Specification |
|------|---------------|
| Tab position | First tab (left) |
| Navigation | Tab bar at bottom |
| Settings access | Gear icon in header (right) |

#### UI Components

**Progress Bars**
- Water: Current / Goal (e.g., 1.2L / 2.0L)
- Caffeine: Current / Limit (e.g., 150mg / 300mg)
- Over 100%: Bar stops at 100%, text shows exceeded value

**Quick Add Buttons**
- Count: 7 buttons
- Design: Text only (no icons)
- Items: Water, Coffee, Tea, Green Tea, Juice, Milk, +

**Today's Log**
- Position: Below progress bars
- Display: All items (scrollable)
- Empty state: "No records yet" text

#### Edge Cases
- **Empty state**: Show "No records yet" in log section
- **Over 100%**: Bar caps at 100%, text shows "2.5L / 2.0L ✓"
- **Midnight reset**: Clear all records at 00:00
```

## Example: Settings Screen

```markdown
### 4.5 Settings Screen

#### Access
- Tap gear icon in home screen header (top-right)

#### Sections

| Section | Items |
|---------|-------|
| Goals | Water goal, Caffeine limit, Bedtime |
| Display | Unit (ml/oz) |
| Account | Subscription management |

#### Item Details

| Item | Input Type | Default |
|------|-----------|---------|
| Water goal | Slider (ml) | 2,000ml |
| Caffeine limit | Number input (mg) | 300mg |
| Bedtime | Time picker | 22:00 |
| Unit | Toggle (ml/oz) | ml |

#### Behaviors
- Unit change: Display conversion only (data unchanged)
- Navigation: Push to detail screen for each setting
```

---

## Cross-Cutting Sections Template

These sections should be added to every requirements document for mobile apps.

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
