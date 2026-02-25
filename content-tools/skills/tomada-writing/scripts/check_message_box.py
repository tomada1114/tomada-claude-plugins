#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
メッセージボックス（:::message）チェックスクリプト
Zennの特殊なMarkdown構文である:::messageボックスの品質を評価する

学び（2026-01-22）:
- :::messageボックスは「特別な枠」として表示されるため、短くすべき
- 見出しや箇条書きを入れない
- 詳細な説明が必要な場合は、ボックスの外に書くか別記事リンクで対応
"""

import sys
import re
import json
import io

# 標準出力をUTF-8に設定
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def extract_message_boxes(content):
    """:::messageボックスを抽出"""
    boxes = []
    lines = content.split('\n')

    in_message_box = False
    current_box = {
        "start_line": 0,
        "end_line": 0,
        "content_lines": [],
        "raw_content": ""
    }

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # メッセージボックスの開始
        if stripped.startswith(':::message'):
            in_message_box = True
            current_box = {
                "start_line": i,
                "end_line": 0,
                "content_lines": [],
                "raw_content": ""
            }
            continue

        # メッセージボックスの終了
        if in_message_box and stripped == ':::':
            in_message_box = False
            current_box["end_line"] = i
            current_box["raw_content"] = '\n'.join(current_box["content_lines"])
            boxes.append(current_box)
            continue

        # メッセージボックス内のコンテンツ
        if in_message_box:
            current_box["content_lines"].append(line)

    return boxes


def check_message_box_quality(box):
    """個別のメッセージボックスの品質をチェック"""
    issues = []
    content_lines = box["content_lines"]
    raw_content = box["raw_content"]
    start_line = box["start_line"]

    # 空行を除いた実質的な行数
    non_empty_lines = [line for line in content_lines if line.strip()]
    line_count = len(non_empty_lines)

    # 文字数（空白・改行除く）
    char_count = len(raw_content.replace('\n', '').replace(' ', ''))

    # 1. 行数チェック（5行以下が理想）
    if line_count > 5:
        issues.append({
            "type": "too_many_lines",
            "start_line": start_line,
            "actual_lines": line_count,
            "recommended_max": 5,
            "severity": "high",
            "message": f"メッセージボックス（行{start_line}）が{line_count}行あります。5行以下が推奨です。"
        })

    # 2. 文字数チェック（200文字以下が理想）
    if char_count > 200:
        issues.append({
            "type": "too_many_chars",
            "start_line": start_line,
            "actual_chars": char_count,
            "recommended_max": 200,
            "severity": "medium",
            "message": f"メッセージボックス（行{start_line}）が{char_count}文字あります。200文字以下が推奨です。"
        })

    # 3. 見出し（**太字**で始まる行）チェック
    heading_pattern = re.compile(r'^\*\*(.+?)\*\*\s*$')
    for i, line in enumerate(content_lines):
        stripped = line.strip()
        if heading_pattern.match(stripped):
            issues.append({
                "type": "heading_in_box",
                "start_line": start_line,
                "content_line": start_line + i + 1,
                "content": stripped,
                "severity": "high",
                "message": f"メッセージボックス（行{start_line}）内に見出しがあります（行{start_line + i + 1}）。見出しは外に出してください。"
            })

    # 4. 箇条書きチェック
    bullet_count = 0
    for i, line in enumerate(content_lines):
        stripped = line.strip()
        if stripped.startswith('- ') or stripped.startswith('* ') or stripped.startswith('+ '):
            bullet_count += 1

    if bullet_count >= 3:
        issues.append({
            "type": "bullet_list_in_box",
            "start_line": start_line,
            "bullet_count": bullet_count,
            "severity": "high",
            "message": f"メッセージボックス（行{start_line}）内に{bullet_count}個の箇条書きがあります。箇条書きはボックス外に出すか、短く要約してください。"
        })
    elif bullet_count >= 1:
        issues.append({
            "type": "bullet_in_box",
            "start_line": start_line,
            "bullet_count": bullet_count,
            "severity": "low",
            "message": f"メッセージボックス（行{start_line}）内に箇条書きがあります。できればボックス外に出すことを検討してください。"
        })

    # 5. ネストされた見出し（### や ####）チェック
    for i, line in enumerate(content_lines):
        stripped = line.strip()
        if re.match(r'^#{2,}\s+', stripped):
            issues.append({
                "type": "markdown_heading_in_box",
                "start_line": start_line,
                "content_line": start_line + i + 1,
                "content": stripped,
                "severity": "high",
                "message": f"メッセージボックス（行{start_line}）内にMarkdown見出しがあります（行{start_line + i + 1}）。見出しは外に出してください。"
            })

    return issues


def check_message_boxes(content):
    """全てのメッセージボックスをチェック"""
    boxes = extract_message_boxes(content)

    all_issues = []
    for box in boxes:
        issues = check_message_box_quality(box)
        all_issues.extend(issues)

    # スコア計算
    score = 100
    for issue in all_issues:
        if issue["severity"] == "high":
            score -= 15
        elif issue["severity"] == "medium":
            score -= 8
        elif issue["severity"] == "low":
            score -= 3

    return {
        "score": max(0, score),
        "box_count": len(boxes),
        "issues": all_issues,
        "stats": {
            "total_boxes": len(boxes),
            "boxes_with_issues": len(set(issue["start_line"] for issue in all_issues))
        }
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_message_box.py <markdown_file> [--fix]")
        sys.exit(1)

    filepath = sys.argv[1]

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        result = check_message_boxes(content)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
