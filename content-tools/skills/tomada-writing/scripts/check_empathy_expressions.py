#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
共感・トーンチェックスクリプト
共感表現、上から目線表現、励まし表現、読者配慮表現を検出・評価する
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


def check_empathy_expressions(content):
    """共感表現をチェック"""
    issues = []
    findings = []

    clean_content = remove_frontmatter_and_code_blocks(content)

    # 共感表現パターン
    # Note: 共感語尾（〜ね/〜よね）は評価対象外（自然な文章で無理に使う必要はない）
    empathy_patterns = [
        (r'困っていませんか', '共感的問いかけ'),
        (r'悩んでいませんか', '共感的問いかけ'),
        (r'迷っていませんか', '共感的問いかけ'),
        (r'難しいですよね', '共感表現'),
        (r'わかります', '共感表現'),
        # 共感語尾（ですよね/ますよね）は評価対象外とした
        (r'かもしれません', '控えめな主張'),
        (r'と思います', '控えめな主張'),
        (r'私も最初は', '経験共有'),
        (r'私も昔', '経験共有'),
        (r'私もそうでした', '経験共有'),
        (r'一緒に[^。]{1,20}ましょう', '伴走表現'),
        (r'まずは[^。]{1,20}から', 'ハードル下げ'),
    ]

    empathy_count = 0

    for pattern, category in empathy_patterns:
        matches = list(re.finditer(pattern, clean_content))
        if matches:
            empathy_count += len(matches)
            for match in matches:
                findings.append({
                    "type": "empathy",
                    "category": category,
                    "match": match.group(0)[:30],
                    "position": match.start()
                })

    # 文数をカウント
    sentences = re.split(r'[。！？]', clean_content)
    sentence_count = len([s for s in sentences if s.strip()])

    # 共感表現の割合チェック（推奨: 5-15%）
    if sentence_count > 0:
        ratio = (empathy_count / sentence_count) * 100

        if ratio < 3:
            issues.append({
                "type": "insufficient_empathy",
                "message": f"共感表現が少なめです（{empathy_count}個/{sentence_count}文 = {ratio:.1f}%）。「〜かもしれません」「〜と思います」などを増やしてください。",
                "severity": "medium",
                "penalty": 5  # ペナルティを軽減
            })
        elif ratio > 20:
            issues.append({
                "type": "excessive_empathy",
                "message": f"共感表現が多すぎます（{empathy_count}個/{sentence_count}文 = {ratio:.1f}%）。くどくなる恐れがあります。",
                "severity": "low",
                "penalty": 3
            })

    return issues, findings, empathy_count


def check_condescending_expressions(content):
    """上から目線表現をチェック"""
    issues = []
    findings = []

    clean_content = remove_frontmatter_and_code_blocks(content)

    # 上から目線表現パターン（完全NG）
    condescending_patterns = [
        (r'すべき[でだ]', 'すべき'),
        (r'当然[でだ]', '当然'),
        (r'必ず[^しでだ]', '必ず'),
        (r'常識ですが', '常識'),
        (r'素人', '素人'),
        (r'知らないと恥', '知らないと恥'),
        (r'に決まっている', '決めつけ'),
        (r'わからないのですか', '見下し'),
        (r'できないなら', '見下し'),
    ]

    condescending_count = 0

    for pattern, name in condescending_patterns:
        matches = list(re.finditer(pattern, clean_content))
        if matches:
            condescending_count += len(matches)
            for match in matches:
                findings.append({
                    "type": "condescending",
                    "expression": name,
                    "match": match.group(0),
                    "position": match.start()
                })
                issues.append({
                    "type": "condescending_expression",
                    "message": f"上から目線の表現「{match.group(0)}」があります。読者に寄り添う表現に変更してください。",
                    "severity": "high",
                    "penalty": 10
                })

    return issues, findings, condescending_count


