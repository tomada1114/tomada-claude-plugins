#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
導入フレーズチェックスクリプト
導入フレーズの使用頻度、日常的な例えの検出、説明表現を評価する
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


def check_intro_phrases(content):
    """導入フレーズの使用をチェック"""
    issues = []
    findings = []

    clean_content = remove_frontmatter_and_code_blocks(content)

    # 導入フレーズパターン
    intro_phrase_patterns = [
        # 基本的な導入表現
        (r'簡単に言[うえ]と', '簡単に言うと'),
        (r'例えば', '例えば'),
        (r'具体的に[はで]', '具体的には'),
        (r'つまり', 'つまり'),
        (r'言い換えると', '言い換えると'),
        (r'要するに', '要するに'),
        (r'実は', '実は'),
        (r'まず[、は]', 'まず'),

        # ポイント強調系
        (r'ここで[重大]要なの[はが]', 'ポイント強調'),
        (r'ポイントは', 'ポイント強調'),
        (r'重要なのは', 'ポイント強調'),
        (r'注目すべきは', 'ポイント強調'),

        # 注意形（注意・警告を促す表現）
        (r'注意が必要', '注意形'),
        (r'特に注意したいのは', '注意形'),
        (r'気をつけ[てた]', '注意形'),
        (r'注意点[はとして]', '注意形'),
        (r'忘れないで', '注意形'),

        # 補足形（特徴・役割・存在を説明する表現）
        (r'特徴があり', '補足形'),
        (r'特徴として', '補足形'),
        (r'役割を[果は]たし', '補足形'),
        (r'役割があり', '補足形'),
        (r'メリットがあり', '補足形'),
        (r'メリットとして', '補足形'),
        (r'デメリットとして', '補足形'),
        (r'理由[はとして]', '補足形'),
        (r'背景[はとして]', '補足形'),

        # とまだ式：疑問先回りパターン
        (r'と思った方も', '疑問先回り'),
        (r'と思う方も', '疑問先回り'),
        (r'と感じ[たる]方も', '疑問先回り'),
        (r'ではないでしょうか', '疑問先回り'),
        (r'かもしれません', '控えめ断定'),

        # 両面提示パターン
        (r'一方で', '両面提示'),
        (r'ただ[、し]', '両面提示'),
        (r'とはいえ', '両面提示'),
    ]

    phrase_counts = {}
    total_count = 0

    for pattern, name in intro_phrase_patterns:
        matches = list(re.finditer(pattern, clean_content))
        if matches:
            phrase_counts[name] = len(matches)
            total_count += len(matches)
            for match in matches:
                findings.append({
                    "type": "intro_phrase",
                    "phrase": name,
                    "match": match.group(0),
                    "position": match.start()
                })

    # H2セクション数をカウント
    h2_count = len(re.findall(r'^##\s+', clean_content, re.MULTILINE))

    # 推奨: 10-25回/記事（パターン拡張に伴い閾値を調整）
    if total_count < 5:
        issues.append({
            "type": "insufficient_intro_phrases",
            "message": f"導入フレーズが少なめです（{total_count}個）。「例えば」「つまり」「一方で」「注意が必要」などを10-25回使用してください。",
            "severity": "medium",
            "penalty": 8
        })
    elif total_count < 10:
        issues.append({
            "type": "low_intro_phrases",
            "message": f"導入フレーズがやや少なめです（{total_count}個）。10-25回が推奨です。",
            "severity": "low",
            "penalty": 4
        })
    elif total_count > 35:
        issues.append({
            "type": "excessive_intro_phrases",
            "message": f"導入フレーズが多すぎます（{total_count}個）。くどくなる可能性があります。",
            "severity": "low",
            "penalty": 3
        })

    # セクションあたりの分布チェック
    if h2_count > 0 and total_count > 0:
        avg_per_section = total_count / h2_count
        if avg_per_section < 0.5:
            issues.append({
                "type": "uneven_intro_distribution",
                "message": f"導入フレーズの分布が偏っています（{h2_count}セクションに対し{total_count}個）。各セクションに1個以上を目指してください。",
                "severity": "low",
                "penalty": 3
            })

    return issues, findings, phrase_counts, total_count


