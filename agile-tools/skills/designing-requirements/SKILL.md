---
name: designing-requirements
description: Transform rough product ideas into detailed, implementation-ready requirements. Acts as PdM and UI/UX designer to clarify ambiguous points, design screens, and create ticket breakdowns. Use PROACTIVELY when user mentions requirements, specs, PRD, wireframe, UI design, UX flow, product idea, feature planning, ticket breakdown, or asks to refine/detail app ideas. Examples: <example>Context: User has rough idea user: 'Help me refine this app spec' assistant: 'I will use designing-requirements skill' <commentary>Triggered by spec refinement request</commentary></example> <example>Context: Planning phase user: 'Let's detail the requirements' assistant: 'I will use designing-requirements skill' <commentary>Triggered by requirements detailing</commentary></example>
---

# Product Requirements Designer

Transform rough product ideas and memos into detailed, implementation-ready requirements through structured questioning and UI/UX design.

## When to Use This Skill

Use PROACTIVELY when:
- User has a rough product idea or feature memo to refine
- Requirements need to be detailed for ticket creation
- UI/UX decisions need to be made
- Screen layouts and user flows need to be designed
- Implementation tickets need to be broken down
- User mentions: requirements, PRD, wireframe, UI, UX, specs, tickets

## Workflow Overview

```
Phase 1: Read & Understand
    ↓
Phase 2: Identify Ambiguities
    ↓
Phase 3: Question Rounds (AskUserQuestion)
    ↓
Phase 4: Document Updates
    ↓
Phase 5: Ticket Breakdown
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
| Touch Targets | Are all interactive elements ≥44x44pt? |
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
- サイズ選択UIはどのような形式？
  → Bottom Sheet / Modal / Inline Expansion

- ボタンのデザインは？
  → アイコン+テキスト / アイコンのみ / テキストのみ

- リストの表示形式は？
  → グループ化 / フラット
```

**Behavior Questions:**
```
- 100%を超えた場合の表示は？
  → 100%で止める / 超過分を別色 / リング形式

- 削除時の確認は？
  → 確認あり / 確認なし

- エラー時の挙動は？
  → 警告して続行 / ブロック
```

**Navigation Questions:**
```
- 画面へのアクセス方法は？
  → タブバー / ヘッダーアイコン / 画面内リンク

- オンボーディングのステップ数は？
  → 1画面 / 3ステップ / 4ステップ
```

**Pro/Free Questions:**
```
- Paywall表示タイミングは？
  → 機能タップ時 / 境界到達時

- PaywallのUIは？
  → SDK標準 / カスタム
```

**Mobile UX Questions (CRITICAL for mobile apps):**
```
- 主要アクションボタンの配置は？
  → 画面下部（Thumb-Zone）に固定 / 画面中央 / コンテンツ内

- ローディング表示の形式は？
  → シンプルスピナー / Skeleton Screen / コンテンツのShimmer

- Haptic Feedback（振動フィードバック）は？
  → 実装する（記録成功、警告時）/ 実装しない
```

**Accessibility Questions (MUST ASK):**
```
- アクセシビリティ要件は？
  → WCAG AA準拠 / 基本対応のみ / MVP対象外

- VoiceOver/TalkBack対応は？
  → フル対応 / 基本対応（accessibilityLabel）/ MVP対象外
```

**Error Prevention Questions:**
```
- 削除操作のUXは？
  → 即削除（確認なし）/ Undo付きToast / 確認ダイアログ

- バリデーションルールを詳細定義しますか？
  → 定義する（文字数、範囲など明記）/ 実装時に決定

- エラー表示の形式は？
  → Toast / Alert / インラインメッセージ
```

**Visual Design Questions:**
```
- ダークモード対応は？
  → ライトモードのみ（MVP）/ システム設定に自動追従 / 手動切替

- Empty State（データなし時）の表示は？
  → シンプルテキスト / アイコン＋テキスト / CTA付き
```

## Phase 4: Document Updates

After gathering all answers, update the requirements document:

### 4.1 機能定義の詳細化

For each feature section, add:
- Detailed specifications
- UI behavior descriptions
- Edge case handling
- Default values

### 4.2 ワイヤーフレーム追加

Create ASCII wireframes for each screen:

