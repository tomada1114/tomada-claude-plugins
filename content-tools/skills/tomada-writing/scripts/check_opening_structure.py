#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
冒頭構成チェックスクリプト
冒頭の必須要素（挨拶、結論先出し、価値提示、要約セクション）を順序含めて評価する
"""

import sys
import re
import json
import io

# 標準出力をUTF-8に設定
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def remove_frontmatter(content):
    """frontmatterを除外"""
    return re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)


def get_opening_content(content, until_first_h2=True):
    """冒頭部分を取得（最初のH2セクションまで、または最初の500文字）"""
    clean_content = remove_frontmatter(content)

    if until_first_h2:
        # 最初のH2見出しまでを取得
        match = re.search(r'^##\s+', clean_content, re.MULTILINE)
        if match:
            return clean_content[:match.start()]

    # H2がない場合は最初の500文字
    return clean_content[:500]


def check_greeting(content):
    """挨拶をチェック"""
    opening = get_opening_content(content)

    # 挨拶パターン
    greeting_patterns = [
        r'こんにちは[、,]?\s*とまだです',
        r'とまだです[。！]',
        r'こんにちは[！。]',
    ]

    for pattern in greeting_patterns:
        match = re.search(pattern, opening[:200])  # 最初の200文字以内
        if match:
            return {
                "found": True,
                "position": match.start(),
                "match": match.group(0)
            }

    return {
        "found": False,
        "issue": {
            "type": "missing_greeting",
            "message": "冒頭に「こんにちは、とまだです」がありません。",
            "severity": "high",
            "penalty": 10
        }
    }


def check_conclusion_first(content):
    """結論先出しをチェック"""
    opening = get_opening_content(content)

    # 結論先出しパターン
    conclusion_patterns = [
        r'今回伝えたいこと[はの]',
        r'要点[はを]',
        r'一言で言[えう]ば',
        r'結論から[言いう]',
        r'先に結論',
        r'この記事の結論',
        r'端的に言[えう]ば',
    ]

    for pattern in conclusion_patterns:
        match = re.search(pattern, opening)
        if match:
            return {
                "found": True,
                "position": match.start(),
                "match": match.group(0)
            }

    return {
        "found": False,
        "issue": {
            "type": "missing_conclusion_first",
            "message": "冒頭に結論先出しがありません。「今回伝えたいことの要点は〇〇です」などを追加してください。",
            "severity": "high",
            "penalty": 10
        }
    }


def check_value_proposition(content):
    """記事の価値提示をチェック"""
    opening = get_opening_content(content)

    # 価値提示パターン
    value_patterns = [
        r'この記事では[^。]{1,50}解説',
        r'この記事では[^。]{1,50}説明',
        r'この記事では[^。]{1,50}紹介',
        r'この記事を読む[とで][^。]{1,30}',
        r'読み終わる頃には',
        r'理解できるようになります',
        r'わかるようになります',
        r'できるようになります',
        r'身につ[きく]ます',
    ]

    for pattern in value_patterns:
        match = re.search(pattern, opening)
        if match:
            return {
                "found": True,
                "position": match.start(),
                "match": match.group(0)[:50]
            }

    return {
        "found": False,
        "issue": {
            "type": "missing_value_proposition",
            "message": "記事の価値提示がありません。「この記事では〜を解説します」「読み終わる頃には〜できるようになります」などを追加してください。",
            "severity": "medium",
            "penalty": 5
        }
    }


def check_summary_section(content):
    """要約セクションをチェック"""
    clean_content = remove_frontmatter(content)

    # 要約セクションパターン
    summary_patterns = [
        r'##\s*忙しい人のために要約',
        r'##\s*要約',
        r'##\s*まず結論',
        r'##\s*TL;DR',
        r'##\s*この記事のポイント',
    ]

    for pattern in summary_patterns:
        match = re.search(pattern, clean_content[:1500])  # 最初の1500文字以内
        if match:
            return {
                "found": True,
                "position": match.start(),
                "match": match.group(0)
            }

    return {
        "found": False,
        "issue": {
            "type": "missing_summary_section",
            "message": "「忙しい人のために要約」セクションがありません。冒頭付近に追加してください。",
            "severity": "high",
            "penalty": 8
        }
    }


def check_opening_order(elements):
    """冒頭要素の順序をチェック"""
    issues = []

    # 期待される順序: 挨拶 → 結論先出し → 価値提示 → 要約
    order_checks = [
        ("greeting", "conclusion_first", "挨拶の後に結論先出し"),
        ("conclusion_first", "value_proposition", "結論先出しの後に価値提示"),
    ]

    for first, second, description in order_checks:
        first_elem = elements.get(first)
        second_elem = elements.get(second)

        if first_elem and second_elem:
            if first_elem.get("found") and second_elem.get("found"):
                if first_elem.get("position", 0) > second_elem.get("position", 0):
                    issues.append({
                        "type": "wrong_order",
                        "message": f"冒頭要素の順序が推奨と異なります: {description}が期待されます。",
                        "severity": "low",
                        "penalty": 3
                    })

    return issues


def check_opening_structure(content):
    """冒頭構成の全要素をチェック"""
    all_issues = []
    elements = {}
    score = 100

    # 1. 挨拶チェック
    result = check_greeting(content)
    elements["greeting"] = result
    if not result.get("found"):
        all_issues.append(result["issue"])

    # 2. 結論先出しチェック
    result = check_conclusion_first(content)
    elements["conclusion_first"] = result
    if not result.get("found"):
        all_issues.append(result["issue"])

    # 3. 価値提示チェック
    result = check_value_proposition(content)
    elements["value_proposition"] = result
    if not result.get("found"):
        all_issues.append(result["issue"])

    # 4. 要約セクションチェック
    result = check_summary_section(content)
    elements["summary_section"] = result
    if not result.get("found"):
        all_issues.append(result["issue"])

    # 6. 順序チェック
    order_issues = check_opening_order(elements)
    all_issues.extend(order_issues)

    # スコア計算
    for issue in all_issues:
        score -= issue.get('penalty', 5)

    # 統計情報
    stats = {
        "greeting_found": elements.get("greeting", {}).get("found", False),
        "conclusion_first_found": elements.get("conclusion_first", {}).get("found", False),
        "value_proposition_found": elements.get("value_proposition", {}).get("found", False),
        "summary_section_found": elements.get("summary_section", {}).get("found", False),
        "elements_found": sum(1 for e in elements.values() if e.get("found", False)),
        "total_elements": 4
    }

    return {
        "score": max(0, score),
        "issues": all_issues,
        "elements": elements,
        "stats": stats
    }


def main():
    if len(sys.argv) != 2:
        print("Usage: python check_opening_structure.py <markdown_file>")
        sys.exit(1)

    filepath = sys.argv[1]

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        result = check_opening_structure(content)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
