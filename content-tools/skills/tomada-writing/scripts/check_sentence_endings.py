#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文末表現バリエーションチェックスクリプト
文末表現の多様性を評価し、単調な文末の繰り返しを検出する
"""

import sys
import re
import json
import io

# 標準出力をUTF-8に設定
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 文末パターンの定義（推奨割合付き）
# Note: empathy（〜ね/〜よね）は評価対象外（自然な文章で無理に使う必要はない）
SENTENCE_ENDING_PATTERNS = {
    "basic": {
        "patterns": [r'です[。\n]', r'ます[。\n]'],
        "name": "基本形（です/ます）",
        "recommended_min": 50,
        "recommended_max": 70  # 上限を緩和（〜ね不要になった分）
    },
    "emphasis": {
        "patterns": [r'のです[。\n]', r'わけです[。\n]', r'なのです[。\n]'],
        "name": "強調形（のです/わけです）",
        "recommended_min": 5,  # 最低ラインを緩和
        "recommended_max": 20
    },
    "question": {
        "patterns": [r'でしょうか[。？\n]', r'ませんか[。？\n]', r'ですか[。？\n]', r'ますか[。？\n]'],
        "name": "問いかけ形（でしょうか/ませんか）",
        "recommended_min": 3,  # 最低ラインを緩和
        "recommended_max": 15
    },
    "reason": {
        "patterns": [r'からです[。\n]', r'ためです[。\n]', r'からでしょう[。\n]'],
        "name": "理由形（から/ため）",
        "recommended_min": 5,  # 最低ラインを緩和
        "recommended_max": 20
    }
}


def remove_frontmatter_and_code_blocks(content):
    """frontmatterとコードブロックを除外"""
    # frontmatterを除外（先頭の --- ... --- ブロック）
    content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)

    # コードブロックを除外（```で囲まれた部分）
    content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)

    return content


def extract_sentences(content):
    """文を抽出（見出し、箇条書き、空行を除外）"""
    clean_content = remove_frontmatter_and_code_blocks(content)
    lines = clean_content.split('\n')
    sentences = []

    for line in lines:
        stripped = line.strip()

        # 見出し、箇条書き、空行はスキップ
        if not stripped or stripped.startswith('#') or stripped.startswith('- ') or stripped.startswith('* '):
            continue

        # 句点で分割して文を抽出
        for sentence in re.split(r'[。！？]', stripped):
            if sentence.strip():
                sentences.append(sentence.strip())

    return sentences


def classify_sentence_ending(sentence):
    """文末パターンを分類"""
    sentence_with_period = sentence + "。"  # パターンマッチ用に句点を追加

    # 順序が重要：より具体的なパターンを先に評価する
    # 強調形・理由形は「です」を含むため、「基本形」より先に評価する必要がある
    priority_order = ["emphasis", "reason", "question", "basic"]

    for category in priority_order:
        if category in SENTENCE_ENDING_PATTERNS:
            config = SENTENCE_ENDING_PATTERNS[category]
            for pattern in config["patterns"]:
                if re.search(pattern, sentence_with_period):
                    return category

    return "other"


def check_consecutive_same_endings(sentences, max_consecutive=3):
    """同一文末の連続をチェック"""
    issues = []

    if len(sentences) < max_consecutive:
        return []

    endings = [classify_sentence_ending(s) for s in sentences]

    consecutive_count = 1
    start_idx = 0

    for i in range(1, len(endings)):
        if endings[i] == endings[i-1] and endings[i] != "other":
            consecutive_count += 1
            if consecutive_count >= max_consecutive:
                issues.append({
                    "type": "consecutive_same_ending",
                    "ending_type": SENTENCE_ENDING_PATTERNS.get(endings[i], {}).get("name", endings[i]),
                    "count": consecutive_count,
                    "start_sentence": sentences[start_idx][:50],
                    "severity": "medium"
                })
        else:
            consecutive_count = 1
            start_idx = i

    return issues


def calculate_ending_ratios(sentences):
    """文末パターンの割合を計算"""
    if not sentences:
        return {}

    counts = {cat: 0 for cat in SENTENCE_ENDING_PATTERNS.keys()}
    counts["other"] = 0

    for sentence in sentences:
        ending = classify_sentence_ending(sentence)
        counts[ending] = counts.get(ending, 0) + 1

    total = len(sentences)
    ratios = {}

    for category, count in counts.items():
        ratio = (count / total) * 100
        ratios[category] = {
            "count": count,
            "ratio": round(ratio, 1)
        }

    return ratios


def check_sentence_endings(content):
    """文末表現のバリエーションをチェック"""
    sentences = extract_sentences(content)

    if len(sentences) < 10:
        return {
            "score": 100,
            "issues": [],
            "message": "文数が少ないため評価をスキップ",
            "stats": {
                "sentence_count": len(sentences)
            }
        }

    issues = []
    score = 100

    # 文末パターンの割合を計算
    ratios = calculate_ending_ratios(sentences)

    # 各パターンの割合をチェック
    for category, config in SENTENCE_ENDING_PATTERNS.items():
        if category in ratios:
            actual_ratio = ratios[category]["ratio"]
            min_ratio = config["recommended_min"]
            max_ratio = config["recommended_max"]

            if actual_ratio < min_ratio:
                # 基本形以外で不足の場合は軽い減点
                if category != "basic":
                    penalty = 5
                    severity = "low"
                else:
                    penalty = 10
                    severity = "medium"

                issues.append({
                    "type": "insufficient_ending_variety",
                    "category": config["name"],
                    "actual_ratio": actual_ratio,
                    "recommended_min": min_ratio,
                    "recommended_max": max_ratio,
                    "severity": severity
                })
                score -= penalty

            elif actual_ratio > max_ratio:
                # 基本形が多すぎる場合は減点
                if category == "basic":
                    penalty = 10
                    severity = "medium"
                else:
                    penalty = 5
                    severity = "low"

                issues.append({
                    "type": "excessive_ending_pattern",
                    "category": config["name"],
                    "actual_ratio": actual_ratio,
                    "recommended_min": min_ratio,
                    "recommended_max": max_ratio,
                    "severity": severity
                })
                score -= penalty

    # 連続する同一文末をチェック
    consecutive_issues = check_consecutive_same_endings(sentences)
    for issue in consecutive_issues:
        issues.append({
            "type": issue["type"],
            "message": f"{issue['ending_type']}が{issue['count']}回連続しています",
            "preview": issue["start_sentence"],
            "severity": issue["severity"]
        })
        score -= 5

    return {
        "score": max(0, score),
        "issues": issues,
        "stats": {
            "sentence_count": len(sentences),
            "ratios": ratios
        }
    }


def main():
    if len(sys.argv) != 2:
        print("Usage: python check_sentence_endings.py <markdown_file>")
        sys.exit(1)

    filepath = sys.argv[1]

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        result = check_sentence_endings(content)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