```
┌─────────────────────────────────┐
│  App Title              [⚙️]   │  ← Header with action
├─────────────────────────────────┤
│                                 │
│  Section Content               │
│  ████████████░░░░░░  60%       │  ← Progress indicator
│                                 │
├─────────────────────────────────┤
│  [Button 1] [Button 2] [+]     │  ← Action buttons
├──────────┬──────────────────────┤
│  [Tab 1]  │     [Tab 2]        │  ← Tab bar
└──────────┴──────────────────────┘
```

### 4.3 フロー図追加

Document user flows:

```
1. User taps button
2. Bottom Sheet appears with options
3. User selects option
4. Record saved → Toast notification
5. UI updates with new data
```

### 4.4 横断的セクションの追加（REQUIRED）

Based on user decisions, add these cross-cutting sections to the requirements:

**エラーハンドリング（Error Handling）:**
```markdown
### X.X エラーハンドリング

#### DB保存エラー
- **形式**: Toast / Alert
- **メッセージ**: 「保存に失敗しました」
- **リトライ**: 自動 / 手動

#### ネットワークエラー
- **形式**: Alert with retry
- **メッセージ**: 具体的なエラー内容
```

**アクセシビリティ（Accessibility）:**
```markdown
### X.X アクセシビリティ

#### 基本要件（WCAG 2.1 AA準拠）
- **コントラスト比**: テキスト 4.5:1以上
- **タッチターゲット**: 44x44pt以上
- **accessibilityLabel**: 全インタラクティブ要素に必須

#### VoiceOver対応
- accessibilityRole設定
- 状態変化のアナウンス
```

**ローディング・フィードバック:**
```markdown
### X.X フィードバック

#### ローディング
- **形式**: Spinner / Skeleton / Shimmer
- **表示**: 配置位置、オーバーレイ有無

#### 成功フィードバック
- **形式**: Toast通知
- **Haptic**: Light / Medium / None
```

## Phase 5: Ticket Breakdown

Create implementation tickets organized by phase:

### Phase Structure Template

```markdown
### Phase N: [Phase Name]

| # | Ticket | Details |
|---|--------|---------|
| N-1 | Ticket Name | Technical requirements |
| N-2 | Ticket Name | Technical requirements |
```

### Recommended Phases

1. **Foundation** - DB schema, state management, navigation
2. **Core UI** - Main screen components
3. **Core Features** - Primary functionality
4. **Secondary Features** - Supporting functionality
5. **Settings** - Configuration screens
6. **Onboarding** - First-run experience
7. **Monetization** - Pro features, paywalls
8. **i18n** - Internationalization
9. **Polish** - Error handling, assets, store prep

## Best Practices

### Questioning

- Ask questions in rounds of 3-4 related topics
- Always provide 2-4 concrete options
- Include trade-off descriptions
- Don't ask about obvious decisions
- Skip questions if the document is already clear

### Wireframes

- Use ASCII art for quick visualization
- Keep wireframes simple but complete
- Show key UI elements and their positions
- Annotate with arrows and comments

### Documentation

- Be specific, not vague
- Include default values
- Document edge cases
- Cross-reference related sections

### Tickets

- One ticket = one deployable unit
- Include technical requirements
- Order by dependency
- Group by development phase

## Templates

See the templates directory for:
- [requirements-section.md](templates/requirements-section.md) - Feature section template
- [wireframe-patterns.md](templates/wireframe-patterns.md) - Common UI patterns
- [ticket-breakdown.md](templates/ticket-breakdown.md) - Ticket structure template

## AI Assistant Instructions

When this skill is activated:

### DO:
1. **Read first** - Always read the requirements document before asking questions
2. **Use AskUserQuestion** - Proactively clarify ambiguities
3. **Batch questions** - Group related questions (max 4 per round)
4. **Provide options** - Always give concrete choices, not open-ended questions
5. **Create wireframes** - Use ASCII art for all screens
6. **Update systematically** - Edit the document section by section
7. **Create ticket breakdown** - Always end with implementation tickets
8. **Track progress** - Use TodoWrite to track phases

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
4. Skip wireframe creation
5. Leave edge cases undefined
6. Create overly granular tickets
7. **Skip Mobile UX checks** - These are often overlooked but critical
8. **Skip Accessibility checks** - WCAG compliance should be decided early
9. **Skip Error Handling UX** - Every app needs clear error feedback

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
