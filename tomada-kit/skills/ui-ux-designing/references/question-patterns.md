# 質問パターン集

UI/UXデザインの方向性を決定するための質問パターン。AskUserQuestionツールで使用する。

## 使用原則

1. **1ラウンド3-4問まで**
2. **必ず2-4個の選択肢を提示**
3. **各選択肢にトレードオフ説明を付ける**
4. **推奨がある場合は「（推奨）」を明示**

---

## Phase 3: 方向性決定の質問

### 全体トーン

```json
{
  "question": "アプリ全体のトーン（デザインの雰囲気）はどうしますか？",
  "header": "トーン",
  "options": [
    {
      "label": "プロフェッショナル",
      "description": "落ち着いた色調、ミニマルな装飾。ビジネスツール感"
    },
    {
      "label": "フレンドリー",
      "description": "明るい色、イラストやアニメーション多め。Duolingo風"
    },
    {
      "label": "モダン・クリーン",
      "description": "白基調、アクセントカラー控えめ。Apple風"
    }
  ],
  "multiSelect": false
}
```

### カラースキーム

```json
{
  "question": "カラースキームのベースはどれが良いですか？",
  "header": "カラー",
  "options": [
    {
      "label": "ダークモード基調（推奨）",
      "description": "濃い背景にアクセントカラー。集中力向上、目に優しい"
    },
    {
      "label": "ライトモード基調",
      "description": "白/グレー基調にアクセントカラー"
    },
    {
      "label": "システム連動",
      "description": "OSのダーク/ライト設定に追従"
    }
  ],
  "multiSelect": false
}
```

### アクセントカラー

```json
{
  "question": "アクセントカラーのイメージはどれが近いですか？",
  "header": "アクセント",
  "options": [
    {
      "label": "ブルー系",
      "description": "信頼感・プロフェッショナル。テック企業で多用"
    },
    {
      "label": "グリーン系",
      "description": "成長・学習。Duolingoなど学習アプリに多い"
    },
    {
      "label": "パープル/バイオレット系",
      "description": "創造性・AI感。差別化しやすい"
    },
    {
      "label": "オレンジ/イエロー系",
      "description": "エネルギー・ポジティブ。注意を引きやすい"
    }
  ],
  "multiSelect": false
}
```

### 会話/コンテンツUI（該当する場合）

```json
{
  "question": "会話中のUIはどのスタイルが良いですか？",
  "header": "会話UI",
  "options": [
    {
      "label": "ミニマル（推奨）",
      "description": "会話中は波形アニメーションとステータスのみ。会話に集中させる"
    },
    {
      "label": "チャットバブル",
      "description": "発言がリアルタイムでテキスト表示される従来型チャットUI"
    },
    {
      "label": "ハイブリッド",
      "description": "普段はミニマル、タップでトランスクリプト表示"
    }
  ],
  "multiSelect": false
}
```

---

## Phase 4: 詳細決定の質問

### スコア/フィードバック表示

```json
{
  "question": "スコア表示のビジュアルはどの形式が良いですか？",
  "header": "スコア表示",
  "options": [
    {
      "label": "円形ゲージ（推奨）",
      "description": "複数の円形ゲージで各軸を表示。直感的"
    },
    {
      "label": "バーチャート",
      "description": "横棒グラフで各軸を比較表示"
    },
    {
      "label": "総合点のみ",
      "description": "大きな数字で1つのスコア、内訳は展開式"
    }
  ],
  "multiSelect": false
}
```

### 情報密度

```json
{
  "question": "フィードバック画面の情報密度はどの程度が良いですか？",
  "header": "情報密度",
  "options": [
    {
      "label": "コンパクト（推奨）",
      "description": "スコア+ハイライトのみ。詳細は展開式"
    },
    {
      "label": "詳細表示",
      "description": "全発言と代替表現を一度に表示"
    },
    {
      "label": "カード式",
      "description": "各発言をカードで表示、スワイプで確認"
    }
  ],
  "multiSelect": false
}
```

### 導入UI

```json
{
  "question": "セッション開始前の導入UIはどうしますか？",
  "header": "導入UI",
  "options": [
    {
      "label": "シンプル（推奨）",
      "description": "シナリオ説明+開始ボタンのみ"
    },
    {
      "label": "ブリーフィング",
      "description": "面接官の紹介、今日のトピックなどの導入"
    },
    {
      "label": "ウォームアップ",
      "description": "簡単なマイクテストなどの準備運動"
    }
  ],
  "multiSelect": false
}
```

### 終了トランジション

