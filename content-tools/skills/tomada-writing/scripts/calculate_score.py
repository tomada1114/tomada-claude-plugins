#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
総合スコア計算スクリプト v3.0
評価前に自動修正を実行し、各チェックスクリプトの結果を統合して総合スコアを算出する

スコア配分（100点満点）:
- 接続詞スコア: 20点
- NGワードスコア: 15点
- 文体品質スコア: 15点
- 文体スタイルスコア: 15点
- 共感・トーンスコア: 15点
- 冒頭構成スコア: 10点
- 導入フレーズスコア: 10点
"""

import sys
import json
import subprocess
import io
import os
import re

# 標準出力をUTF-8に設定
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


# ============================================================
# 自動修正機能 (autofix)
# ============================================================

# 避けるべき接続詞の置換ルール
CONJUNCTION_REPLACEMENTS = [
    # 文頭パターン（行頭）
    (r'^でも、', 'ですが、'),
    (r'^でも，', 'ですが、'),
    (r'^だけど、', 'ですが、'),
    (r'^だけど，', 'ですが、'),
    (r'^じゃあ、', ''),  # 削除
    (r'^じゃあ，', ''),  # 削除
    (r'^だから、', 'そのため、'),
    (r'^だから，', 'そのため、'),
    (r'^それで、', 'そのため、'),
    (r'^それで，', 'そのため、'),
]

# 句点後の接続詞置換ルール
CONJUNCTION_AFTER_PERIOD = [
    (r'。でも、', '。ですが、'),
    (r'。でも，', '。ですが、'),
    (r'。だけど、', '。ですが、'),
    (r'。だけど，', '。ですが、'),
    (r'。だから、', '。そのため、'),
    (r'。だから，', '。そのため、'),
    (r'。それで、', '。そのため、'),
    (r'。それで，', '。そのため、'),
]

# 上から目線表現の置換ルール
CONDESCENDING_REPLACEMENTS = [
    (r'すべきです', 'がおすすめです'),
    (r'すべきだと', 'がおすすめだと'),
    (r'当然ですが', ''),  # 削除
    (r'当然だが', ''),  # 削除
]


def remove_frontmatter_for_autofix(content):
    """frontmatterを分離して返す"""
    match = re.match(r'^(---\n.*?\n---\n)', content, flags=re.DOTALL)
    if match:
        return match.group(1), content[match.end():]
    return '', content


def autofix_content(content):
    """
    機械的に修正可能な項目を自動修正する

    Returns:
        tuple: (修正後のコンテンツ, 修正レポート)
    """
    fixes = []

    # frontmatterを保護
    frontmatter, body = remove_frontmatter_for_autofix(content)

    # コードブロックを一時的に保護
    code_blocks = []
    def save_code_block(match):
        code_blocks.append(match.group(0))
        return f'___CODE_BLOCK_{len(code_blocks) - 1}___'

    body = re.sub(r'```.*?```', save_code_block, body, flags=re.DOTALL)

    # 1. 避けるべき接続詞の置換（文頭）
    lines = body.split('\n')
    new_lines = []
    for line in lines:
        original_line = line
        for pattern, replacement in CONJUNCTION_REPLACEMENTS:
            new_line = re.sub(pattern, replacement, line)
            if new_line != line:
                fixes.append({
                    "type": "conjunction_replacement",
                    "before": line.strip()[:50],
                    "after": new_line.strip()[:50],
                    "pattern": pattern
                })
                line = new_line
        new_lines.append(line)
    body = '\n'.join(new_lines)

    # 2. 避けるべき接続詞の置換（句点後）
    for pattern, replacement in CONJUNCTION_AFTER_PERIOD:
        matches = list(re.finditer(re.escape(pattern.replace('。', '。')), body))
        if matches:
            for match in matches:
                fixes.append({
                    "type": "conjunction_after_period",
                    "before": match.group(0),
                    "after": replacement,
                    "pattern": pattern
                })
        body = body.replace(pattern.replace('。', '。'), replacement)

    # 3. 上から目線表現の置換
    for pattern, replacement in CONDESCENDING_REPLACEMENTS:
        matches = list(re.finditer(pattern, body))
        if matches:
            for match in matches:
                fixes.append({
                    "type": "condescending_replacement",
                    "before": match.group(0),
                    "after": replacement if replacement else "(削除)",
                    "pattern": pattern
                })
        body = re.sub(pattern, replacement, body)

    # コードブロックを復元
    for i, code_block in enumerate(code_blocks):
        body = body.replace(f'___CODE_BLOCK_{i}___', code_block)

    # frontmatterを復元
    fixed_content = frontmatter + body

    report = {
        "total_fixes": len(fixes),
        "fixes": fixes
    }

    return fixed_content, report


def run_check(script_path, markdown_file):
    """チェックスクリプトを実行して結果を取得"""
    try:
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'

        result = subprocess.run(
            ['python3', script_path, markdown_file],
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=True,
            env=env
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_path}: {e.stderr}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from {script_path}: {e}", file=sys.stderr)
        return None


def calculate_conjunction_score(structure_result, max_score=20):
    """接続詞スコアを計算（20点満点）"""
    if not structure_result or 'issues' not in structure_result:
        return max_score

    score = max_score
    issues = structure_result.get('issues', [])

    for issue in issues:
        category = issue.get('category', '')

        if category == '接続詞使用率':
            if '低め' in issue.get('message', '') or '%です。' in issue.get('message', ''):
                score -= 8
            else:
                score -= 4
        elif category == '接続詞不足':
            score -= 2
        elif category == '避けるべき接続詞':
            score -= 1

    return max(0, score)


def calculate_ng_words_score(ng_result, max_score=15):
    """NGワードスコアを計算（15点満点）

    重要: NG表現は100%回避が必須。1件でもあれば0点（即不合格）。
    """
    if not ng_result:
        return max_score

    forbidden_count = ng_result.get('total_issues', 0)

    if forbidden_count == 0:
        return max_score
    else:
        return 0  # 1件でもあれば0点（v9.0.0で厳格化）


def calculate_style_quality_score(structure_result, max_score=15):
    """文体品質スコアを計算（15点満点）"""
    if not structure_result:
        return max_score

    score = max_score
    issues = structure_result.get('issues', [])

    issue_categories = {}
    for issue in issues:
        category = issue.get('category', '')
        if category not in ['接続詞使用率', '接続詞不足', '避けるべき接続詞']:
            if category not in issue_categories:
                issue_categories[category] = []
            issue_categories[category].append(issue)

    for category, category_issues in issue_categories.items():
        count = len(category_issues)
        severity = category_issues[0].get('severity', 'medium')

        if severity == 'high':
            score -= min(2 + count * 0.3, 4)
        elif severity == 'medium':
            score -= min(1 + count * 0.2, 3)
        else:
            score -= min(0.5 + count * 0.1, 2)

    return max(0, score)


def calculate_saborou_score(saborou_result, max_score=15):
    """文体スタイルスコアを計算（15点満点）"""
    if not saborou_result:
        return max_score

    # スクリプトのスコアを15点満点に正規化
    raw_score = saborou_result.get('score', 100)
    normalized_score = (raw_score / 100) * max_score

    return round(normalized_score, 1)


def calculate_empathy_score(empathy_result, max_score=15):
    """共感・トーンスコアを計算（15点満点）"""
    if not empathy_result:
        return max_score

    raw_score = empathy_result.get('score', 100)
    normalized_score = (raw_score / 100) * max_score

    return round(normalized_score, 1)


def calculate_opening_score(opening_result, max_score=10):
    """冒頭構成スコアを計算（10点満点）"""
    if not opening_result:
        return max_score

    raw_score = opening_result.get('score', 100)
    normalized_score = (raw_score / 100) * max_score

    return round(normalized_score, 1)


def calculate_intro_phrases_score(intro_result, max_score=10):
    """導入フレーズスコアを計算（10点満点）"""
    if not intro_result:
        return max_score

    raw_score = intro_result.get('score', 100)
    normalized_score = (raw_score / 100) * max_score

    return round(normalized_score, 1)


# 各軸の最低基準（配点の80%）- v9.0.0で追加
AXIS_MINIMUM_THRESHOLDS = {
    "conjunction": 16,      # 20点 × 80% = 16点
    "ng_words": 15,         # 15点満点必須（0件必須なので満点のみ合格）
    "style_quality": 12,    # 15点 × 80% = 12点
    "saborou_style": 12,    # 15点 × 80% = 12点
    "empathy_tone": 12,     # 15点 × 80% = 12点
    "opening_structure": 8, # 10点 × 80% = 8点
    "intro_phrases": 8,     # 10点 × 80% = 8点
}


def check_axis_minimums(breakdown):
    """各軸が最低基準を満たしているかチェック（v9.0.0で追加）

    Returns:
        list: 基準未達の軸のリスト。空リストなら全軸合格。
    """
    failed_axes = []
    for axis, threshold in AXIS_MINIMUM_THRESHOLDS.items():
        score = breakdown.get(axis, {}).get("score", 0)
        if score < threshold:
            failed_axes.append({
                "axis": axis,
                "score": score,
                "threshold": threshold,
                "deficit": round(threshold - score, 1)
            })
    return failed_axes


def calculate_total_score(
    ng_result,
    structure_result,
    saborou_result,
    empathy_result,
    opening_result,
    intro_result
):
    """総合スコアを計算（100点満点）

    v9.0.0更新: 各軸最低基準チェック、再実行要否フラグを追加。
    """

    # 各評価軸でスコア計算
    conjunction_score = calculate_conjunction_score(structure_result)
    ng_score = calculate_ng_words_score(ng_result)
    style_score = calculate_style_quality_score(structure_result)
    saborou_score = calculate_saborou_score(saborou_result)
    empathy_score = calculate_empathy_score(empathy_result)
    opening_score = calculate_opening_score(opening_result)
    intro_score = calculate_intro_phrases_score(intro_result)

    total_score = (
        conjunction_score +
        ng_score +
        style_score +
        saborou_score +
        empathy_score +
        opening_score +
        intro_score
    )

    # 総合評価の判定
    if total_score >= 95:
        grade = "A+"
        status = "優秀（とまだスタイルを完璧に再現）"
    elif total_score >= 90:
        grade = "A"
        status = "良好（公開可能な高品質）"
    elif total_score >= 80:
        grade = "B+"
        status = "概ね良好（軽微な修正で公開可能）"
    elif total_score >= 70:
        grade = "B"
        status = "要改善（部分的な修正が必要）"
    elif total_score >= 50:
        grade = "C"
        status = "要大幅改善（複数の問題を修正）"
    else:
        grade = "D"
        status = "不合格（大幅な書き直しが必要）"

    # 内訳を構築
    breakdown = {
        "conjunction": {
            "score": conjunction_score,
            "max_score": 20,
            "min_threshold": AXIS_MINIMUM_THRESHOLDS["conjunction"],
            "description": "接続詞の使用率と質"
        },
        "ng_words": {
            "score": ng_score,
            "max_score": 15,
            "min_threshold": AXIS_MINIMUM_THRESHOLDS["ng_words"],
            "description": "禁止表現の回避（0件必須）"
        },
        "style_quality": {
            "score": style_score,
            "max_score": 15,
            "min_threshold": AXIS_MINIMUM_THRESHOLDS["style_quality"],
            "description": "文体品質（構造など）"
        },
        "saborou_style": {
            "score": saborou_score,
            "max_score": 15,
            "min_threshold": AXIS_MINIMUM_THRESHOLDS["saborou_style"],
            "description": "とまだ式スタイル（結論先出し、両面提示など）"
        },
        "empathy_tone": {
            "score": empathy_score,
            "max_score": 15,
            "min_threshold": AXIS_MINIMUM_THRESHOLDS["empathy_tone"],
            "description": "共感・トーン（読者への寄り添い）"
        },
        "opening_structure": {
            "score": opening_score,
            "max_score": 10,
            "min_threshold": AXIS_MINIMUM_THRESHOLDS["opening_structure"],
            "description": "冒頭構成（挨拶、問いかけ、要約など）"
        },
        "intro_phrases": {
            "score": intro_score,
            "max_score": 10,
            "min_threshold": AXIS_MINIMUM_THRESHOLDS["intro_phrases"],
            "description": "導入フレーズ（例えば、つまりなど）"
        }
    }

    # 各軸最低基準チェック（v9.0.0で追加）
    failed_axes = check_axis_minimums(breakdown)

    # 再実行判定: 基準未達の軸があれば再実行必須
    requires_retry = len(failed_axes) > 0

    return {
        "total_score": round(total_score, 1),
        "grade": grade,
        "status": status,
        "requires_retry": requires_retry,
        "failed_axes": failed_axes,
        "breakdown": breakdown
    }


def calculate_sentence_ending_score(sentence_ending_result):
    """文末表現スコア（参考値として表示、総合スコアには含めない）"""
    if not sentence_ending_result:
        return None

    return {
        "score": sentence_ending_result.get('score', 0),
        "max_score": 100,
        "description": "文末表現のバリエーション（参考値）",
        "stats": sentence_ending_result.get('stats', {}),
        "issues": sentence_ending_result.get('issues', [])
    }


def main():
    if len(sys.argv) != 2:
        print("Usage: python calculate_score.py <markdown_file>")
        sys.exit(1)

    markdown_file = sys.argv[1]
    script_dir = sys.path[0]

    # ============================================================
    # Step 1: ファイルを読み込み、自動修正を実行
    # ============================================================
    try:
        with open(markdown_file, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except FileNotFoundError:
        print(f"Error: File '{markdown_file}' not found", file=sys.stderr)
        sys.exit(1)

    # 自動修正を実行
    fixed_content, autofix_report = autofix_content(original_content)

    # 修正があった場合はファイルを上書き保存
    if autofix_report["total_fixes"] > 0:
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        print(f"[autofix] {autofix_report['total_fixes']}件の自動修正を適用しました", file=sys.stderr)

    # ============================================================
    # Step 2: 各チェックスクリプトを実行
    # ============================================================
    ng_result = run_check(f"{script_dir}/check_ng_words.py", markdown_file)
    structure_result = run_check(f"{script_dir}/check_structure.py", markdown_file)
    sentence_ending_result = run_check(f"{script_dir}/check_sentence_endings.py", markdown_file)

    # 新規スクリプト
    saborou_result = run_check(f"{script_dir}/check_saborou_style.py", markdown_file)
    empathy_result = run_check(f"{script_dir}/check_empathy_expressions.py", markdown_file)
    opening_result = run_check(f"{script_dir}/check_opening_structure.py", markdown_file)
    intro_result = run_check(f"{script_dir}/check_intro_phrases.py", markdown_file)

    # Zenn固有チェック（参考値）
    message_box_result = run_check(f"{script_dir}/check_message_box.py", markdown_file)

    # ============================================================
    # Step 3: 総合スコアを計算
    # ============================================================
    total_result = calculate_total_score(
        ng_result,
        structure_result,
        saborou_result,
        empathy_result,
        opening_result,
        intro_result
    )

    # 文末表現スコア（参考値）
    sentence_ending_score = calculate_sentence_ending_score(sentence_ending_result)

    # 結果を統合
    result = {
        **total_result,
        "autofix": autofix_report,
        "details": {
            "ng_words": ng_result,
            "structure": structure_result,
            "sentence_endings": sentence_ending_result,
            "saborou_style": saborou_result,
            "empathy_expressions": empathy_result,
            "opening_structure": opening_result,
            "intro_phrases": intro_result
        }
    }

    # 参考情報として追加
    result["reference"] = {}
    if sentence_ending_score:
        result["reference"]["sentence_endings"] = sentence_ending_score
    if message_box_result:
        result["reference"]["message_box"] = {
            "score": message_box_result.get("score", 100),
            "box_count": message_box_result.get("box_count", 0),
            "issues": message_box_result.get("issues", []),
            "description": "メッセージボックス（:::message）の品質（Zenn記事向け）"
        }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
