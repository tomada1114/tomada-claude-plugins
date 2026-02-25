#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
太字フォーマットの問題検出・修正スクリプト
CommonMark仕様に基づき、約物との接触問題を検出・修正する
"""

import sys
import re
import json
import io

# 標準出力をUTF-8に設定
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 問題のある太字パターン（約物が強調符号に直接接触）
# CommonMark仕様では、約物に接する場合は分かち書きが必要
PROBLEMATIC_PATTERNS = {
    # 開き括弧系が**の直後にある（**「 → 「** に修正が必要）
    "opening_bracket": {
        "pattern": r'\*\*([「『（【〈《])',
        "description": "開き括弧が**の直後にあり、太字にならない可能性",
        "fix_hint": "括弧を太字の外に出す: 「**内容**」"
    },
    # 閉じ括弧系が**の直前にあり、その後に文字が続く（」**として → 」として**）
    # 連続太字パターン: 閉じ括弧の直後に次の太字が始まる
    "consecutive_bold": {
        "pattern": r'([」』）】〉》])\*\*([ぁ-んァ-ヶー一-龠a-zA-Z])',
        "description": "閉じ括弧直後に太字が連続し、レンダリングが崩れる可能性",
        "fix_hint": "連続太字を分離: 」**として → 」として**"
    },
}

# 自動修正可能なパターン
AUTO_FIX_PATTERNS = [
    # **「内容」** → 「**内容**」
    {
        "pattern": r'\*\*「([^」]+)」\*\*',
        "replacement": r'「**\1**」',
        "description": "カギ括弧を太字の外に移動"
    },
    # **『内容』** → 『**内容**』
    {
        "pattern": r'\*\*『([^』]+)』\*\*',
        "replacement": r'『**\1**』',
        "description": "二重カギ括弧を太字の外に移動"
    },
    # **（内容）** → （**内容**）
    {
        "pattern": r'\*\*（([^）]+)）\*\*',
        "replacement": r'（**\1**）',
        "description": "丸括弧を太字の外に移動"
    },
    # **(内容)** → (**内容**)
    {
        "pattern": r'\*\*\(([^\)]+)\)\*\*',
        "replacement": r'(**\1**)',
        "description": "半角丸括弧を太字の外に移動"
    },
    # **【内容】** → 【**内容**】
    {
        "pattern": r'\*\*【([^】]+)】\*\*',
        "replacement": r'【**\1**】',
        "description": "隅付き括弧を太字の外に移動"
    },
    # **〈内容〉** → 〈**内容**〉
    {
        "pattern": r'\*\*〈([^〉]+)〉\*\*',
        "replacement": r'〈**\1**〉',
        "description": "山括弧を太字の外に移動"
    },
    # **《内容》** → 《**内容**》
    {
        "pattern": r'\*\*《([^》]+)》\*\*',
        "replacement": r'《**\1**》',
        "description": "二重山括弧を太字の外に移動"
    },
    # 連続太字パターン: 」**として → 」として** (助詞を太字の外に移動)
    # よく現れる接続語・助詞パターンを安全に自動修正
    {
        "pattern": r'([」』）】〉》])\*\*(として|について|を通じて|における|と|を|に|で|が|は|も|から|まで|より|へ)',
        "replacement": r'\1\2**',
        "description": "連続太字を分離（助詞を太字の外に移動）"
    },
]


def remove_frontmatter_and_code_blocks(content):
    """frontmatterとコードブロックを除外（位置情報は保持）"""
    # frontmatterを除外（先頭の --- ... --- ブロック）
    content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)

    # コードブロックを除外（```で囲まれた部分）
    content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)

    return content


def check_bold_formatting(content):
    """太字フォーマットの問題をチェック"""
    issues = []

    # コードブロック等を除外
    clean_content = remove_frontmatter_and_code_blocks(content)

    # 問題パターンをチェック
    for name, config in PROBLEMATIC_PATTERNS.items():
        matches = list(re.finditer(config["pattern"], clean_content))
        for match in matches:
            # マッチした行を特定
            line_start = clean_content.rfind('\n', 0, match.start()) + 1
            line_end = clean_content.find('\n', match.end())
            if line_end == -1:
                line_end = len(clean_content)
            line_content = clean_content[line_start:line_end].strip()

            issues.append({
                "type": name,
                "matched": match.group(),
                "description": config["description"],
                "fix_hint": config["fix_hint"],
                "line_content": line_content[:100] + ("..." if len(line_content) > 100 else ""),
                "severity": "warning"
            })

    return issues


def get_auto_fixes(content):
    """自動修正可能な箇所を特定"""
    fixes = []

    # コードブロック等を除外
    clean_content = remove_frontmatter_and_code_blocks(content)

    for fix_config in AUTO_FIX_PATTERNS:
        matches = list(re.finditer(fix_config["pattern"], clean_content))
        for match in matches:
            original = match.group()
            fixed = re.sub(fix_config["pattern"], fix_config["replacement"], original)

            fixes.append({
                "original": original,
                "fixed": fixed,
                "description": fix_config["description"]
            })

    return fixes


def apply_fixes(content):
    """自動修正を適用（コードブロック内は除外）"""
    # コードブロックを一時的にプレースホルダーに置換
    code_blocks = []

    def save_code_block(match):
        code_blocks.append(match.group())
        return f"__CODE_BLOCK_{len(code_blocks) - 1}__"

    # frontmatterを保護
    frontmatter_match = re.match(r'^(---\n.*?\n---\n)', content, flags=re.DOTALL)
    frontmatter = ""
    if frontmatter_match:
        frontmatter = frontmatter_match.group(1)
        content = content[len(frontmatter):]

    # コードブロックを保護
    content = re.sub(r'```.*?```', save_code_block, content, flags=re.DOTALL)

    # 修正を適用
    for fix_config in AUTO_FIX_PATTERNS:
        content = re.sub(fix_config["pattern"], fix_config["replacement"], content)

    # コードブロックを復元
    for i, block in enumerate(code_blocks):
        content = content.replace(f"__CODE_BLOCK_{i}__", block)

    return frontmatter + content


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_bold_formatting.py <markdown_file> [--fix]")
        print("  --fix: Apply automatic fixes and output corrected content")
        sys.exit(1)

    filepath = sys.argv[1]
    apply_fix = "--fix" in sys.argv

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        if apply_fix:
            # 修正を適用して出力
            fixed_content = apply_fixes(content)
            fixes = get_auto_fixes(content)

            result = {
                "status": "fixed",
                "fixes_applied": len(fixes),
                "fixes": fixes,
                "fixed_content": fixed_content
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # チェックのみ
            issues = check_bold_formatting(content)
            auto_fixes = get_auto_fixes(content)

            result = {
                "status": "ok" if len(issues) == 0 else "issues_found",
                "total_issues": len(issues),
                "auto_fixable": len(auto_fixes),
                "issues": issues,
                "suggested_fixes": auto_fixes
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))

    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
