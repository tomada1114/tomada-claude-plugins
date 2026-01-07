#!/usr/bin/env python3
"""
SRTファイルから長い字幕（指定文字数超）を検出するスクリプト

Usage:
    python detect_long_subtitles.py input.srt [--max-chars 20]

出力: JSON形式で長い字幕のリストを表示
"""

import sys
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class SubtitleBlock:
    """字幕ブロック"""
    number: int
    start: str
    end: str
    text: str
    length: int


def parse_srt(content: str) -> list[SubtitleBlock]:
    """SRTファイルをパースしてSubtitleBlockのリストを返す"""
    blocks = []
    lines = content.split('\n')

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 番号行（数字のみ）
        if line.isdigit():
            number = int(line)
            i += 1

            # タイムコード行
            if i < len(lines) and '-->' in lines[i]:
                timecode = lines[i].strip()
                parts = timecode.split(' --> ')
                start = parts[0] if len(parts) > 0 else ''
                end = parts[1] if len(parts) > 1 else ''
                i += 1

                # テキスト行（空行まで）
                text_lines = []
                while i < len(lines) and lines[i].strip():
                    text_lines.append(lines[i].strip())
                    i += 1

                text = ''.join(text_lines)  # 改行なしで結合
                blocks.append(SubtitleBlock(
                    number=number,
                    start=start,
                    end=end,
                    text=text,
                    length=len(text)
                ))
        else:
            i += 1

    return blocks


def detect_long_subtitles(blocks: list[SubtitleBlock], max_chars: int) -> list[SubtitleBlock]:
    """指定文字数を超える字幕を検出"""
    return [b for b in blocks if b.length > max_chars]


def main():
    parser = argparse.ArgumentParser(
        description='SRTファイルから長い字幕を検出'
    )
    parser.add_argument('input', help='入力SRTファイル')
    parser.add_argument('--max-chars', type=int, default=24,
                        help='1行あたりの最大文字数（デフォルト: 24）')

    args = parser.parse_args()

    try:
        input_file = Path(args.input)
        if not input_file.exists():
            print(f'{{"error": "ファイルが見つかりません: {args.input}"}}')
            sys.exit(1)

        content = input_file.read_text(encoding='utf-8-sig')  # BOM対応
        blocks = parse_srt(content)
        long_subtitles = detect_long_subtitles(blocks, args.max_chars)

        result = {
            'total': len(blocks),
            'max_chars': args.max_chars,
            'count': len(long_subtitles),
            'long_subtitles': [asdict(b) for b in long_subtitles]
        }

        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        print(f'{{"error": "{e}"}}')
        sys.exit(1)


if __name__ == "__main__":
    main()
