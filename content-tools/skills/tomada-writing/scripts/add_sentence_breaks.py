#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
句点改行自動挿入スクリプト
段落内の句点（。）ごとに改行を自動挿入し、記事の可読性を向上させる

保護対象（改行を入れない領域）:
- frontmatter（---で囲まれた部分）
- コードブロック（```で囲まれた部分）
- インラインコード（`で囲まれた部分）
- 引用ブロック（>で始まる行）
- 箇条書き（-, *, 1.で始まる行）
- テーブル（|で区切られた行）
- URL/リンク
"""

import sys
import re
import json
import io

# 標準出力をUTF-8に設定
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def is_protected_line(line):
    """保護対象の行かどうかを判定"""
    stripped = line.strip()

    # 空行
    if not stripped:
        return True

    # 見出し（# で始まる）
    if stripped.startswith('#'):
        return True

    # 引用ブロック（> で始まる）
    if stripped.startswith('>'):
        return True

    # 箇条書き（-, *, + で始まる）
    if re.match(r'^[-*+]\s', stripped):
        return True

    # 番号付きリスト（1. 2. などで始まる）
    if re.match(r'^\d+\.\s', stripped):
        return True

    # テーブル（| を含む）
    if '|' in stripped and stripped.startswith('|'):
        return True

    # 画像/リンクのみの行
    if re.match(r'^!\[.*\]\(.*\)$', stripped) or re.match(r'^\[.*\]\(.*\)$', stripped):
        return True

    # コードブロック開始/終了
    if stripped.startswith('```'):
        return True

    # frontmatter区切り
    if stripped == '---':
        return True

    return False


def add_sentence_breaks_to_line(line):
    """
    行内の句点（。）の後に改行を挿入
    ただし、インラインコードやリンク内は保護
    """
    if not line.strip():
        return line

    # インラインコードとリンクをプレースホルダーで保護
    placeholders = []

    def save_placeholder(match):
        placeholders.append(match.group())
        return f"__PLACEHOLDER_{len(placeholders) - 1}__"

    # インラインコードを保護（`...`）
    protected_line = re.sub(r'`[^`]+`', save_placeholder, line)

    # リンクを保護（[text](url)）
    protected_line = re.sub(r'\[[^\]]*\]\([^\)]*\)', save_placeholder, protected_line)

    # URLを保護（https://... や http://...）
    protected_line = re.sub(r'https?://[^\s）」』\)]+', save_placeholder, protected_line)

    # 句点の後に改行を挿入（既に改行がある場合は追加しない）
    # 「。」の後にテキストが続く場合のみ改行を挿入
    result = re.sub(r'。(?![\n$])', '。\n', protected_line)

    # プレースホルダーを復元
    for i, placeholder in enumerate(placeholders):
        result = result.replace(f"__PLACEHOLDER_{i}__", placeholder)

    return result


def process_content(content):
    """
    コンテンツ全体を処理し、句点改行を挿入
    """
    # frontmatterを分離
    frontmatter = ""
    body = content

    frontmatter_match = re.match(r'^(---\n.*?\n---\n)', content, flags=re.DOTALL)
    if frontmatter_match:
        frontmatter = frontmatter_match.group(1)
        body = content[len(frontmatter):]

    # コードブロックをプレースホルダーで保護
    code_blocks = []

    def save_code_block(match):
        code_blocks.append(match.group())
        return f"__CODE_BLOCK_{len(code_blocks) - 1}__"

    body = re.sub(r'```.*?```', save_code_block, body, flags=re.DOTALL)

    # 行ごとに処理
    lines = body.split('\n')
    processed_lines = []

    for line in lines:
        # プレースホルダー行はそのまま
        if '__CODE_BLOCK_' in line:
            processed_lines.append(line)
            continue

        # 保護対象の行はそのまま
        if is_protected_line(line):
            processed_lines.append(line)
            continue

        # 通常段落に句点改行を挿入
        processed_line = add_sentence_breaks_to_line(line)
        processed_lines.append(processed_line)

    result = '\n'.join(processed_lines)

    # コードブロックを復元
    for i, block in enumerate(code_blocks):
        result = result.replace(f"__CODE_BLOCK_{i}__", block)

    # 連続した空行を正規化（3つ以上の改行を2つに）
    result = re.sub(r'\n{3,}', '\n\n', result)

    return frontmatter + result


def count_changes(original, processed):
    """変更箇所をカウント"""
    # 句点の後の改行数を比較
    original_breaks = len(re.findall(r'。\n', original))
    processed_breaks = len(re.findall(r'。\n', processed))
    return processed_breaks - original_breaks


def get_preview(original, processed, max_examples=5):
    """変更のプレビューを取得"""
    examples = []

    # 差分を行単位で比較
    original_lines = original.split('\n')
    processed_lines = processed.split('\n')

    # 処理後の方が行数が多い場合、変更箇所を特定
    # 簡易的に、句点改行が追加された箇所をサンプル表示
    processed_text = processed

    # 「。\n」の後にテキストが続くパターンを検索
    pattern = r'。\n([^\n#>\-*|`\d])'
    matches = list(re.finditer(pattern, processed_text))

    for match in matches[:max_examples]:
        # マッチ位置の前後を取得
        start = max(0, match.start() - 30)
        end = min(len(processed_text), match.end() + 30)
        context = processed_text[start:end].replace('\n', '↵\n')
        examples.append({
            "context": context,
            "position": match.start()
        })

    return examples


def main():
    if len(sys.argv) < 2:
        print("Usage: python add_sentence_breaks.py <markdown_file> [--fix] [--dry-run]")
        print("  --fix: Apply changes and save to file")
        print("  --dry-run: Show what would be changed without applying")
        sys.exit(1)

    filepath = sys.argv[1]
    apply_fix = "--fix" in sys.argv
    dry_run = "--dry-run" in sys.argv

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 処理を実行
        processed = process_content(content)
        changes_count = count_changes(content, processed)

        if apply_fix and not dry_run:
            # ファイルに書き込み
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(processed)

            result = {
                "status": "fixed",
                "file": filepath,
                "sentence_breaks_added": changes_count,
                "message": f"{changes_count}箇所に句点改行を挿入しました"
            }
        else:
            # チェックのみ（またはdry-run）
            preview = get_preview(content, processed)

            result = {
                "status": "preview" if dry_run else "check",
                "file": filepath,
                "sentence_breaks_to_add": changes_count,
                "preview_examples": preview,
                "message": f"{changes_count}箇所に句点改行を挿入できます" if changes_count > 0 else "句点改行の追加は不要です"
            }

            if dry_run:
                result["processed_content"] = processed

        print(json.dumps(result, ensure_ascii=False, indent=2))

    except FileNotFoundError:
        print(json.dumps({
            "status": "error",
            "message": f"File '{filepath}' not found"
        }, ensure_ascii=False))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "message": str(e)
        }, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
