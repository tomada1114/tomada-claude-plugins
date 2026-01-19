#!/usr/bin/env python3
"""
音声入力誤変換の機械的修正スクリプト

Usage:
  python fix_transcription.py <file_or_directory>
  python fix_transcription.py --dry-run <file>  # 変更を適用せずプレビュー

Output: JSON形式で修正結果を出力
"""

import sys
import json
import re
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DICT_PATH = SCRIPT_DIR.parent / "dictionaries" / "misconversion-dict.json"


class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    END = '\033[0m'


def load_dictionary():
    """辞書ファイルを読み込み"""
    with open(DICT_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def apply_exact_matches(text, exact_match_dict):
    """exact_match パターンを適用"""
    fixes = []
    for category, patterns in exact_match_dict.items():
        if isinstance(patterns, dict):
            for wrong, correct in patterns.items():
                if wrong in text:
                    count = text.count(wrong)
                    text = text.replace(wrong, correct)
                    fixes.append({
                        "type": "exact",
                        "category": category,
                        "from": wrong,
                        "to": correct,
                        "count": count
                    })
    return text, fixes


def apply_regex_patterns(text, regex_patterns):
    """regex_patterns を適用"""
    fixes = []
    for pattern_obj in regex_patterns:
        pattern = pattern_obj["pattern"]
        replacement = pattern_obj["replacement"]
        try:
            matches = re.findall(pattern, text)
            if matches:
                text = re.sub(pattern, replacement, text)
                fixes.append({
                    "type": "regex",
                    "pattern": pattern,
                    "to": replacement,
                    "count": len(matches)
                })
        except re.error as e:
            # 正規表現エラーは警告のみ
            print(f"Warning: Invalid regex pattern '{pattern}': {e}", file=sys.stderr)
    return text, fixes


def process_file(file_path, dictionary, dry_run=False):
    """単一ファイルを処理"""
    file_path = Path(file_path)

    if not file_path.exists():
        return {
            "path": str(file_path),
            "error": "File not found",
            "modified": False,
            "fixes": [],
            "total_fixes": 0
        }

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original = f.read()
    except UnicodeDecodeError:
        return {
            "path": str(file_path),
            "error": "Unable to read file (encoding error)",
            "modified": False,
            "fixes": [],
            "total_fixes": 0
        }

    text = original
    all_fixes = []

    # Phase 1a: exact_match
    text, fixes = apply_exact_matches(text, dictionary.get("exact_match", {}))
    all_fixes.extend(fixes)

    # Phase 1b: regex_patterns
    text, fixes = apply_regex_patterns(text, dictionary.get("regex_patterns", []))
    all_fixes.extend(fixes)

    # ファイル更新（dry_runでなければ）
    modified = text != original
    if not dry_run and modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)

    return {
        "path": str(file_path),
        "modified": modified,
        "fixes": all_fixes,
        "total_fixes": sum(f["count"] for f in all_fixes)
    }


def process_directory(dir_path, dictionary, dry_run=False):
    """ディレクトリ内の対象ファイルを処理"""
    dir_path = Path(dir_path)
    results = []

    # txt と md ファイルを対象
    for pattern in ["*.txt", "*.md"]:
        for file_path in dir_path.glob(pattern):
            result = process_file(file_path, dictionary, dry_run)
            results.append(result)

    return results


def print_summary(results, dry_run=False):
    """結果サマリを表示"""
    total_files = len(results)
    modified_files = sum(1 for r in results if r.get("modified", False))
    total_fixes = sum(r.get("total_fixes", 0) for r in results)

    mode = "[DRY-RUN] " if dry_run else ""

    print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.CYAN}{mode}Phase 1: 機械的置換 完了{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"処理ファイル数: {total_files}件")
    print(f"修正あり: {Colors.GREEN}{modified_files}件{Colors.END}")
    print(f"修正なし: {total_files - modified_files}件")
    print(f"総修正件数: {Colors.GREEN}{total_fixes}件{Colors.END}")

    if modified_files > 0:
        print(f"\n{Colors.YELLOW}修正内容:{Colors.END}")
        for result in results:
            if result.get("modified", False):
                path = Path(result["path"]).name
                fixes = result.get("fixes", [])
                fix_count = result.get("total_fixes", 0)

                # 修正例を3件まで表示
                examples = []
                for fix in fixes[:3]:
                    if fix["type"] == "exact":
                        examples.append(f"{fix['from']}→{fix['to']}")
                    else:
                        examples.append(f"[regex] →{fix['to']}")

                example_str = ", ".join(examples)
                if len(fixes) > 3:
                    example_str += f" 他{len(fixes)-3}件"

                print(f"  - {path}: {fix_count}件 ({example_str})")


def main():
    parser = argparse.ArgumentParser(
        description='音声入力誤変換の機械的修正スクリプト'
    )
    parser.add_argument(
        'path',
        help='処理対象のファイルまたはディレクトリ'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='変更を適用せずプレビューのみ'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='JSON形式で出力（LLM連携用）'
    )

    args = parser.parse_args()
    path = Path(args.path)

    # 辞書読み込み
    try:
        dictionary = load_dictionary()
    except FileNotFoundError:
        print(f"Error: Dictionary file not found: {DICT_PATH}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in dictionary: {e}", file=sys.stderr)
        sys.exit(1)

    # 処理実行
    if path.is_file():
        results = [process_file(path, dictionary, args.dry_run)]
    elif path.is_dir():
        results = process_directory(path, dictionary, args.dry_run)
    else:
        print(f"Error: Path not found: {path}", file=sys.stderr)
        sys.exit(1)

    # 出力
    if args.json:
        output = {
            "phase": "mechanical_replacement",
            "dry_run": args.dry_run,
            "files_processed": len(results),
            "files_modified": sum(1 for r in results if r.get("modified", False)),
            "total_fixes": sum(r.get("total_fixes", 0) for r in results),
            "results": results,
            "context_hints": dictionary.get("context_dependent", [])
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print_summary(results, args.dry_run)

    # 修正があった場合は0、なければ1
    has_modifications = any(r.get("modified", False) for r in results)
    sys.exit(0 if has_modifications else 1)


if __name__ == "__main__":
    main()
