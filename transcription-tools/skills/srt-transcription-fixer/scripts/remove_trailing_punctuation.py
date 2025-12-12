#!/usr/bin/env python3
"""
SRTファイルの各字幕行末から句読点（、。）を削除するスクリプト

Usage:
    python remove_trailing_punctuation.py input.srt [output.srt]

    output.srtを省略すると、input.srtを上書きします。
"""

import sys
import re
from pathlib import Path


def remove_trailing_punctuation(text: str) -> str:
    """行末の句読点（、。）を削除"""
    return re.sub(r'[、。]+$', '', text)


def process_srt(input_path: str, output_path: str | None = None) -> tuple[int, list[str]]:
    """
    SRTファイルを処理し、各字幕の行末句読点を削除

    Returns:
        tuple: (修正した行数, 修正内容のリスト)
    """
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"ファイルが見つかりません: {input_path}")

    content = input_file.read_text(encoding='utf-8')
    lines = content.split('\n')

    modified_count = 0
    modifications = []
    result_lines = []

    # SRT形式: 番号、タイムコード、テキスト、空行の繰り返し
    i = 0
    while i < len(lines):
        line = lines[i]

        # 番号行（数字のみ）
        if line.strip().isdigit():
            result_lines.append(line)
            i += 1

            # タイムコード行
            if i < len(lines):
                result_lines.append(lines[i])
                i += 1

            # テキスト行（空行まで）
            while i < len(lines) and lines[i].strip():
                original = lines[i]
                modified = remove_trailing_punctuation(original)

                if original != modified:
                    modified_count += 1
                    modifications.append(f"  {original} → {modified}")

                result_lines.append(modified)
                i += 1
        else:
            # 空行やその他
            result_lines.append(line)
            i += 1

    # 出力
    output_file = Path(output_path) if output_path else input_file
    output_file.write_text('\n'.join(result_lines), encoding='utf-8')

    return modified_count, modifications


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        count, mods = process_srt(input_path, output_path)

        if count > 0:
            print(f"✅ {count}箇所の行末句読点を削除しました")
            for mod in mods[:10]:  # 最初の10件を表示
                print(mod)
            if len(mods) > 10:
                print(f"  ... 他 {len(mods) - 10} 件")
        else:
            print("✅ 削除すべき行末句読点はありませんでした")

    except FileNotFoundError as e:
        print(f"❌ エラー: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 予期せぬエラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
