#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NGワード・NG表現の検出スクリプト
記事内の避けるべき表現を自動検出し、スコアリングする
"""

import sys
import re
import json
import io

# 標準出力をUTF-8に設定
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# NGワードリスト（ADDTIONAL_RULE準拠）
NG_WORDS = {
    "大袈裟表現": [
        # 既存
        "なんと", "驚くべき", "魔法のような", "びっくりしたのは",
        "強力な", "まるで", "驚くのは", "劇的に", "圧倒的", "革命的",
        # ADDTIONAL_RULEで追加
        "信じられない", "想像以上に", "衝撃的", "爆発的", "画期的",
        "夢のような", "絶対に", "誰でも簡単に", "最強の", "究極の"
    ],
    "過度な安心表現": [
        # 2025-11-15追加: 3回以上使用された場合に減点
        # 注: カウント方式で評価（後述のcheck_overused_words関数で処理）
    ],
    "くだけすぎ表現": [
        # 既存
        "なんです", "って何？", "でも、",
        # ADDTIONAL_RULEで追加
        "なんだけど", "ですよね？"
    ],
    "避けるべき表現": [
        # 既存
        "マスター", "というステップで", "ステップ",
        "xxxライフを", "を楽しみましょう", "楽しんでください", "を楽しんで",
        "それは、", "ですよね！", "開発ライフ", "エンジニアライフ",
        "完全理解", "完全マスター", "完璧に", "それでは、良い",
        # ADDTIONAL_RULEで追加
        "3ステップで", "さあ、始めましょう", "今すぐ始めよう",
        "挫折しない", "3ヶ月で", "1ヶ月で", "完全版"
    ],
    "読者呼称NG": [
        # 2025-12-22追加: 「あなた」は「皆さん」「開発者」「ユーザー」に置換
        "あなたは", "あなたの", "あなたが", "あなたに", "あなたも",
        "あなたにとって", "あなたへ", "あなたを"
    ],
    "著者経験の捏造": [
        "私も昔は", "以前に", "実は私も", "最初に", "昔"
    ],
    "軽すぎる表現": [
        # 既存
        "あ、",
        # ADDTIONAL_RULEで追加
        "えっ、"
    ]
}

# NGパターン（正規表現）
NG_PATTERNS = {
    "堅い敬語": r"(でございます|いたします|申し上げます)",
    # 箇条書き説明: 1行内でコロンの後に30文字以上続く場合を検出
    # 改行を含まないように修正: コロン以外→コロン→改行以外の文字30個以上→行末
    "箇条書き説明": r"^[-*]\s*[^:\n：]+[：:][^\n]{30,}$",
    "Learning Next言及": r"Learning\s*Next.*\d+.*問題",
    "過度な感嘆": r"！{2,}"
}

def remove_frontmatter_and_code_blocks(content, remove_inline_code=False):
    """frontmatterとコードブロックを除外

    Args:
        content: 元のコンテンツ
        remove_inline_code: インラインコードも除外するか（デフォルト: False）
    """
    # frontmatterを除外（先頭の --- ... --- ブロック）
    content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)

    # コードブロックを除外（```で囲まれた部分）
    content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)

    if remove_inline_code:
        # インラインコードを空白に置き換え（`で囲まれた部分）
        # 削除すると文字列が結合されて意図しないマッチが発生するため、空白に置換
        content = re.sub(r'`[^`]+`', ' ', content)

    return content

def check_overused_words(content):
    """過度に使用された安心表現をチェック（2025-11-15追加）"""
    issues = []
    score_penalty = 0

    clean_content = remove_frontmatter_and_code_blocks(content, remove_inline_code=True)

    # 過度な使用をチェックする表現リスト
    overused_checks = {
        "大丈夫": {"threshold": 2, "penalty_per_extra": 3},
        "安心": {"threshold": 2, "penalty_per_extra": 3},
        "実は": {"threshold": 2, "penalty_per_extra": 2},
        "簡単に言うと": {"threshold": 1, "penalty_per_extra": 3}
    }

    for word, config in overused_checks.items():
        count = len(re.findall(re.escape(word), clean_content))
        if count > config["threshold"]:
            extra = count - config["threshold"]
            penalty = extra * config["penalty_per_extra"]
            score_penalty += penalty
            issues.append({
                "category": "過度な安心表現",
                "word": word,
                "count": count,
                "threshold": config["threshold"],
                "penalty": penalty,
                "severity": "medium",
                "message": f"「{word}」が{count}回使用されています（推奨: {config['threshold']}回まで）"
            })

    # 組み合わせNG表現をチェック
    combo_patterns = [
        r"でも大丈夫です。実は",
        r"安心してください。実は",
        r"思ったより簡単",
        r"意外と簡単",
        r"驚くほど簡単",
        r"とても簡単",
        r"実は.*簡単",  # 「実は」と「簡単」の組み合わせ
        r"\d+分.*完了",  # 「〇分で完了」などの時間断言
        r"\d+分.*終わ",  # 「〇分で終わる」などの時間断言
        r"\d+分.*でき",  # 「〇分でできる」などの時間断言
        r"数分.*完了",   # 「数分で完了」
        r"すぐに.*完了", # 「すぐに完了」
        r"あっという間", # 「あっという間」
    ]

    for pattern in combo_patterns:
        matches = list(re.finditer(pattern, clean_content))
        if matches:
            score_penalty += len(matches) * 10  # 組み合わせは厳しく減点
            issues.append({
                "category": "過度な安心表現",
                "pattern": pattern,
                "count": len(matches),
                "penalty": len(matches) * 10,
                "severity": "high",
                "message": f"「{pattern}」のような組み合わせ表現は完全NGです"
            })

    return issues, score_penalty

def check_ng_words(content):
    """NGワード・表現をチェック"""
    issues = []
    score = 100

    # NGワードチェック用：インラインコードも除外
    clean_content = remove_frontmatter_and_code_blocks(content, remove_inline_code=True)

    # NGワードチェック
    for category, words in NG_WORDS.items():
        if category == "過度な安心表現":
            # 過度な安心表現は別関数で処理
            continue
        for word in words:
            matches = re.finditer(re.escape(word), clean_content)
            count = len(list(matches))
            if count > 0:
                issues.append({
                    "category": category,
                    "word": word,
                    "count": count,
                    "severity": "high"
                })
                score -= count * 5  # 1件につき5点減点

    # 過度な安心表現のチェック（2025-11-15追加）
    overused_issues, overused_penalty = check_overused_words(content)
    issues.extend(overused_issues)
    score -= overused_penalty

    # NGパターンチェック用：インラインコードを除外
    content_for_patterns = remove_frontmatter_and_code_blocks(content, remove_inline_code=True)

    # NGパターンチェック
    for name, pattern in NG_PATTERNS.items():
        matches = re.finditer(pattern, content_for_patterns, re.MULTILINE)
        count = len(list(matches))
        if count > 0:
            issues.append({
                "category": name,
                "pattern": pattern,
                "count": count,
                "severity": "medium"
            })
            score -= count * 3  # 1件につき3点減点

    return {
        "score": max(0, score),
        "issues": issues,
        "total_issues": len(issues)
    }

def main():
    if len(sys.argv) != 2:
        print("Usage: python check_ng_words.py <markdown_file>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        result = check_ng_words(content)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
