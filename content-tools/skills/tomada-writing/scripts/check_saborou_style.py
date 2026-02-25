#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文体スタイルチェックスクリプト v1.1
とまだ式文体スタイル（結論先出し、両面提示、疑問先回り）を検出・評価する

v1.1変更点:
- 括弧補足チェックはスコアに影響させない（統計情報としてのみ保持）
"""

import sys
import re
import json
import io

# 標準出力をUTF-8に設定
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def remove_frontmatter_and_code_blocks(content):
    """frontmatterとコードブロックを除外"""
    content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)
    content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
    return content


def get_opening_section(content, max_paragraphs=10):
    """冒頭セクションを取得（最初の10段落）"""
    clean_content = remove_frontmatter_and_code_blocks(content)
    paragraphs = re.split(r'\n\n+', clean_content)

    # 見出しを除いた段落を取得
    text_paragraphs = []
    for para in paragraphs:
        stripped = para.strip()
        if stripped and not stripped.startswith('#'):
            text_paragraphs.append(stripped)
        if len(text_paragraphs) >= max_paragraphs:
            break

    return '\n\n'.join(text_paragraphs)


def check_conclusion_first(content):
    """結論先出しをチェック"""
    issues = []
    findings = []

    # 結論先出しのパターン
    conclusion_patterns = [
        r'今回伝えたいこと[はの]',
        r'要点[はを]',
        r'一言で言[えう]ば',
        r'結論から[言いう]',
        r'先に結論',
        r'端的に言[えう]ば',
        r'この記事の結論',
        r'まず結論',
    ]

    opening = get_opening_section(content, max_paragraphs=5)

    found = False
    for pattern in conclusion_patterns:
        match = re.search(pattern, opening)
        if match:
            found = True
            findings.append({
                "type": "conclusion_first",
                "pattern": pattern,
                "match": match.group(0),
                "position": "opening"
            })
            break

    if not found:
        issues.append({
            "type": "missing_conclusion_first",
            "message": "冒頭に結論先出しがありません。「今回伝えたいことの要点は〇〇です」などの表現を追加してください。",
            "severity": "high",
            "penalty": 10
        })

    return issues, findings


def check_both_sides_presentation(content):
    """両面提示をチェック"""
    issues = []
    findings = []

    clean_content = remove_frontmatter_and_code_blocks(content)

    # 両面提示のパターン
    both_sides_patterns = [
        (r'一方で', '一方で'),
        (r'ただ[、,]', 'ただ'),
        (r'とはいえ', 'とはいえ'),
        (r'ただし[、,]', 'ただし'),
        (r'しかし[、,]', 'しかし'),
        (r'デメリット', 'デメリット'),
        (r'注意点', '注意点'),
        (r'限界', '限界'),
        (r'課題', '課題'),
    ]

    found_count = 0
    found_expressions = []

    for pattern, name in both_sides_patterns:
        matches = list(re.finditer(pattern, clean_content))
        if matches:
            found_count += len(matches)
            found_expressions.append(name)
            findings.append({
                "type": "both_sides",
                "expression": name,
                "count": len(matches)
            })

    # 1記事に最低1箇所の両面提示が必要
    if found_count == 0:
        issues.append({
            "type": "missing_both_sides",
            "message": "両面提示がありません。「一方で」「ただ」「とはいえ」などを使って、メリットだけでなくデメリットや注意点も示してください。",
            "severity": "high",
            "penalty": 8
        })
    elif found_count < 2:
        issues.append({
            "type": "insufficient_both_sides",
            "message": f"両面提示が{found_count}箇所のみです。2箇所以上が推奨されます。",
            "severity": "medium",
            "penalty": 4
        })

    return issues, findings


def check_anticipate_questions(content):
    """読者の疑問先回りをチェック"""
    issues = []
    findings = []

    clean_content = remove_frontmatter_and_code_blocks(content)

    # 疑問先回りのパターン
    anticipate_patterns = [
        r'と思った方もいるかもしれません',
        r'と思われるかもしれません',
        r'と疑問に思う方',
        r'と感じた方',
        r'という疑問',
        r'ここで疑問',
        r'なぜ[^。]{1,20}と思う方',
        r'「[^」]{1,30}？」と',
        r'「[^」]{1,30}では？」',
    ]

    found_count = 0

    for pattern in anticipate_patterns:
        matches = list(re.finditer(pattern, clean_content))
        if matches:
            found_count += len(matches)
            for match in matches:
                findings.append({
                    "type": "anticipate_question",
                    "match": match.group(0)[:50],
                    "position": match.start()
                })

    # 疑問先回りはオプション（検出するがペナルティなし）
    # 冗長になりがちなので、必須としない

    return issues, findings


def check_parenthetical_notes(content):
    """括弧による補足・本音をチェック"""
    issues = []
    findings = []

    clean_content = remove_frontmatter_and_code_blocks(content)

    # 括弧補足のパターン（本文中の括弧、コード内の括弧は除外）
    # 日本語の括弧（）を検出
    parenthetical_pattern = r'（[^）]{5,100}）'

    matches = list(re.finditer(parenthetical_pattern, clean_content))

    # 本音・補足として機能している括弧をカウント
    valid_parentheticals = []
    for match in matches:
        text = match.group(0)
        # プログラミング用語や技術的な括弧は除外
        if not re.search(r'[a-zA-Z]{3,}', text):  # 英語3文字以上を含まない
            valid_parentheticals.append(text)
            findings.append({
                "type": "parenthetical_note",
                "content": text[:50],
                "position": match.start()
            })

    count = len(valid_parentheticals)

    # 2-4個が理想
    if count == 0:
        issues.append({
            "type": "no_parenthetical_notes",
            "message": "括弧による補足・本音がありません。「（正直私もまだ模索中ですが）」のような表現を1-2個追加してください。",
            "severity": "low",
            "penalty": 3
        })
    elif count > 6:
        issues.append({
            "type": "excessive_parenthetical_notes",
            "message": f"括弧補足が{count}個と多すぎます。2-4個程度が推奨されます。",
            "severity": "low",
            "penalty": 2
        })

    return issues, findings


def check_saborou_style(content):
    """とまだ式文体スタイルの全要素をチェック"""
    all_issues = []
    all_findings = []
    score = 100

    # 1. 結論先出しチェック
    issues, findings = check_conclusion_first(content)
    all_issues.extend(issues)
    all_findings.extend(findings)

    # 2. 両面提示チェック
    issues, findings = check_both_sides_presentation(content)
    all_issues.extend(issues)
    all_findings.extend(findings)

    # 3. 疑問先回りチェック
    issues, findings = check_anticipate_questions(content)
    all_issues.extend(issues)
    all_findings.extend(findings)

    # 4. 括弧補足チェック（統計情報のみ、スコアには影響させない）
    parenthetical_issues, parenthetical_findings = check_parenthetical_notes(content)
    # issuesはスコアに影響させないため、all_issuesには追加しない
    # findingsは統計情報として保持
    all_findings.extend(parenthetical_findings)

    # スコア計算（括弧補足以外のissuesのみ）
    for issue in all_issues:
        score -= issue.get('penalty', 5)

    # 統計情報
    stats = {
        "conclusion_first_found": any(f['type'] == 'conclusion_first' for f in all_findings),
        "both_sides_count": sum(1 for f in all_findings if f['type'] == 'both_sides'),
        "anticipate_questions_count": sum(1 for f in all_findings if f['type'] == 'anticipate_question'),
        "parenthetical_notes_count": sum(1 for f in all_findings if f['type'] == 'parenthetical_note')
    }

    return {
        "score": max(0, score),
        "issues": all_issues,
        "findings": all_findings,
        "stats": stats,
        "info": {
            "parenthetical_notes": parenthetical_issues  # 参考情報として保持
        }
    }


def main():
    if len(sys.argv) != 2:
        print("Usage: python check_saborou_style.py <markdown_file>")
        sys.exit(1)

    filepath = sys.argv[1]

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        result = check_saborou_style(content)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
