# 変換ルール集（Claude ⇄ 両対応）

対象スキルの SKILL.md 本文・参照を「Claude でも Codex でも破綻しない」形に書き換える具体ルール。**事実・手順・コード・固有名詞・意味は変えない**。変えるのは「プラットフォーム依存の表現と配置」だけ。

## 目次
- [R1 frontmatter](#r1-frontmatter)
- [R2 ハードコードパス→相対](#r2-ハードコードパス相対)
- [R3 オーケストレーション→条件分岐表現](#r3-オーケストレーション条件分岐表現)
- [R4 依存サブエージェント抽出](#r4-依存サブエージェント抽出)
- [R5 cross-skill 参照の解決](#r5-cross-skill-参照の解決)
- [R6 AskUserQuestion](#r6-askuserquestion)
- [R7 MCP ツール](#r7-mcp-ツール)
- [R8 Claude専用として残す](#r8-claude専用として残す)
- [R9 オーケストレーション文脈ロジック](#r9-オーケストレーション文脈ロジック)
- [R10 サブエージェントへのパス受け渡し（最重要）](#r10-サブエージェントへのパス受け渡し最重要)
- [条件分岐表現の書式（重要）](#条件分岐表現の書式重要)
- [劣化注記フォーマット](#劣化注記フォーマット)

## R1 frontmatter
- `name` / `description` は保持。`description` に**両プラットフォーム分のトリガー語**を含める（日本語・英語両方）。
- Claude 専用フィールド（`allowed-tools` 等）は**残してよい**（Codex は無視）。ただし `model`/`context: fork` を**本文ロジックの前提にしない**。`context: fork` は多くの場合「分離/性能のヒント」でロジック非依存 → Codex では「メインで逐次実行」と一言添えれば足り、過剰に作り込まない（L8）。
- 必要なら Codex UI 用に `metadata.short-description` を追加（任意）。
- **参照専用 hub スキル**（他スキルから `Skill`/データ参照されるだけで、ユーザーが直接呼ばない）は、`description` のトリガー語の価値が低い。トリガー整備より **`references/` のレイアウトと相対パスの正しさ**を優先する（L2）。

## R2 ハードコードパス→相対
- スキル内部参照の絶対パス（`~/.claude/skills/<self>/references/x.md`、`/Users/.../.claude/skills/<self>/scripts/y.py` 等）→ **スキルルートからの相対**（`references/x.md`, `scripts/y.py`）に直す。
- 理由: Topology A で Codex は同一実体を symlink 経由で読むため、**相対パスは両者で同一に解決**される。絶対 `.claude/` パスは（repo-scope では実体が存在するため厳密には「壊れる」とは限らないが）**scope 依存で脆く**、Codex の探索パス前提とずれる。相対化が一貫して安全（L4）。
- スクリプト起動例も相対化（SKILL.md には「スキルディレクトリ基準で `python3 scripts/...`」と明記）。`$CLAUDE_PLUGIN_ROOT` 等の Claude 専用変数は使わない。
- **注意: 呼び出し元のプロジェクトファイルを引数に取るスクリプト**（例 `scripts/check-captions.sh Articles/` — スクリプトパスは skill 基準だが `Articles/` は呼び出し元プロジェクト基準）。スクリプトパスだけ相対化すると**2 つの引数が別 cwd を前提**にして崩れる。→ 解決: ①「このコマンドは**プロジェクトルートで実行**し、スクリプトは絶対/解決済みパスで呼ぶ」と明記、または②引数側も呼び出し元基準であることをコメントで明示。hub の lint/check スクリプトで頻出（L1）。

## R3 オーケストレーション→条件分岐表現
`Task` 並列・`context: fork` 等は、**両プラットフォームで読める条件分岐文**に置換する。テンプレ（パス受け渡しは [R10] 厳守）:

```markdown
> **Claude Code**: `Task`（subagent_type: general-purpose）で次を**並列**起動。各サブエージェントには
>   `references/agents/<role>.md` を**メインが読み込み、その内容**（参照データパスは絶対化）を
>   プロンプトとして渡す（相対パスを渡さない＝[R10]）。
> **Codex / Task が無い環境**: メインが同 `references/agents/<role>.md` を skill 相対で読み、
>   手順を**逐次インライン**実行する（並列性は失われる→[劣化注記]）。
```

- 構造は両対応で維持：**サブエージェントは互いに会話しない・メインが統合**。
- ただし**並列性には 2 種**ある。混同しない（L11）:
  - **速度のための並列**（独立 fan-out）→ Codex で**逐次化して安全**。
  - **正しさのためのフェーズ順序**（例 Phase1 の結果を Phase2 が使う）→ **必ず順序を保持**。Codex でもフェーズ直列は維持し、その旨を明記。「逐次化＝所要時間増」だけと捉えてフェーズ順序まで崩さない。
- `/batch`・tmux 起動も同様に「Claude: …／Codex: 逐次」で二重化。

## R4 依存サブエージェント抽出
**まずサブエージェントの「種類」を見分ける（L5）。種類で戦略が変わる:**
- **(i) 登録済み Claude サブエージェント**: `.md` に frontmatter（`tools`/`model`/`color` 等）を持ち、`subagent_type` 等で**名前起動**され Claude が解決。在処は `<repo>/.claude/agents/**`・`~/.claude/agents/**`。
- **(ii) プロンプト同梱の指示ファイル**: frontmatter 無しの素の手順/チェックリスト。**メインが読んで内容を `Task` に渡す**だけ（cc-book の 5 評価器はこちら。`<skill>/agents/<name>.md` に置かれる skill-local）。

classify の dependent_subagents を**実体で確認**し、各々が (i)/(ii)/未定義 のどれかを判定してから抽出する。

**抽出と canonical（drift を作らない＝L6）:**
- **(ii) 指示ファイル**: `references/agents/<name>.md` を**唯一の canonical**にする（skill 相対パスを内蔵）。**ミラーを作らない**。SKILL.md は両プラットフォームともここを起点にする:
  - Claude: メインが `references/agents/<name>.md` を読み、**内容**を `Task` に渡す（相対パスを渡さない＝[R10]）。
  - Codex: メインが同ファイルを skill 相対で読み、逐次インライン実行。
  - → 1 ファイルで両対応、コピー無しで drift ゼロ。元の `<skill>/agents/<name>.md` が重複するなら canonical 化（`references/agents/` を正、SKILL.md の参照を統一）。
- **(i) 登録済みサブエージェント**: `.claude/agents/<name>.md` は Claude のネイティブ名前起動用に**残す**。Codex 逐次パス用に知識コピーを `references/agents/<name>.md` に抽出（起動メタ `tools`/`model`/`color` は落とす）。コピーは snapshot → 「<source> からの抜粋（更新時要同期）」と注記。
- **cross-skill サブエージェント**（別スキルの `agents/` に定義され本スキルから呼ばれる）: 定義元スキルも両対応化し、可能なら参照を一本化。コピー時は drift 注記。
- **未定義サブエージェント**（名前参照だが実体なし）: 抽出不能 → Claude 専用節（[R8]）＋「Codex では定義が必要」とユーザー報告。
- **共有サブエージェント**（複数スキルが使う）は重複コピーせず既抽出の共有 reference を指す。

## R5 cross-skill 参照の解決
cross-skill には **2 種**ある。必ず区別する:
- **(a) データ参照**: 他スキルの `references/`・`scripts/` を読む/実行（例 `cc-book-context/references/x.md`, `cc-book-context/scripts/check_ng_words.py`）。
- **(b) 実行**: `Skill` ツールで他スキルの**ワークフロー自体を起動**（例 cc-book-review が score-check を回す）。

**(a) データ参照の解決**:
- スキルルート相対 `../<other>/references/x.md`・`../<other>/scripts/y.py` に直す。
- **相互依存スキルは同じ codex dir へまとめて bridge**（hub 優先）する。`~/.codex/skills/<self>` と `~/.codex/skills/<other>` が並べば `../<other>/...` が Claude/Codex 双方で解決する（依存スキルにも `bridge_symlink.sh` を実行）。
- ※ 単一スキルだけ bridge した場合、symlink 経由の `../` 解決はツールの logical/physical 解釈に依存して不確実。**まとめて bridge** が確実。

**(b) 実行の解決**（優先順）:
0. **呼び先が「両対応化済みの独立スキル」なら、名前で参照しプラットフォームに解決させる**（Claude: `Skill` で起動／Codex: 同名スキルが bridge 済みなら起動）。inline はあくまでフォールバック（L9）。
   — オーケストレーターでは 1〜3 の「呼び先ロジックを呼び元に取り込む」発想は**誤り**（数百行の重複と即 drift）。呼び先は独立スキルのまま、呼び出し側は「両対応済みなら委譲／無ければ劣化」と書く。
1. （呼び先が小さい補助処理なら）ロジック/チェックリストを `references/agents/<name>.md` に抽出（[R4]）し、メインが逐次インライン、または
2. 呼び先が純データ hub なら必要内容を本スキルの `references/` に **inline**、または
3. どうしても無理 → **Claude 専用節**（[R8]）。

**実行オーケストレーターは「最後に」変換する（ハード前提・L10）**: 他スキルを `Skill` で回すオーケストレーターは、呼び先が bridge されるまで Codex 版が**機能しない**（黙って単一ファイルのツールに退化する）。これは最適化ではなく**前提条件**。変換時に「必要な推移的 bridge セット」を列挙し、依存を**全部先に**両対応化＋bridge してから着手する。
**依存順序**: hub → 被呼び出しスキル → オーケストレーター。
**drift**: 抽出（コピー）は snapshot。canonical を 1 つに保つため可能なら相対参照を優先し、コピー時は「<source> からの抜粋（更新時要同期）」と注記。
**user-scope ⇄ repo-scope**: 呼び先が user スキル（`~/.claude/skills/`）で呼び元が repo スキルなら**別ツリー**＝相対不可 → inline か claude-only。
**多エージェント・プロセスの inline は「本質的に劣化」（L12）**: Agent Teams を使う議論型スキルなど、**独立した複数エージェントの議論**が品質保証の核であるスキルを 1 モデルの自己レビューに inline すると、出力スキーマは同じでも**独立性という品質保証が失われる**。データファイルの inline（無損失）と区別し、**「best-effort 劣化」として必ず明示**する（黙って inline しない）。
**共有だが platform 依存の reference テキストの所有者（L3）**: 別スキルの `references/` に置かれた tmux/`AskUserQuestion` 等の Claude 専用記述は、**それを保管する hub ではなく、それを実際に使うオーケストレーター側の変換で**扱う（hub は保管庫、orchestrator が論理的所有者）。
**home 絶対パス**（`~/.claude/skills/<other>/scripts/...`）: Codex で壊れ得る → 相対化不可なら [R7] と同様にフォールバック明記。

## R6 AskUserQuestion
- 「選択肢を提示して `AskUserQuestion` で確認」→ Codex 版では「**ユーザーに通常の文章で質問し、回答を待つ**」に変換。意図（何を確認するか）は保つ。

## R7 MCP ツール
- `mcp__server__tool` 依存は、Codex 側に同名サーバがあれば動作。無い場合は**フォールバック**（CLI/手動手順）を本文に併記し、未対応を[劣化注記]。

## R8 Claude専用として残す
- 両対応化が割に合わない箇所は、見出しに `（Claude Code 専用）` を付け、Codex では読み飛ばす旨を明記して**隔離**。無理に劣化させて壊すより安全。

## R9 オーケストレーション文脈ロジック
「呼び出し元スキルの判定」「親からの隠し引数」「セッション文脈依存の分岐」等、Claude のオーケストレーション文脈に依存するロジックは Codex に等価が無い。→ 該当分岐は **Claude 専用節**（[R8]）にし、Codex 既定動作を 1 つ明示（例: 「Codex では単体実行として扱う」）。

## R10 サブエージェントへのパス受け渡し（最重要）
claude-code-guide で確認した Claude Code の確定挙動（2026）:
- **SKILL.md 本文の相対リンク**（`references/x.md` 等）は **skill ディレクトリ基準**でメインが解決する（OK）。
- **`Task` で起動したサブエージェントの cwd は「セッション cwd（= repo root）」**で、skill dir ではない（ドキュメント明記）。
- → **サブエージェントのプロンプトに skill 相対パスを渡しても、skill dir 基準では解決されない**（repo root 基準になり外れる）＝信頼不可。

**従う規則:**
1. **メインが読むファイル**（SKILL.md の相対リンク、Codex 逐次パスでメインが読む `references/...`）→ **skill 相対で OK**。
2. **`Task` サブエージェントに渡すもの** → **相対パスを渡さない**。次のどちらかにする:
   - **(推奨) 内容をインライン**: メインが `references/agents/<name>.md` を読み、**本文そのもの**をプロンプトに埋める。
   - **絶対パスを渡す**: メインが skill dir を解決し、絶対パスにしてから渡す（`${CLAUDE_SKILL_DIR}` 等の展開はメイン本文側で）。
3. サブエージェントが実行中に参照する**データパス**（指示文中の `../<other>/...` 等）も、サブエージェント cwd=repo root のため**そのままでは解決しない**。メインが渡す際に**絶対化**するか、必要データを**インライン**する。
4. Codex 逐次パスは「メインが skill 相対で読む」ので相対のままで可。

要するに: **canonical な指示は `references/agents/<name>.md` に skill 相対で 1 つ持ち、Claude `Task` へはメインが「内容（＋絶対化したデータパス）」を渡す。Codex はメインが相対で読んで逐次実行**。これで 1 ソース・drift ゼロ・両対応。

## 条件分岐表現の書式（重要）
条件分岐は**プレーンな Markdown 散文**で書く（`> **Claude Code**: … / **Codex**: …`）。`{{claude:…|codex:…}}` のような独自構文は使わない — 両プラットフォームのパーサが安全に読めるのは通常の Markdown だけ。

## 劣化注記フォーマット
SKILL.md 末尾に「Codex での制約」節を設け、失われる機能を箇条書き:

```markdown
## Codex での制約（best-effort 劣化）
- 並列 `Task` → 逐次実行（所要時間増）
- `AskUserQuestion` → 通常対話で代替
- `<MCP/tmux/...>` → <フォールバック or 未対応>
```
