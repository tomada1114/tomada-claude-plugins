#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
記事構造チェックスクリプト
見出し構造、段落の長さ、文の長さなどを評価する
"""

import sys
import re
import json
import io

# 標準出力をUTF-8に設定
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def parse_markdown(content):
    """マークダウンをパースして構造を解析"""
    lines = content.split('\n')
    
    headings = []
    paragraphs = []
    sentences = []
    current_paragraph = []
    
    for line in lines:
        # 見出しの抽出
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2)
            headings.append({
                "level": level,
                "text": text,
                "length": len(text)
            })
            
            # 段落の区切り
            if current_paragraph:
                para_text = ' '.join(current_paragraph)
                paragraphs.append(para_text)
                current_paragraph = []
            continue
        
        # 空行は段落の区切り
        if not line.strip():
            if current_paragraph:
                para_text = ' '.join(current_paragraph)
                paragraphs.append(para_text)
                current_paragraph = []
            continue
        
        # コードブロックやリストは除外
        if line.startswith('```') or line.startswith('- ') or line.startswith('* '):
            continue
        
        # 通常のテキスト
        current_paragraph.append(line.strip())
        
        # 文の抽出（句点で区切る）
        for sentence in re.split(r'[。！？]', line):
            if sentence.strip():
                sentences.append(sentence.strip())
    
    # 最後の段落
    if current_paragraph:
        para_text = ' '.join(current_paragraph)
        paragraphs.append(para_text)
    
    return headings, paragraphs, sentences

def check_bold_as_list_pattern(content):
    """太字を箇条書き風に書くNGパターンを検出"""
    lines = content.split('\n')
    issues = []

    # **太字** - 説明のパターンを検出（箇条書き記号なし）
    bold_explanation_pattern = re.compile(r'^\*\*(.+?)\*\*\s*[-–]\s*(.+)$')

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 箇条書き記号がない場合のみチェック
        # ただし、**太字** で始まる場合は箇条書き記号ではない
        if (not stripped.startswith('- ') and
            not stripped.startswith('* ') and
            not stripped.startswith('+ ') and
            bold_explanation_pattern.match(stripped)):

            # パターンにマッチした行を起点にカウント開始
            consecutive_count = 1
            line_numbers = [i + 1]  # 1-indexed
            j = i + 1

            # 次の行から連続するパターンを探す
            while j < len(lines):
                next_line = lines[j].strip()

                # 空行は許容（単一空行で区切られたパターン）
                if not next_line:
                    j += 1
                    continue

                # パターンにマッチする行が続く場合
                # ただし、**太字** で始まる場合は箇条書き記号ではない
                if (not next_line.startswith('- ') and
                    not next_line.startswith('* ') and
                    not next_line.startswith('+ ') and
                    bold_explanation_pattern.match(next_line)):
                    consecutive_count += 1
                    line_numbers.append(j + 1)  # 1-indexed
                    j += 1
                else:
                    # パターンが途切れた
                    break

            # 3個以上連続している場合はissueとして記録
            if consecutive_count >= 3:
                issues.append({
                    "line_numbers": line_numbers.copy(),
                    "count": consecutive_count
                })

            # 次のチェックは途切れた位置から
            i = j
        else:
            i += 1

    return issues

def check_bullet_explanation_taigendome(content):
    """箇条書き内の説明で体言止めになっていないパターンを検出"""
    lines = content.split('\n')
    issues = []

    # 箇条書き内の **太字** - 説明です。パターンを検出
    bullet_pattern = re.compile(r'^[-*+]\s+\*\*(.+?)\*\*\s*[-–]\s*(.+)$')

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        match = bullet_pattern.match(stripped)
        if match:
            term = match.group(1)
            explanation = match.group(2).strip()
            # 「です」「ます」で終わっている場合は体言止めではない
            if explanation.endswith('です') or explanation.endswith('ます'):
                issues.append({
                    "line_number": i,
                    "term": term,
                    "explanation": explanation,
                    "line": line.strip()
                })

    return issues

def check_summary_section_length(content):
    """まとめセクションの長さをチェック"""
    issues = []

    # まとめセクションを抽出
    summary_match = re.search(r'##\s*まとめ\s*\n(.+?)(?=\n##|$)', content, re.DOTALL)
    if not summary_match:
        return []  # まとめセクションがない場合は別のチェックで検出される

    summary_content = summary_match.group(1).strip()
    lines = [line for line in summary_content.split('\n') if line.strip() and not line.strip().startswith('#')]

    # 行数チェック（10行以内が理想）
    line_count = len(lines)
    if line_count > 10:
        issues.append({
            "type": "summary_too_long_lines",
            "actual_lines": line_count,
            "max_lines": 10,
            "severity": "high"
        })

    # 文字数チェック（300文字以内が理想）
    char_count = len(summary_content)
    if char_count > 300:
        issues.append({
            "type": "summary_too_long_chars",
            "actual_chars": char_count,
            "max_chars": 300,
            "severity": "high"
        })

    # 「～しました」の繰り返しパターンをチェック
    shimashita_pattern = re.compile(r'しました[。\n]')
    shimashita_count = len(shimashita_pattern.findall(summary_content))
    if shimashita_count >= 3:
        issues.append({
            "type": "repetitive_shimashita",
            "count": shimashita_count,
            "severity": "medium"
        })

    return issues

def check_connector_words(content):
    """接続詞不足を検出（連続する文の間に接続詞がない箇所）"""
    issues = []

    # 接続詞リスト
    connectors = [
        'しかし', 'ただし', 'そのため', 'したがって', 'その結果', 'つまり',
        'また', 'さらに', 'なお', 'ちなみに', 'ところで', 'では',
        'それでは', 'そこで', 'すると', 'だから', 'なので', 'けれども',
        'でも', 'そして', 'それに', 'ですから', 'このように', 'こうして'
    ]

    # 段落ごとに分割
    paragraphs = content.split('\n\n')

    for para_idx, paragraph in enumerate(paragraphs):
        # コードブロックや見出しは除外
        if '```' in paragraph or paragraph.strip().startswith('#'):
            continue

        # 文に分割（句点で区切る）
        sentences = [s.strip() for s in re.split(r'[。！？]', paragraph) if s.strip()]

        # 5文以上連続して接続詞がない場合のみ検出（v2.0.0で緩和: 3→5）
        if len(sentences) >= 5:
            consecutive_without_connector = 0
            for sentence in sentences:
                has_connector = any(conn in sentence for conn in connectors)
                if not has_connector:
                    consecutive_without_connector += 1
                    if consecutive_without_connector >= 5:
                        issues.append({
                            "type": "missing_connectors",
                            "consecutive_count": consecutive_without_connector,
                            "paragraph_preview": paragraph[:100] + "...",
                            "severity": "medium"  # v2.0.0: high → medium に緩和
                        })
                        break
                else:
                    consecutive_without_connector = 0

    return issues

def check_bullet_intro_quality(content):
    """箇条書き前の導入の質をチェック"""
    issues = []

    lines = content.split('\n')

    # コードブロック内かどうかを追跡
    in_code_block = False

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # コードブロックの開始/終了を検出
        if line.startswith('```'):
            in_code_block = not in_code_block
            i += 1
            continue

        # コードブロック内はスキップ
        if in_code_block:
            i += 1
            continue

        # 箇条書きの開始を検出
        if line.startswith('- ') or line.startswith('* '):
            # 直前の非空行を取得
            intro_lines = []
            j = i - 1
            while j >= 0:
                prev_line = lines[j].strip()
                if not prev_line:
                    j -= 1
                    continue
                # 見出しやコードブロックで止まる
                if prev_line.startswith('#') or prev_line.startswith('```'):
                    break
                intro_lines.insert(0, prev_line)
                j -= 1

                # 2行前まで見る
                if len(intro_lines) >= 2:
                    break

            # 導入が1行以下または「以下の通りです」のみの場合
            if len(intro_lines) == 0:
                issues.append({
                    "type": "no_bullet_intro",
                    "line_number": i + 1,
                    "severity": "high"
                })
            elif len(intro_lines) == 1:
                intro_text = intro_lines[0]
                # 単純な導入パターン
                simple_patterns = [
                    r'^以下の通りです[。）]?$',
                    r'^次のとおりです[。）]?$',
                    r'^以下です[。）]?$',
                    r'^以下になります[。）]?$'
                ]
                if any(re.match(pattern, intro_text) for pattern in simple_patterns):
                    issues.append({
                        "type": "weak_bullet_intro",
                        "line_number": i + 1,
                        "intro": intro_text,
                        "severity": "medium"
                    })

        i += 1

    return issues

def check_conjunction_usage_ratio(content):
    """接続詞使用率をチェック（15-30%が理想、v2.0.0で緩和）"""
    issues = []

    # 推奨接続詞リスト（ADDTIONAL_RULE準拠）
    recommended_conjunctions = [
        'ですが', 'しかし', 'ただし', 'また', 'そして', 'そのため',
        'したがって', 'つまり', 'ちなみに', 'なお', 'さらに', '加えて',
        'もちろん', '一方で', '逆に', '反対に', 'なぜなら', 'というのも',
        'だからこそ', 'たとえば', '具体的には', '実際に', '要するに',
        'その理由は', '例を挙げると', 'それに対して'
    ]

    # 文を分割（句点で区切る）
    sentences = [s.strip() for s in re.split(r'[。！？]', content) if s.strip()]

    # コードブロックや見出しを含む文を除外
    valid_sentences = []
    for sentence in sentences:
        if '```' not in sentence and not sentence.startswith('#'):
            valid_sentences.append(sentence)

    if len(valid_sentences) == 0:
        return []

    # 接続詞を含む文をカウント
    sentences_with_conjunction = 0
    for sentence in valid_sentences:
        if any(conj in sentence for conj in recommended_conjunctions):
            sentences_with_conjunction += 1

    # 使用率を計算
    usage_ratio = (sentences_with_conjunction / len(valid_sentences)) * 100

    # v2.0.0: 閾値を緩和し、ペナルティのバランスを調整
    # 15-30%が理想、10-35%は許容
    if usage_ratio < 10:
        # 10%未満のみ警告（軽度）
        issues.append({
            "type": "low_conjunction_ratio",
            "actual_ratio": round(usage_ratio, 1),
            "expected_min": 15,
            "expected_max": 30,
            "total_sentences": len(valid_sentences),
            "sentences_with_conjunction": sentences_with_conjunction,
            "severity": "low"  # v2.0.0: high → low に緩和
        })
    elif usage_ratio > 35:
        # 35%超は過剰使用として警告（中度）
        issues.append({
            "type": "high_conjunction_ratio",
            "actual_ratio": round(usage_ratio, 1),
            "expected_min": 15,
            "expected_max": 30,
            "total_sentences": len(valid_sentences),
            "sentences_with_conjunction": sentences_with_conjunction,
            "severity": "medium"
        })
    elif usage_ratio > 40:
        # 40%超は機械的な印象として警告（高度）
        issues.append({
            "type": "excessive_conjunction_ratio",
            "actual_ratio": round(usage_ratio, 1),
            "expected_min": 15,
            "expected_max": 30,
            "total_sentences": len(valid_sentences),
            "sentences_with_conjunction": sentences_with_conjunction,
            "severity": "high"
        })

    return issues

def check_forbidden_conjunctions(content):
    """避けるべき接続詞（でも、だけど等）を検出"""
    issues = []

    # 避けるべき接続詞と推奨代替表現（ADDTIONAL_RULE準拠）
    forbidden_conjunctions = {
        'でも': 'ですが/しかし/ただし',
        'だけど': 'ですが/しかし',
        'じゃあ': '削除または「では」',
        'それで': 'そのため/したがって',
        'だから': 'そのため/したがって'
    }

    lines = content.split('\n')

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # コードブロックや見出しは除外
        if stripped.startswith('```') or stripped.startswith('#'):
            continue

        # 文頭での使用を検出
        for forbidden, alternative in forbidden_conjunctions.items():
            # 文頭パターン: 行の先頭または句点の直後
            pattern = r'(^|[。！？]\s*)' + re.escape(forbidden)
            if re.search(pattern, stripped):
                issues.append({
                    "type": "forbidden_conjunction",
                    "word": forbidden,
                    "alternative": alternative,
                    "line_number": i,
                    "line_preview": stripped[:50] + "..." if len(stripped) > 50 else stripped,
                    "severity": "high"
                })

    return issues

def check_heading_followed_by_text(content):
    """見出しの直後に説明文があるかチェック"""
    issues = []
    lines = content.split('\n')

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 見出しを検出（H2/H3/H4）
        heading_match = re.match(r'^(#{2,4})\s+(.+)$', line)
        if heading_match:
            heading_level = len(heading_match.group(1))
            heading_text = heading_match.group(2)

            # 次の非空行を探す
            j = i + 1
            next_content_line = None
            while j < len(lines):
                next_line = lines[j].strip()
                if next_line:
                    next_content_line = next_line
                    break
                j += 1

            # 次の行が見出し、箇条書き、コードブロックの場合は問題
            if next_content_line:
                is_heading = next_content_line.startswith('#')
                is_bullet = next_content_line.startswith('- ') or next_content_line.startswith('* ')
                is_code = next_content_line.startswith('```')

                if is_heading or is_bullet or is_code:
                    issues.append({
                        "type": "heading_without_intro",
                        "heading_level": heading_level,
                        "heading_text": heading_text,
                        "line_number": i + 1,
                        "next_content": "見出し" if is_heading else ("箇条書き" if is_bullet else "コードブロック"),
                        "severity": "medium"
                    })

        i += 1

    return issues

def check_h4_usage_quality(content):
    """H4見出しの使用品質をチェック"""
    issues = []
    lines = content.split('\n')

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # H4見出しを検出
        h4_match = re.match(r'^####\s+(.+)$', line)
        if h4_match:
            h4_text = h4_match.group(1)
            h4_line_number = i + 1

            # H4見出しの下の内容を取得（次の見出しまで）
            j = i + 1
            content_lines = []
            while j < len(lines):
                next_line = lines[j]
                # 次の見出しが来たら終了
                if re.match(r'^#{2,4}\s+', next_line):
                    break
                # 空行とコードブロック以外をカウント
                if next_line.strip() and not next_line.strip().startswith('```'):
                    content_lines.append(next_line.strip())
                j += 1

            # 文章量をチェック（3段落以上、150文字以上が推奨）
            char_count = sum(len(line) for line in content_lines)
            paragraph_count = len([line for line in content_lines if line and not line.startswith('- ')])

            # 150文字未満または実質的な段落が2つ以下の場合
            if char_count < 150 or paragraph_count < 3:
                issues.append({
                    "type": "insufficient_h4_content",
                    "heading_text": h4_text,
                    "line_number": h4_line_number,
                    "char_count": char_count,
                    "paragraph_count": paragraph_count,
                    "severity": "medium"
                })

        i += 1

    return issues

def remove_frontmatter_and_code_blocks(content):
    """frontmatterとコードブロックを除外"""
    # frontmatterを除外（先頭の --- ... --- ブロック）
    content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)

    # コードブロックを除外（```で囲まれた部分）
    content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)

    return content

def check_heading_before_intro_text(content):
    """見出しの前に「次は〜について説明します」などの前置き説明があるかチェック"""
    lines = content.split('\n')
    issues = []

    # 避けるべきパターン
    intro_patterns = [
        r'次[はに].*について.*説明',
        r'次[はに].*について.*見ていき',
        r'次[はに].*を.*見ていき',
        r'ここからは.*について.*説明',
        r'ここからは.*を.*見ていき',
        r'それでは.*について.*説明',
        r'では.*について.*説明'
    ]

    for i in range(len(lines) - 1):
        line = lines[i].strip()

        # 空行や見出し、コードブロックはスキップ
        if not line or line.startswith('#') or line.startswith('```'):
            continue

        # 次の非空行を探す
        next_heading_idx = None
        for j in range(i + 1, len(lines)):
            next_line = lines[j].strip()
            if not next_line:  # 空行はスキップ
                continue
            if next_line.startswith('##'):  # 見出しを発見
                next_heading_idx = j
                break
            else:  # 見出し以外の内容があれば、この行は見出し直前ではない
                break

        # 次が見出しの場合、現在の行が前置き説明パターンにマッチするかチェック
        if next_heading_idx is not None:
            for pattern in intro_patterns:
                if re.search(pattern, line):
                    issues.append({
                        "line_number": i + 1,
                        "line_content": line[:80],  # 最初の80文字
                        "next_heading": lines[next_heading_idx].strip()[:50],
                        "severity": "high"
                    })
                    break

    return issues

def check_bold_usage(content):
    """太字の使用状況をチェック"""
    issues = []

    # frontmatterとコードブロックを除外
    clean_content = remove_frontmatter_and_code_blocks(content)

    # 全文字数を計算（改行と空白を除く）
    total_chars = len(clean_content.replace('\n', '').replace(' ', ''))

    if total_chars == 0:
        return []

    # 太字部分を抽出
    bold_pattern = re.compile(r'\*\*(.+?)\*\*')
    bold_matches = bold_pattern.findall(clean_content)

    if not bold_matches:
        # 太字が全くない場合は警告（必須ではないが推奨）
        issues.append({
            "type": "no_bold_usage",
            "severity": "low"
        })
        return issues

    # 太字の文字数を計算
    bold_chars = sum(len(match) for match in bold_matches)
    bold_ratio = (bold_chars / total_chars) * 100

    # 太字の割合チェック（5-15%が理想）
    if bold_ratio < 5:
        issues.append({
            "type": "insufficient_bold",
            "actual_ratio": round(bold_ratio, 1),
            "expected_min": 5,
            "expected_max": 15,
            "severity": "low"
        })
    elif bold_ratio > 15:
        issues.append({
            "type": "excessive_bold",
            "actual_ratio": round(bold_ratio, 1),
            "expected_min": 5,
            "expected_max": 15,
            "severity": "medium"
        })

    # 文全体の太字をチェック（句点で終わる）
    lines = clean_content.split('\n')
    for i, line in enumerate(lines, 1):
        # 文全体が太字のパターン: **...。** or **...！** or **...？**
        full_sentence_bold = re.search(r'\*\*[^*]+[。！？]\*\*', line)
        if full_sentence_bold:
            issues.append({
                "type": "full_sentence_bold",
                "line_number": i,
                "content": full_sentence_bold.group(0)[:50] + "..." if len(full_sentence_bold.group(0)) > 50 else full_sentence_bold.group(0),
                "severity": "high"
            })

    return issues

def check_structure(content):
    """構造をチェックしてスコアリング"""
    headings, paragraphs, sentences = parse_markdown(content)

    issues = []
    score = 100

    # 【新規】まとめセクションの長さチェック
    summary_issues = check_summary_section_length(content)
    for issue in summary_issues:
        if issue['type'] == 'summary_too_long_lines':
            issues.append({
                "category": "まとめの長さ（行数）",
                "message": f"まとめセクションが{issue['actual_lines']}行です。{issue['max_lines']}行以内が推奨されます。",
                "severity": issue['severity']
            })
            score -= 15
        elif issue['type'] == 'summary_too_long_chars':
            issues.append({
                "category": "まとめの長さ（文字数）",
                "message": f"まとめセクションが{issue['actual_chars']}文字です。{issue['max_chars']}文字以内が推奨されます。",
                "severity": issue['severity']
            })
            score -= 10
        elif issue['type'] == 'repetitive_shimashita':
            issues.append({
                "category": "まとめの表現パターン",
                "message": f"「～しました」が{issue['count']}回使われています。要約は簡潔に。",
                "severity": issue['severity']
            })
            score -= 5

    # 【新規】接続詞不足のチェック（v2.0.0で緩和）
    connector_issues = check_connector_words(content)
    if connector_issues:
        for issue in connector_issues:
            issues.append({
                "category": "接続詞不足",
                "message": f"{issue['consecutive_count']}文連続で接続詞がありません: {issue['paragraph_preview']}",
                "severity": issue['severity']
            })
        score -= len(connector_issues) * 5  # v2.0.0: 10 → 5 に緩和

    # 【新規】箇条書き導入の質チェック
    bullet_intro_issues = check_bullet_intro_quality(content)
    for issue in bullet_intro_issues:
        if issue['type'] == 'no_bullet_intro':
            issues.append({
                "category": "箇条書きの導入",
                "message": f"行{issue['line_number']}の箇条書きに導入文がありません",
                "severity": issue['severity']
            })
            score -= 8
        elif issue['type'] == 'weak_bullet_intro':
            issues.append({
                "category": "箇条書きの導入",
                "message": f"行{issue['line_number']}の箇条書き導入が弱い: {issue['intro']}",
                "severity": issue['severity']
            })
            score -= 5

    # 【新規】接続詞使用率チェック（v2.0.0で緩和）
    conjunction_ratio_issues = check_conjunction_usage_ratio(content)
    for issue in conjunction_ratio_issues:
        if issue['type'] == 'low_conjunction_ratio':
            issues.append({
                "category": "接続詞使用率",
                "message": f"接続詞使用率が{issue['actual_ratio']}%です。{issue['expected_min']}-{issue['expected_max']}%が推奨されます。（{issue['sentences_with_conjunction']}/{issue['total_sentences']}文）",
                "severity": issue['severity']
            })
            score -= 3  # v2.0.0: 15 → 3 に大幅緩和（低い使用率は軽度）
        elif issue['type'] == 'high_conjunction_ratio':
            issues.append({
                "category": "接続詞使用率",
                "message": f"接続詞使用率が{issue['actual_ratio']}%と高めです。{issue['expected_min']}-{issue['expected_max']}%が推奨されます。（{issue['sentences_with_conjunction']}/{issue['total_sentences']}文）",
                "severity": issue['severity']
            })
            score -= 10  # v2.0.0: 8 → 10 に強化（高い使用率はくどい）
        elif issue['type'] == 'excessive_conjunction_ratio':
            issues.append({
                "category": "接続詞使用率",
                "message": f"接続詞使用率が{issue['actual_ratio']}%と非常に高いです。機械的な印象を与える可能性があります。（{issue['sentences_with_conjunction']}/{issue['total_sentences']}文）",
                "severity": issue['severity']
            })
            score -= 15  # 40%超は大きく減点

    # 【新規】避けるべき接続詞チェック
    forbidden_conj_issues = check_forbidden_conjunctions(content)
    for issue in forbidden_conj_issues:
        issues.append({
            "category": "避けるべき接続詞",
            "message": f"行{issue['line_number']}:「{issue['word']}」は避けるべき接続詞です。代わりに「{issue['alternative']}」を使用してください。",
            "severity": issue['severity'],
            "line_preview": issue['line_preview']
        })
    score -= len(forbidden_conj_issues) * 5

    # 【新規】見出し直後の説明文チェック
    heading_intro_issues = check_heading_followed_by_text(content)
    for issue in heading_intro_issues:
        issues.append({
            "category": "見出し直後の説明文",
            "message": f"行{issue['line_number']}の見出し「{issue['heading_text']}」の直後に説明文がありません（次は{issue['next_content']}）",
            "severity": issue['severity']
        })
    score -= len(heading_intro_issues) * 5

    # 【新規】H4見出しの使用品質チェック
    h4_quality_issues = check_h4_usage_quality(content)
    for issue in h4_quality_issues:
        issues.append({
            "category": "H4見出しの内容量",
            "message": f"行{issue['line_number']}のH4見出し「{issue['heading_text']}」の内容が不足しています（{issue['char_count']}文字、{issue['paragraph_count']}段落）。推奨: 150文字以上、3段落以上",
            "severity": issue['severity']
        })
    score -= len(h4_quality_issues) * 5

    # 【新規】見出し前の前置き説明チェック
    heading_intro_issues = check_heading_before_intro_text(content)
    for issue in heading_intro_issues:
        issues.append({
            "category": "見出し前の前置き説明",
            "message": f"行{issue['line_number']}で見出し前に前置き説明があります: 「{issue['line_content']}」 → 次の見出し: {issue['next_heading']}",
            "severity": issue['severity']
        })
    score -= len(heading_intro_issues) * 10

    # 【新規】太字使用チェック
    bold_issues = check_bold_usage(content)
    for issue in bold_issues:
        if issue['type'] == 'no_bold_usage':
            issues.append({
                "category": "太字の使用",
                "message": "重要なポイントを強調する太字がありません（推奨）",
                "severity": issue['severity']
            })
            score -= 3
        elif issue['type'] == 'insufficient_bold':
            issues.append({
                "category": "太字の使用",
                "message": f"太字の使用率が{issue['actual_ratio']}%と少なめです。{issue['expected_min']}-{issue['expected_max']}%が推奨されます",
                "severity": issue['severity']
            })
            score -= 5
        elif issue['type'] == 'excessive_bold':
            issues.append({
                "category": "太字の使用",
                "message": f"太字の使用率が{issue['actual_ratio']}%と多すぎます。{issue['expected_min']}-{issue['expected_max']}%が推奨されます",
                "severity": issue['severity']
            })
            score -= 8
        elif issue['type'] == 'full_sentence_bold':
            issues.append({
                "category": "太字の使用",
                "message": f"行{issue['line_number']}で文全体が太字になっています: {issue['content']}",
                "severity": issue['severity']
            })
            score -= 10

    # 太字を箇条書き風に書くNGパターンのチェック
    bold_as_list_issues = check_bold_as_list_pattern(content)
    if bold_as_list_issues:
        for issue in bold_as_list_issues:
            issues.append({
                "category": "太字を箇条書き風に書くパターン",
                "message": f"{issue['count']}個の連続した太字説明が箇条書き記号なしで並んでいます（行{issue['line_numbers'][0]}-{issue['line_numbers'][-1]}）",
                "severity": "medium",
                "line_numbers": issue['line_numbers']
            })
        score -= len(bold_as_list_issues) * 5

    # 箇条書き内の説明が体言止めでないパターンのチェック
    taigendome_issues = check_bullet_explanation_taigendome(content)
    if taigendome_issues:
        issues.append({
            "category": "箇条書き説明の体言止め",
            "message": f"{len(taigendome_issues)}箇所で箇条書き内の説明が「です」「ます」で終わっています",
            "severity": "low",
            "examples": [issue['line'] for issue in taigendome_issues[:3]]
        })
        score -= len(taigendome_issues) * 2

    # 見出しの数チェック（4-7個が理想）
    h2_count = len([h for h in headings if h['level'] == 2])
    if h2_count < 4:
        issues.append({
            "category": "見出し数",
            "message": f"メイン見出し(##)が{h2_count}個です。4-7個が推奨されます。",
            "severity": "medium"
        })
        score -= 10
    elif h2_count > 7:
        issues.append({
            "category": "見出し数",
            "message": f"メイン見出し(##)が{h2_count}個と多すぎます。4-7個が推奨されます。",
            "severity": "low"
        })
        score -= 5
    
    # 見出しの長さチェック（30文字以内が理想）
    long_headings = [h for h in headings if h['length'] > 30]
    if long_headings:
        issues.append({
            "category": "見出しの長さ",
            "message": f"{len(long_headings)}個の見出しが30文字を超えています",
            "severity": "low",
            "examples": [h['text'] for h in long_headings[:3]]
        })
        score -= len(long_headings) * 2

    # 冒頭の挨拶チェック
    first_lines = content[:200]
    if "こんにちは、とまだです" not in first_lines:
        issues.append({
            "category": "冒頭の挨拶",
            "message": "冒頭に「こんにちは、とまだです」がありません",
            "severity": "high"
        })
        score -= 10
    
    # 要約セクションのチェック
    if "## 忙しい人のために要約" not in content and "##忙しい人のために要約" not in content:
        issues.append({
            "category": "要約セクション",
            "message": "「忙しい人のために要約」セクションがありません",
            "severity": "high"
        })
        score -= 15
    
    return {
        "score": max(0, score),
        "issues": issues,
        "stats": {
            "heading_count": len(headings),
            "h2_count": h2_count,
            "paragraph_count": len(paragraphs),
            "sentence_count": len(sentences)
        }
    }

def main():
    if len(sys.argv) != 2:
        print("Usage: python check_structure.py <markdown_file>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        result = check_structure(content)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
