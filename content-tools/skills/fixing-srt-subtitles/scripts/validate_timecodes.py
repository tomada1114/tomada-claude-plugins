#!/usr/bin/env python3
"""
SRTファイルのタイムコード異常を検出・修正するスクリプト

Usage:
    python validate_timecodes.py input.srt [--check] [--output output.srt]

問題パターン:
    終了時間の「分」フィールドが開始時間より小さい場合
    例: 00:02:38,714 --> 00:00:40,190 (分が02→00に)

    この問題はWhisper等の文字起こしツールで発生することがある

出力: JSON形式で検証結果を表示
"""

import sys
import json
import argparse
import re
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class TimecodeError:
    """タイムコードエラー情報"""
    type: str
    number: int
    start: str
    end_before: str
    end_after: str | None
    message: str


def parse_to_milliseconds(timecode: str) -> int:
    """タイムコードをミリ秒に変換

    Args:
        timecode: "HH:MM:SS,mmm" 形式の文字列

    Returns:
        ミリ秒単位の整数値
    """
    match = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', timecode)
    if not match:
        raise ValueError(f"Invalid timecode format: {timecode}")

    hours, minutes, seconds, ms = map(int, match.groups())
    return hours * 3600000 + minutes * 60000 + seconds * 1000 + ms


def milliseconds_to_timecode(ms: int) -> str:
    """ミリ秒をタイムコードに変換

    Args:
        ms: ミリ秒単位の整数値

    Returns:
        "HH:MM:SS,mmm" 形式の文字列
    """
    hours = ms // 3600000
    ms %= 3600000
    minutes = ms // 60000
    ms %= 60000
    seconds = ms // 1000
    milliseconds = ms % 1000

    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def validate_and_fix_timecode(start: str, end: str, number: int) -> tuple[str | None, TimecodeError | None]:
    """タイムコードを検証し、必要に応じて修正する

    Args:
        start: 開始タイムコード
        end: 終了タイムコード
        number: 字幕番号

    Returns:
        (fixed_end, error_info) - fixed_end: 修正後の終了時間（修正不要ならNone）
                                  error_info: エラー情報（問題なければNone）
    """
    try:
        start_ms = parse_to_milliseconds(start)
        end_ms = parse_to_milliseconds(end)
    except ValueError as e:
        return None, TimecodeError(
            type="format_error",
            number=number,
            start=start,
            end_before=end,
            end_after=None,
            message=str(e)
        )

    # 分境界異常検出（主要な問題パターン）
    start_min = (start_ms // 60000) % 60
    end_min = (end_ms // 60000) % 60
    start_sec = (start_ms // 1000) % 60
    end_sec = (end_ms // 1000) % 60

    # パターン1: 同じ分内での異常
    # 例: 00:02:38 --> 00:00:40 (本来は 00:02:40)
    # 開始の分 > 終了の分 かつ 秒数は終了 > 開始 → 分フィールドのキャリー失敗
    if start_min > end_min and end_sec > start_sec:
        # 修正：終了時間の分を開始時間の分に合わせる
        corrected_ms = end_ms + (start_min - end_min) * 60000
        fixed_end = milliseconds_to_timecode(corrected_ms)

        return fixed_end, TimecodeError(
            type="minute_field_error",
            number=number,
            start=start,
            end_before=end,
            end_after=fixed_end,
            message=f"分フィールドを{end_min:02d}→{start_min:02d}に修正しました"
        )

    # パターン2: 分境界をまたぐ異常
    # 例: 00:05:58 --> 00:04:02 (本来は 00:06:02)
    # 開始秒 > 終了秒（分境界をまたぐ）かつ 終了の分が開始の分以下
    if start_sec > end_sec and end_min <= start_min:
        # 修正：終了時間の分を開始時間の分+1に合わせる
        expected_min = start_min + 1
        corrected_ms = end_ms + (expected_min - end_min) * 60000
        fixed_end = milliseconds_to_timecode(corrected_ms)

        return fixed_end, TimecodeError(
            type="minute_field_error",
            number=number,
            start=start,
            end_before=end,
            end_after=fixed_end,
            message=f"分フィールドを{end_min:02d}→{expected_min:02d}に修正しました（分境界またぎ）"
        )

    # 一般的な順序チェック（分境界以外の理由）
    if start_ms >= end_ms:
        return None, TimecodeError(
            type="time_reversal",
            number=number,
            start=start,
            end_before=end,
            end_after=None,
            message="終了時間が開始時間より前です（自動修正不可）"
        )

    return None, None  # 問題なし


def process_srt(input_path: Path, output_path: Path | None, check_only: bool) -> dict:
    """SRTファイルを処理して検証・修正する

    Args:
        input_path: 入力ファイルパス
        output_path: 出力ファイルパス（Noneの場合は入力ファイルを上書き）
        check_only: Trueの場合は検証のみ（修正しない）

    Returns:
        処理結果の辞書
    """
    content = input_path.read_text(encoding='utf-8-sig')  # BOM対応
    lines = content.split('\n')

    errors: list[TimecodeError] = []
    fixed_count = 0
    total_blocks = 0
    modified_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 番号行（数字のみ）
        if stripped.isdigit():
            total_blocks += 1
            number = int(stripped)
            modified_lines.append(line)
            i += 1

            # タイムコード行
            if i < len(lines) and '-->' in lines[i]:
                timecode_line = lines[i]
                parts = timecode_line.strip().split(' --> ')

                if len(parts) == 2:
                    start, end = parts
                    fixed_end, error = validate_and_fix_timecode(start, end, number)

                    if error:
                        errors.append(error)

                        if fixed_end and not check_only:
                            # 修正を適用
                            new_timecode_line = f"{start} --> {fixed_end}"
                            # 元の行のインデントを保持
                            leading_space = len(timecode_line) - len(timecode_line.lstrip())
                            modified_lines.append(' ' * leading_space + new_timecode_line)
                            fixed_count += 1
                        else:
                            modified_lines.append(line)
                    else:
                        modified_lines.append(timecode_line)
                else:
                    modified_lines.append(timecode_line)
                i += 1

            # テキスト行（空行まで）
            while i < len(lines) and lines[i].strip():
                modified_lines.append(lines[i])
                i += 1
        else:
            modified_lines.append(line)
            i += 1

    # 結果の書き出し
    if not check_only and fixed_count > 0:
        output = output_path or input_path
        output.write_text('\n'.join(modified_lines), encoding='utf-8')

    return {
        'file': str(input_path),
        'total': total_blocks,
        'valid': len(errors) == 0,
        'fixed': fixed_count > 0,
        'fixed_count': fixed_count,
        'error_count': len(errors),
        'check_only': check_only,
        'errors': [asdict(e) for e in errors]
    }


def main():
    parser = argparse.ArgumentParser(
        description='SRTファイルのタイムコード異常を検出・修正'
    )
    parser.add_argument('input', help='入力SRTファイル')
    parser.add_argument('--check', action='store_true',
                        help='検証のみ（修正しない）')
    parser.add_argument('--output', '-o', help='出力ファイル（指定しない場合は入力ファイルを上書き）')

    args = parser.parse_args()

    try:
        input_file = Path(args.input)
        if not input_file.exists():
            print(json.dumps({
                'error': f'ファイルが見つかりません: {args.input}'
            }, ensure_ascii=False))
            sys.exit(1)

        output_file = Path(args.output) if args.output else None
        result = process_srt(input_file, output_file, args.check)

        print(json.dumps(result, ensure_ascii=False, indent=2))

        # エラーがある場合は終了コード1
        if result['error_count'] > 0 and (args.check or result['fixed_count'] < result['error_count']):
            sys.exit(1)

    except Exception as e:
        print(json.dumps({
            'error': str(e)
        }, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
