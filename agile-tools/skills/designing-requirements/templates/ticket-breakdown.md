# Ticket Breakdown Template

Structure implementation tickets by development phase.

## Template Structure

```markdown
## Implementation Tickets

### Phase N: Phase Name

| # | Ticket | Details |
|---|--------|---------|
| N-1 | Ticket title | Technical requirements and scope |
| N-2 | Ticket title | Technical requirements and scope |
```

## Recommended Phases

### Phase 1: Foundation
Setup the technical base before building features.

| # | Ticket | Details |
|---|--------|---------|
| 1-1 | Database Schema | Define tables, relationships, types |
| 1-2 | State Management | Setup Zustand/Redux stores |
| 1-3 | Navigation Structure | Configure router and screens |
| 1-4 | Theme & Design System | Colors, typography, spacing |
| 1-5 | i18n Setup | Configure localization framework |

### Phase 2: Core UI Components
Build reusable components before screens.

| # | Ticket | Details |
|---|--------|---------|
| 2-1 | Button Components | Primary, secondary, ghost variants |
| 2-2 | Card Components | Container with consistent styling |
| 2-3 | Progress Components | Bar, ring, percentage display |
| 2-4 | List Components | Item, section header, swipe actions |
| 2-5 | Modal Components | Bottom sheet, dialog, alert |

### Phase 3: Main Screen
The primary screen users see and use most.

| # | Ticket | Details |
|---|--------|---------|
| 3-1 | Screen Layout | Header, content, navigation |
| 3-2 | Data Display | Progress, summaries, status |
| 3-3 | Quick Actions | Primary action buttons |
| 3-4 | Activity List | Today's records/activity |

### Phase 4: Recording/Input Flow
The primary user action flow.

| # | Ticket | Details |
|---|--------|---------|
| 4-1 | Input UI | Selection modal, form, picker |
| 4-2 | Data Persistence | Save to database, update state |
| 4-3 | Feedback | Toast, animation, haptics |
| 4-4 | Validation | Input validation, limits |
| 4-5 | Warning Dialogs | Confirmation, alerts |

### Phase 5: History/List Screen
Historical data viewing.

| # | Ticket | Details |
|---|--------|---------|
| 5-1 | List with Grouping | Section headers, date grouping |
| 5-2 | Item Display | Record details, formatting |
| 5-3 | Delete Action | Swipe to delete, confirmation |
| 5-4 | Pagination/Limits | Free tier limits, load more |

### Phase 6: Settings Screen
Configuration and preferences.

| # | Ticket | Details |
|---|--------|---------|
| 6-1 | Settings List UI | Sections, items, chevrons |
| 6-2 | Value Editing | Sliders, pickers, inputs |
| 6-3 | Unit Conversion | Display conversion logic |
| 6-4 | Data Persistence | Save preferences |

### Phase 7: Onboarding
First-run user experience.

| # | Ticket | Details |
|---|--------|---------|
| 7-1 | Welcome Screen | App intro, value proposition |
| 7-2 | Setup Screens | Goal/preference configuration |
| 7-3 | Skip Flow | Handle skip, use defaults |
| 7-4 | Completion State | Mark onboarding complete |

### Phase 8: Monetization
Pro features and paywalls.

| # | Ticket | Details |
|---|--------|---------|
| 8-1 | Payment SDK Setup | RevenueCat, StoreKit integration |
| 8-2 | Subscription State | Pro detection, state management |
| 8-3 | Paywall UI | Purchase screen, restore button |
| 8-4 | Feature Gating | Lock/unlock Pro features |
| 8-5 | Pro-only Features | Implement gated features |

### Phase 9: Polish & Launch
Final touches before release.

| # | Ticket | Details |
|---|--------|---------|
| 9-1 | Error Handling | Global error handling, retry |
| 9-2 | Loading States | Skeleton, spinner, placeholder |
| 9-3 | App Icon & Splash | Asset creation, configuration |
| 9-4 | Store Assets | Screenshots, description, keywords |
| 9-5 | Analytics Setup | Event tracking, crash reporting |

## Ticket Writing Guidelines

### Good Ticket Example

