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