def check_encouragement_style(content):
    """励まし表現のスタイルをチェック（事実ベースかどうか）"""
    issues = []
    findings = []

    clean_content = remove_frontmatter_and_code_blocks(content)

    # 避けるべき励まし表現（とまだ式では事実ベースに置き換える）
    avoid_patterns = [
        (r'大丈夫です[。！]', '大丈夫です'),
        (r'安心してください', '安心してください'),
        (r'心配いりません', '心配いりません'),
        (r'怖がらなくて', '怖がらなくて'),
    ]

    avoid_count = 0

    for pattern, name in avoid_patterns:
        matches = list(re.finditer(pattern, clean_content))
        if matches:
            avoid_count += len(matches)
            for match in matches:
                findings.append({
                    "type": "non_fact_based_encouragement",
                    "expression": name,
                    "position": match.start()
                })

    # 2回以上使用で警告
    if avoid_count >= 2:
        issues.append({
            "type": "non_fact_based_encouragement",
            "message": f"「大丈夫です」「安心してください」が{avoid_count}回使われています。事実ベースの説明に置き換えてください（例: 「このコマンドは3ステップで実行できます」）。",
            "severity": "medium",
            "penalty": 5
        })

    # 推奨される事実ベースの励まし
    fact_based_patterns = [
        r'ステップで[^。]{1,20}できます',
        r'手順[はで][^。]{1,30}です',
        r'〜するだけで',
        r'失敗しても[^。]{1,20}戻せる',
        r'いつでも[^。]{1,20}できる',
    ]

    fact_based_count = 0
    for pattern in fact_based_patterns:
        matches = list(re.finditer(pattern, clean_content))
        fact_based_count += len(matches)

    if fact_based_count > 0:
        findings.append({
            "type": "fact_based_encouragement",
            "count": fact_based_count
        })

    return issues, findings


def check_reader_consideration(content):
    """読者への配慮表現をチェック"""
    issues = []
    findings = []

    clean_content = remove_frontmatter_and_code_blocks(content)

    # 読者配慮表現
    consideration_patterns = [
        (r'ご存じない方', '前提確認'),
        (r'初めての方', '前提確認'),
        (r'〜をご存じでない', '前提確認'),
        (r'詳しく[^。]{1,20}解説', '丁寧な説明'),
        (r'順を追って', '段階的説明'),
        (r'ステップバイステップ', '段階的説明'),
        (r'一つずつ', '段階的説明'),
        (r'方法もあります', '選択肢の提示'),
        (r'お好みで', '選択肢の提示'),
        (r'どちらでも', '選択肢の提示'),
    ]

    consideration_count = 0

    for pattern, category in consideration_patterns:
        matches = list(re.finditer(pattern, clean_content))
        if matches:
            consideration_count += len(matches)
            for match in matches:
                findings.append({
                    "type": "reader_consideration",
                    "category": category,
                    "match": match.group(0)[:30]
                })

    # 記事全体で少なくとも2箇所の配慮表現を推奨
    if consideration_count == 0:
        issues.append({
            "type": "no_reader_consideration",
            "message": "読者への配慮表現がありません。「ご存じない方のために」「方法もあります」などを追加してください。",
            "severity": "low",
            "penalty": 3
        })

    return issues, findings, consideration_count


def check_tone_and_empathy(content):
    """トーンと共感表現の全要素をチェック"""
    all_issues = []
    all_findings = []
    score = 100

    # 1. 共感表現チェック
    issues, findings, empathy_count = check_empathy_expressions(content)
    all_issues.extend(issues)
    all_findings.extend(findings)

    # 2. 上から目線表現チェック
    issues, findings, condescending_count = check_condescending_expressions(content)
    all_issues.extend(issues)
    all_findings.extend(findings)

    # 3. 励まし表現スタイルチェック
    issues, findings = check_encouragement_style(content)
    all_issues.extend(issues)
    all_findings.extend(findings)

    # 4. 読者配慮表現チェック
    issues, findings, consideration_count = check_reader_consideration(content)
    all_issues.extend(issues)
    all_findings.extend(findings)

    # スコア計算
    for issue in all_issues:
        score -= issue.get('penalty', 5)

    # 統計情報
    stats = {
        "empathy_count": empathy_count,
        "condescending_count": condescending_count,
        "consideration_count": consideration_count
    }

    return {
        "score": max(0, score),
        "issues": all_issues,
        "findings": all_findings,
        "stats": stats
    }


def main():
    if len(sys.argv) != 2:
        print("Usage: python check_empathy_expressions.py <markdown_file>")
        sys.exit(1)

    filepath = sys.argv[1]

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        result = check_tone_and_empathy(content)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