```markdown
| 3-1 | Progress Bar Component |
Reusable progress bar for water/caffeine tracking.
- Props: current, goal, color, label
- Handle 100%+ overflow (cap bar, show text)
- Animate on value change
- Accessibility: announce percentage |
```

### Ticket Sizing

- **Small (S)**: Single component, < 2 hours
- **Medium (M)**: Multiple related components, 2-4 hours
- **Large (L)**: Full feature, 4-8 hours
- **X-Large (XL)**: Complex feature, > 8 hours (split it!)

### Dependencies

Note dependencies between tickets:

```markdown
| 4-2 | Data Persistence |
Depends on: 1-1 (Database Schema), 1-2 (State Management)
Save drink records to SQLite, update Zustand store. |
```

### Acceptance Criteria

Include testable criteria:

```markdown
| 7-1 | Welcome Screen |
Criteria:
- [ ] Shows app name and tagline
- [ ] Lists 3 feature points
- [ ] "Next" navigates to step 2
- [ ] "Skip" completes onboarding with defaults |
```

## Example: Complete Breakdown

```markdown
## 12. Implementation Tickets

### Phase 1: Foundation

| # | Ticket | Details |
|---|--------|---------|
| 1-1 | Database Schema | drink_logs, settings, custom_drinks tables with Drizzle ORM |
| 1-2 | Zustand Store | Today's records, settings, subscription state |
| 1-3 | Tab Navigation | expo-router (tabs) with Home/History |
| 1-4 | Theme Config | iOS System Colors, light mode only |

### Phase 2: Home Screen

| # | Ticket | Details |
|---|--------|---------|
| 2-1 | Progress Bars | Water/caffeine with 100% overflow handling |
| 2-2 | Cutoff Display | Calculate bedtime - 6h, show time |
| 2-3 | Quick Add Buttons | 7 text buttons in 2-row grid |
| 2-4 | Today's Log | Scrollable list of today's records |

### Phase 3: Recording Flow

| # | Ticket | Details |
|---|--------|---------|
| 3-1 | Size Selection Sheet | Bottom sheet with 150/250/350ml options |
| 3-2 | Save to Database | SQLite insert, Zustand update |
| 3-3 | Toast Notification | Success message at screen top |
| 3-4 | Cutoff Warning | iOS Alert after size selection |

### Phase 4: History Screen

| # | Ticket | Details |
|---|--------|---------|
| 4-1 | Grouped List | SectionList with date headers |
| 4-2 | Swipe Delete | Left swipe, no confirmation |
| 4-3 | Paywall Boundary | 🔒 header for 7+ days ago |

### Phase 5: Settings

| # | Ticket | Details |
|---|--------|---------|
| 5-1 | Settings List | Grouped list with sections |
| 5-2 | Goal Editors | Modal with slider/picker |
| 5-3 | Unit Toggle | ml/oz switch, display conversion |
| 5-4 | Subscription Link | Navigate to paywall |

### Phase 6: Onboarding

| # | Ticket | Details |
|---|--------|---------|
| 6-1 | Welcome Screen | App intro, feature bullets |
| 6-2 | Water Goal Setup | Slider for ml target |
| 6-3 | Bedtime Setup | Time picker |
| 6-4 | Skip Handling | AsyncStorage flag, defaults |

### Phase 7: Pro Features

| # | Ticket | Details |
|---|--------|---------|
| 7-1 | RevenueCat Setup | SDK init, entitlements |
| 7-2 | Custom Drink Form | Name + caffeine toggle + mg input |
| 7-3 | Paywall Screen | RevenueCat PaywallUI |
| 7-4 | Restore Purchases | Restore button handling |

### Phase 8: i18n

| # | Ticket | Details |
|---|--------|---------|
| 8-1 | i18n Config | expo-localization setup |
| 8-2 | Translation Files | en.json, ja.json |
| 8-3 | Apply Translations | Replace hardcoded strings |

### Phase 9: Polish

| # | Ticket | Details |
|---|--------|---------|
| 9-1 | Daily Reset | 00:00 record reset logic |
| 9-2 | Error Handling | Try-catch, error UI |
| 9-3 | App Assets | Icon, splash screen |
| 9-4 | Store Prep | Screenshots, metadata |
```