def check_everyday_analogies(content):
    """日常的な例えの使用をチェック"""
    issues = []
    findings = []

    clean_content = remove_frontmatter_and_code_blocks(content)

    # 日常的な例えのパターン
    analogy_patterns = [
        (r'ようなもの[でだ]', '〜のようなもの'),
        (r'に例えると', '例え導入'),
        (r'に置き換えると', '置き換え'),
        (r'で言えば', '〜で言えば'),
        (r'日常[でに][言い]えば', '日常での例え'),
        (r'身近な例[でだ]', '身近な例'),
        (r'イメージし[てや]', 'イメージ誘導'),
        (r'想像し[てや]', 'イメージ誘導'),
        (r'考えてみて', '思考誘導'),
        (r'レストラン', '日常アナロジー'),
        (r'本棚', '日常アナロジー'),
        (r'料理', '日常アナロジー'),
        (r'住所', '日常アナロジー'),
        (r'地図', '日常アナロジー'),
    ]

    analogy_count = 0

    for pattern, category in analogy_patterns:
        matches = list(re.finditer(pattern, clean_content))
        if matches:
            analogy_count += len(matches)
            for match in matches:
                findings.append({
                    "type": "everyday_analogy",
                    "category": category,
                    "match": match.group(0),
                    "position": match.start()
                })

    # 推奨: 2-5個/記事
    if analogy_count == 0:
        issues.append({
            "type": "no_analogies",
            "message": "日常的な例えがありません。複雑な概念を説明する際に「〜のようなもの」「例えば、レストランで言えば〜」などを使用してください。",
            "severity": "medium",
            "penalty": 5
        })
    elif analogy_count > 8:
        issues.append({
            "type": "excessive_analogies",
            "message": f"日常的な例えが多すぎます（{analogy_count}個）。例えに頼りすぎると冗長になります。",
            "severity": "low",
            "penalty": 3
        })

    return issues, findings, analogy_count


def check_explanation_depth(content):
    """説明の深さ（抽象と具体のバランス）をチェック"""
    issues = []
    findings = []

    clean_content = remove_frontmatter_and_code_blocks(content)

    # 抽象的説明のパターン
    abstract_patterns = [
        r'概念',
        r'理論',
        r'仕組み',
        r'原理',
        r'考え方',
        r'アプローチ',
        r'方針',
    ]

    # 具体的説明のパターン
    concrete_patterns = [
        r'具体的に',
        r'実際に',
        r'たとえば',
        r'例えば',
        r'この場合',
        r'のケースでは',
        r'手順は',
        r'方法は',
    ]

    abstract_count = sum(len(re.findall(p, clean_content)) for p in abstract_patterns)
    concrete_count = sum(len(re.findall(p, clean_content)) for p in concrete_patterns)

    findings.append({
        "type": "explanation_balance",
        "abstract_count": abstract_count,
        "concrete_count": concrete_count
    })

    # 具体的説明が抽象的説明より少ない場合
    if abstract_count > 0 and concrete_count < abstract_count:
        issues.append({
            "type": "insufficient_concrete",
            "message": f"抽象的な説明（{abstract_count}個）に対して具体例（{concrete_count}個）が少なめです。「例えば」「具体的には」を増やしてください。",
            "severity": "low",
            "penalty": 3
        })

    return issues, findings


def check_all_intro_and_explanations(content):
    """導入フレーズと説明表現の全要素をチェック"""
    all_issues = []
    all_findings = []
    score = 100

    # 1. 導入フレーズチェック
    issues, findings, phrase_counts, total_phrases = check_intro_phrases(content)
    all_issues.extend(issues)
    all_findings.extend(findings)

    # 2. 日常的な例えチェック
    issues, findings, analogy_count = check_everyday_analogies(content)
    all_issues.extend(issues)
    all_findings.extend(findings)

    # 3. 説明の深さチェック
    issues, findings = check_explanation_depth(content)
    all_issues.extend(issues)
    all_findings.extend(findings)

    # スコア計算
    for issue in all_issues:
        score -= issue.get('penalty', 5)

    # 統計情報
    stats = {
        "intro_phrase_count": total_phrases,
        "phrase_breakdown": phrase_counts,
        "analogy_count": analogy_count
    }

    return {
        "score": max(0, score),
        "issues": all_issues,
        "findings": all_findings,
        "stats": stats
    }


def main():
    if len(sys.argv) != 2:
        print("Usage: python check_intro_phrases.py <markdown_file>")
        sys.exit(1)

    filepath = sys.argv[1]

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        result = check_all_intro_and_explanations(content)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