```json
{
  "question": "セッション終了時のトランジションはどうしますか？",
  "header": "終了演出",
  "options": [
    {
      "label": "スムーズ遷移",
      "description": "会話終了後、フェードでフィードバック画面へ"
    },
    {
      "label": "サマリーモーダル",
      "description": "モーダルで結果概要を表示、タップで詳細へ"
    },
    {
      "label": "即時表示",
      "description": "遂行なくフィードバック画面を表示"
    }
  ],
  "multiSelect": false
}
```

### アニメーション

```json
{
  "question": "アニメーション/マイクロインタラクションの程度はどうしますか？",
  "header": "アニメ",
  "options": [
    {
      "label": "最小限（推奨）",
      "description": "波形と画面遷移のみ。パフォーマンス優先"
    },
    {
      "label": "適度に使用",
      "description": "ボタン押下、スコアカウントアップ等を追加"
    },
    {
      "label": "積極的に使用",
      "description": "各所に微細な動きで体験を豊かに"
    }
  ],
  "multiSelect": false
}
```

### デバイス優先度

```json
{
  "question": "モバイルとデスクトップの優先度はどちらですか？",
  "header": "デバイス",
  "options": [
    {
      "label": "モバイルファースト",
      "description": "モバイルを主要ターゲットとして設計"
    },
    {
      "label": "デスクトップファースト",
      "description": "デスクトップを主要ターゲットとして設計"
    },
    {
      "label": "同等",
      "description": "両方を同じ重要度で設計"
    }
  ],
  "multiSelect": false
}
```

### ステータス表示（会話アプリ向け）

```json
{
  "question": "会話中のステータス表示で重要な要素はどれですか？",
  "header": "ステータス",
  "options": [
    {
      "label": "音声波形+状態テキスト",
      "description": "「聴いています...」「考え中...」などの状態表示"
    },
    {
      "label": "音声波形のみ",
      "description": "テキストなしで視覚的に状態を伝える"
    },
    {
      "label": "残りターン数も表示",
      "description": "「3/10」のように進捗も視覚化"
    }
  ],
  "multiSelect": false
}
```

---

## 汎用パターン

### 認証方式

```json
{
  "question": "MVPでのユーザー認証は必要ですか？",
  "header": "認証",
  "options": [
    {
      "label": "認証なし",
      "description": "ローカルストレージのみで履歴保存。ブラウザを変えると消える"
    },
    {
      "label": "任意認証",
      "description": "認証なしでも使えるが、ログインすれば履歴がクラウド保存"
    },
    {
      "label": "必須認証",
      "description": "使用にはGoogleログイン必須、全履歴をクラウド保存"
    }
  ],
  "multiSelect": false
}
```

### UI言語

```json
{
  "question": "UIの表示言語はMVPでどうしますか？",
  "header": "UI言語",
  "options": [
    {
      "label": "日本語のみ",
      "description": "ターゲットが日本人なのでUI日本語固定"
    },
    {
      "label": "英語のみ",
      "description": "English immersionとしてUIも英語固定"
    },
    {
      "label": "切り替え可能",
      "description": "既存の多言語対応を活用して選択可能に"
    }
  ],
  "multiSelect": false
}
```

### エラー表示

```json
{
  "question": "エラー表示の形式はどうしますか？",
  "header": "エラー表示",
  "options": [
    {
      "label": "Toast",
      "description": "画面下部に一時的なメッセージ表示。自動で消える"
    },
    {
      "label": "Alert",
      "description": "モーダルで表示。ユーザーが閉じる必要あり"
    },
    {
      "label": "インライン",
      "description": "エラー発生箇所の近くにメッセージ表示"
    }
  ],
  "multiSelect": false
}
```

### ローディング表示

```json
{
  "question": "ローディング表示の形式はどうしますか？",
  "header": "ローディング",
  "options": [
    {
      "label": "スピナー",
      "description": "シンプルな回転アイコン"
    },
    {
      "label": "スケルトン",
      "description": "コンテンツの形をグレーで表示"
    },
    {
      "label": "プログレスバー",
      "description": "進捗を横棒で表示"
    }
  ],
  "multiSelect": false
}
```

---

## 質問の組み合わせ例

### 第1ラウンド（方向性）

```
1. 全体トーン
2. カラースキーム
3. アクセントカラー
```

### 第2ラウンド（詳細 - 会話アプリ向け）

```
1. 会話UI
2. ステータス表示
3. フィードバック情報密度
```

### 第3ラウンド（体験）

```
1. 導入UI
2. 終了トランジション
3. アニメーション
4. デバイス優先度
```

### 第4ラウンド（インフラ）

```
1. 認証方式
2. UI言語
```
