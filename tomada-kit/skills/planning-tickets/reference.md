# planning-tickets Reference

SKILL.md の原則を運用に落とすときの手順とコマンド。

## 作成順序と番号の埋め戻し

Issue 番号は作成するまで確定しないため、一発で正しい相互参照は書けない。二段構えにする:

1. **全チケットの本文をローカルファイルに書き切る**(1 チケット 1 ファイル、`NNN-<slug>.md`。NNN は依存順の仮 ID)。依存は仮 ID で書く(`Depends on 010` など)
2. **依存順(基盤 → 並列 → 統合)に作成**: `gh issue create --title "..." --body-file NNN-<slug>.md --label ...`。作成のたびに仮 ID → 実番号の対応を記録する
3. **実番号に置換して埋め戻す**: 全本文の Depends on / Blocks を実番号に置換し、`gh issue edit <番号> --body-file <更新済みファイル>` で更新する。基盤チケットの `Blocks #N` は作成時点では書けないので、この埋め戻しが必須になる
4. **検証**: `gh issue list --json number,title,labels` で件数・タイトル接頭辞・ラベルを確認し、基盤チケット 1 件を `gh issue view` して Blocks が実番号になっていることを見る

## ラベルとマイルストーン

リポジトリに初回だけ作成する:

```bash
gh label create "foundation"  --color "5319E7" --description "Must complete before parallel work"
gh label create "parallel"    --color "0E8A16" --description "Can work in parallel"
gh label create "integration" --color "FBCA04" --description "Connects multiple components"
gh label create "blocked"     --color "B60205" --description "Waiting on dependency completion"
```

マイルストーンを使う場合(フェーズ単位を推奨):

```bash
gh api repos/{owner}/{repo}/milestones -f title="M1: Core" -f description="..."
gh issue create ... --milestone "M1: Core"
```

## サイズ調整の目安

- **適正**: 単一責務、1〜3 時間、2〜5 ファイル、受け入れ条件 3〜5 個、独立してテスト可能
- 分割すると依存が生まれるなら分割しない(独立性 > 粒度)。30 分未満の断片は関連ごと束ねる
- 「並列可」を名乗るチケット同士は変更ファイルが重ならないことを確認する。重なるなら片方に寄せるか順次にする
- 並列ストリームには必ず合流点(統合チケット)を作る — 作り忘れが最頻の欠落
