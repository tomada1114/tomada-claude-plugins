# GitHub Issue Template

`gh issue create --body-file` に渡す Issue 本文の SSOT。ゴールは「誰が(どのエージェントが)実装しても要件は絶対に満たせる」— すべての要件をソース文書由来の実値で書き、曖昧語とプレースホルダーを残さない。

セクション構成は下のスケルトンが正。ドメイン固有の要件群(UI 仕様、API 仕様、DB スキーマ仕様など)が必要な場合は、Functional Requirements の下に同形式の表を追加して拡張する — 別テンプレートは作らない。

## Issue body skeleton

````markdown
## User Story

**As a** [user type]
**I want** [goal]
**So that** [benefit]

## Background & Context

[このチケットが全体のどこに位置するか 2〜3 行。実装者が参照すべき
要件・設計文書のセクション番号を明記する(例: REQUIREMENTS.md §3.1, DESIGN.md §3.2)]

| Item | Value | Source |
|------|-------|--------|
| [要件由来の具体値をすべて列挙] | [実値] | [文書名 §x.x] |

## Functional Requirements (EARS)

| ID | Requirement | Verification |
|----|-------------|--------------|
| REQ-001 | **When** [trigger], the system shall [action]. | [検証方法] |
| REQ-002 | **While** [state], the system shall [behavior]. | [検証方法] |
| REQ-003 | **If** [error condition], **then** the system shall [recovery]. | [検証方法] |

## Boundary Conditions

| Condition | EARS Requirement |
|-----------|------------------|
| Minimum / Maximum / Empty / Over-limit / Null | **When** [境界値], the system shall [振る舞い]. |

## Concrete Examples

<!-- 最低 3 つ: happy path / boundary / error。すべて実値で書く -->

### Example 1: Happy Path — [scenario]

```
Trigger:      [具体的な操作・入力]
Pre-state:    [実値]
Action:       [実値]
Post-state:   [実値]
Verification: [確認手順]
```

## Acceptance Criteria

<!-- 全 REQ-* を網羅し、ID を対応させる。実値のない条件は書かない -->

- [ ] REQ-001: [実値つきの検証可能な条件]
- [ ] Boundary: [境界の振る舞いを検証]
- [ ] [lint / type check / test コマンド] passes

## Not In Scope

<!-- 必須。除外先の所在(別チケット番号 or 理由)を書く -->

- NOT implementing: [除外事項] → #XX が担当
- NOT handling: [エッジケース] → [将来対応。理由]

## Dependencies

<!-- 表記は必ず "Depends on #N" / "Blocks #N" — 自動化ツールが正規表現で読む。なければ "None" -->

- Depends on #XX — [必要なもの: 型 / 関数 / コンポーネント]
- Blocks #YY — [このチケットの完了を待つもの]

## Worktree (if parallel)

```bash
git worktree add ../[project]-[area] feature/issue-XX-[slug]
```
````

## バリアント(スケルトンからの差分だけ)

- **【基盤】チケット**: Functional Requirements を型・定数・スキーマの仕様表(名前 / フィールド / 制約 / 値と出典)にする。Concrete Examples は使用例コードで代替してよい。作成時点では下流の番号が未確定なので、`Blocks #N` は全チケット作成後に埋め戻す([reference.md](../reference.md) の作成順序)
- **【依存あり】統合チケット**: Background に統合フロー(A → 変換 → B)を書く。Depends on には「マージ済みであること」を明記し、Not In Scope に「接続対象コンポーネントの内部ロジックは変更しない」を含める
