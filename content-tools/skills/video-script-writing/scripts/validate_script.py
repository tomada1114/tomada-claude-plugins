#!/usr/bin/env python3
"""
YouTube台本バリデーションスクリプト

台本ファイルを評価し、7軸のスコアを算出する。
Marpスライドファイルの場合はスピーカーノートを抽出して評価する。
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def is_marp_file(content: str) -> bool:
    """Marpファイルかどうかを判定"""
    # front matterにmarp: trueがあるか
    return bool(re.search(r'^---\s*\nmarp:\s*true', content, re.MULTILINE))


def extract_speaker_notes(content: str) -> str:
    """Marpファイルからスピーカーノートを抽出

    HTMLコメント（<!-- ... -->）の中身を抽出し、
    Marpディレクティブ（_class:, _paginate: など）は除外する。
    """
    pattern = r'<!--\s*([\s\S]*?)\s*-->'
    notes = re.findall(pattern, content)

    # Marpディレクティブを除外
    # _class:, _paginate:, _header:, _footer:, _backgroundColor: など
    filtered_notes = []
    for note in notes:
        note = note.strip()
        # _で始まるMarpディレクティブは除外
        if note and not note.startswith('_'):
            filtered_notes.append(note)

    return '\n\n'.join(filtered_notes)


@dataclass(frozen=True)
class AxisScore:
    """評価軸のスコア"""

    name: str
    score: float
    max_score: float
    threshold: float
    passed: bool
    details: list[str]


@dataclass(frozen=True)
class EvaluationResult:
    """評価結果"""

    total_score: float
    grade: str
    passed: bool
    axes: list[AxisScore]
    ng_words_found: list[str]
    improvement_suggestions: list[str]


# NGワードパターン
NG_PATTERNS = [
    # 誇大表現
    (r"ヤバい|やばい|ヤバ", "誇大表現「ヤバい」"),
    (r"神(?!経|社|様|話|秘)", "誇大表現「神」"),
    (r"最強", "誇大表現「最強」"),
    (r"爆速", "誇大表現「爆速」"),
    (r"革命的", "誇大表現「革命的」"),
    (r"チート級", "誇大表現「チート級」"),
    # 過度な断定
    (r"絶対(?!に.{0,5}ない)", "過度な断定「絶対」"),
    (r"必ず(?!しも)", "過度な断定「必ず」"),
    (r"間違いなく", "過度な断定「間違いなく」"),
    (r"100%", "過度な断定「100%」"),
    # 安易な約束
    (r"簡単です", "安易な約束「簡単です」"),
    (r"すぐできます", "安易な約束「すぐできます」"),
    (r"誰でもできます", "安易な約束「誰でもできます」"),
    (r"失敗しません", "安易な約束「失敗しません」"),
    # 視聴者を下に見る
    (r"知らないと損", "煽り表現「知らないと損」"),
    (r"まだやってないの", "上から目線「まだやってないの」"),
    (r"常識ですが", "上から目線「常識ですが」"),
    # 品のない表現
    (r"ぶっちゃけ", "品のない表現「ぶっちゃけ」"),
    (r"クソ", "品のない表現「クソ」"),
    (r"ガチで", "品のない表現「ガチで」"),
]

# 語尾パターン
GOBI_PATTERNS = [
    r"ですね[。\n]",
    r"になります[。\n]",
    r"でしょう[。\n]",
    r"ということです[。\n]",
    r"てくる[。\n]",
    r"ていく[。\n]",
    r"してみましょう[。\n]",
    r"できます[。\n]",
]

# 親近感表現
SHINKINKAN_PATTERNS = [
    r"私も",
    r"皆さんも",
    r"私の場合",
    r"正直に言うと",
    r"実は私も",
]

# 強調語
KYOCHO_PATTERNS = [
    r"めちゃくちゃ",
    r"かなり",
    r"結構",
    r"本当に",
    r"なんと",
    r"非常に",
]

# 問いかけパターン
TOIKAKE_PATTERNS = [
    r"ないでしょうか",
    r"と思いませんか",
    r"ではありませんか",
    r"どうでしょうか",
]

# リスク言及パターン
RISK_PATTERNS = [
    r"注意",
    r"リスク",
    r"費用",
    r"セキュリティ",
    r"公開しない",
    r"厳重に管理",
]

# CTAパターン
CTA_PATTERNS = [
    r"チャンネル登録",
    r"高評価",
    r"コメント",
]


def check_ng_words(content: str) -> list[str]:
    """NGワードをチェック"""
    found = []
    for pattern, description in NG_PATTERNS:
        if re.search(pattern, content):
            found.append(description)
    return found


def count_pattern_matches(content: str, patterns: list[str]) -> int:
    """パターンのマッチ数をカウント"""
    count = 0
    for pattern in patterns:
        count += len(re.findall(pattern, content))
    return count


def count_unique_patterns(content: str, patterns: list[str]) -> int:
    """ユニークなパターンのマッチ数をカウント"""
    count = 0
    for pattern in patterns:
        if re.search(pattern, content):
            count += 1
    return count


def calculate_sentence_lengths(content: str) -> tuple[int, int, float]:
    """文の長さを計算（合計、40字以内の数、割合）"""
    # 句点で分割
    sentences = re.split(r"[。\n]", content)
    sentences = [s.strip() for s in sentences if s.strip()]

    total = len(sentences)
    if total == 0:
        return 0, 0, 0.0

    short_count = sum(1 for s in sentences if len(s) <= 40)
    ratio = short_count / total

    return total, short_count, ratio


def has_structure(content: str) -> tuple[bool, bool, bool]:
    """3部構成をチェック（冒頭、本編、締め）"""
    has_intro = bool(
        re.search(r"(冒頭|## 冒頭|問題提起|ないでしょうか)", content)
    )
    has_main = bool(
        re.search(r"(本編|## 本編|セクション|### セクション)", content)
    )
    has_ending = bool(re.search(r"(締め|## 締め|まとめ|ということで)", content))
    return has_intro, has_main, has_ending


def evaluate_script(content: str) -> EvaluationResult:
    """台本を評価"""
    axes = []
    suggestions = []

    # 1. Structure Score (20pt)
    has_intro, has_main, has_ending = has_structure(content)
    structure_score = 0.0
    structure_details = []

    if has_intro:
        structure_score += 7
        structure_details.append("冒頭あり")
    else:
        structure_details.append("冒頭なし")
        suggestions.append("Structure: 冒頭に問題提起を追加する")

    if has_main:
        structure_score += 7
        structure_details.append("本編あり")
    else:
        structure_details.append("本編なし")
        suggestions.append("Structure: 本編セクションを追加する")

    if has_ending:
        structure_score += 6
        structure_details.append("締めあり")
    else:
        structure_details.append("締めなし")
        suggestions.append("Structure: 締めに要約とCTAを追加する")

    axes.append(
        AxisScore(
            name="Structure",
            score=structure_score,
            max_score=20,
            threshold=16,
            passed=structure_score >= 16,
            details=structure_details,
        )
    )

    # 2. Speech Pattern Score (20pt)
    gobi_count = count_unique_patterns(content, GOBI_PATTERNS)
    shinkinkan_count = count_pattern_matches(content, SHINKINKAN_PATTERNS)
    kyocho_count = count_pattern_matches(content, KYOCHO_PATTERNS)

    speech_score = 0.0
    speech_details = []

    # 語尾の多様性 (6pt)
    if gobi_count >= 3:
        speech_score += 6
        speech_details.append(f"語尾パターン{gobi_count}種類")
    else:
        speech_score += gobi_count * 2
        speech_details.append(f"語尾パターン{gobi_count}種類（3種類以上推奨）")
        suggestions.append(
            f"Speech Pattern: 語尾パターンを増やす（現在{gobi_count}→3種類以上）"
        )

    # 親近感表現 (6pt)
    if shinkinkan_count >= 2:
        speech_score += 6
        speech_details.append(f"親近感表現{shinkinkan_count}個")
    else:
        speech_score += shinkinkan_count * 3
        speech_details.append(f"親近感表現{shinkinkan_count}個（2個以上推奨）")
        suggestions.append(
            f"Speech Pattern: 「私も〜」などの親近感表現を追加する（現在{shinkinkan_count}個）"
        )

    # 強調語 (4pt)
    if kyocho_count >= 2:
        speech_score += 4
        speech_details.append(f"強調語{kyocho_count}個")
    else:
        speech_score += kyocho_count * 2
        speech_details.append(f"強調語{kyocho_count}個")

    # 段階的説明 (4pt) - 簡易チェック
    if re.search(r"とは|まず|次に|最後に", content):
        speech_score += 4
        speech_details.append("段階的説明あり")
    else:
        speech_details.append("段階的説明なし")

    axes.append(
        AxisScore(
            name="Speech Pattern",
            score=speech_score,
            max_score=20,
            threshold=16,
            passed=speech_score >= 16,
            details=speech_details,
        )
    )

    # 3. Engagement Score (15pt)
    toikake_count = count_pattern_matches(content, TOIKAKE_PATTERNS)
    minna_count = len(re.findall(r"皆さん|あなた|一緒に", content))
    has_experience = bool(re.search(r"私も|私の場合", content))

    engagement_score = 0.0
    engagement_details = []

    if toikake_count >= 2:
        engagement_score += 5
        engagement_details.append(f"問いかけ{toikake_count}回")
    else:
        engagement_score += toikake_count * 2.5
        engagement_details.append(f"問いかけ{toikake_count}回（2回以上推奨）")

    if minna_count >= 3:
        engagement_score += 5
        engagement_details.append(f"包含表現{minna_count}回")
    else:
        engagement_score += minna_count * 1.7
        engagement_details.append(f"包含表現{minna_count}回（3回以上推奨）")

    if has_experience:
        engagement_score += 5
        engagement_details.append("実体験共有あり")
    else:
        engagement_details.append("実体験共有なし")
        suggestions.append("Engagement: 「私も〜」という実体験を追加する")

    axes.append(
        AxisScore(
            name="Engagement",
            score=min(engagement_score, 15),
            max_score=15,
            threshold=12,
            passed=engagement_score >= 12,
            details=engagement_details,
        )
    )

    # 4. Technical Accuracy Score (15pt)
    risk_count = count_pattern_matches(content, RISK_PATTERNS)

    tech_score = 0.0
    tech_details = []

    # 用語の正確性は手動確認が必要なので基本点を付与
    tech_score += 6
    tech_details.append("用語チェック: 手動確認推奨")

    if risk_count >= 1:
        tech_score += 5
        tech_details.append(f"リスク言及{risk_count}回")
    else:
        tech_details.append("リスク言及なし")
        suggestions.append("Technical: セキュリティ・費用リスクへの言及を追加する")

    # 信頼性は手動確認
    tech_score += 4
    tech_details.append("信頼性チェック: 手動確認推奨")

    axes.append(
        AxisScore(
            name="Technical Accuracy",
            score=tech_score,
            max_score=15,
            threshold=12,
            passed=tech_score >= 12,
            details=tech_details,
        )
    )

    # 5. Readability Score (15pt)
    total_sentences, short_sentences, short_ratio = calculate_sentence_lengths(content)

    read_score = 0.0
    read_details = []

    # 文の長さ (6pt)
    if short_ratio >= 0.8:
        read_score += 6
        read_details.append(f"短文率{short_ratio*100:.0f}%")
    else:
        read_score += short_ratio * 7.5
        read_details.append(f"短文率{short_ratio*100:.0f}%（80%以上推奨）")
        suggestions.append(
            f"Readability: 長い文を分割する（現在{short_ratio*100:.0f}%→80%以上）"
        )

    # 段落構成 (5pt)
    paragraph_count = len(re.findall(r"\n\n", content))
    if paragraph_count >= 5:
        read_score += 5
        read_details.append(f"段落{paragraph_count}個")
    else:
        read_score += paragraph_count
        read_details.append(f"段落{paragraph_count}個")

    # リズム (4pt) - 簡易チェック
    read_score += 4
    read_details.append("リズムチェック: 音読確認推奨")

    axes.append(
        AxisScore(
            name="Readability",
            score=min(read_score, 15),
            max_score=15,
            threshold=12,
            passed=read_score >= 12,
            details=read_details,
        )
    )

    # 6. NG Word Score (10pt)
    ng_words = check_ng_words(content)

    if len(ng_words) == 0:
        ng_score = 10.0
        ng_passed = True
        ng_details = ["NGワードなし"]
    else:
        ng_score = 0.0
        ng_passed = False
        ng_details = [f"NGワード検出: {', '.join(ng_words)}"]
        suggestions.extend([f"NG Word: 「{w}」を削除または言い換える" for w in ng_words])

    axes.append(
        AxisScore(
            name="NG Word",
            score=ng_score,
            max_score=10,
            threshold=10,
            passed=ng_passed,
            details=ng_details,
        )
    )

    # 7. CTA Score (5pt)
    cta_count = count_unique_patterns(content, CTA_PATTERNS)

    cta_score = 0.0
    cta_details = []

    if "チャンネル登録" in content:
        cta_score += 2
        cta_details.append("チャンネル登録あり")
    else:
        cta_details.append("チャンネル登録なし")

    if "高評価" in content:
        cta_score += 2
        cta_details.append("高評価あり")
    else:
        cta_details.append("高評価なし")

    if "コメント" in content:
        cta_score += 1
        cta_details.append("コメント促進あり")
    else:
        cta_details.append("コメント促進なし")

    if cta_score < 4:
        suggestions.append("CTA: チャンネル登録・高評価の呼びかけを追加する")

    axes.append(
        AxisScore(
            name="CTA",
            score=cta_score,
            max_score=5,
            threshold=4,
            passed=cta_score >= 4,
            details=cta_details,
        )
    )

    # 総合評価
    total_score = sum(axis.score for axis in axes)
    all_passed = all(axis.passed for axis in axes)

    if total_score >= 95:
        grade = "A+"
    elif total_score >= 90:
        grade = "A"
    elif total_score >= 80:
        grade = "B+"
    elif total_score >= 70:
        grade = "B"
    else:
        grade = "C"

    return EvaluationResult(
        total_score=total_score,
        grade=grade,
        passed=total_score >= 90 and all_passed,
        axes=axes,
        ng_words_found=ng_words,
        improvement_suggestions=suggestions,
    )


def print_result(result: EvaluationResult) -> None:
    """結果を出力"""
    print("=" * 60)
    print("YouTube台本評価レポート")
    print("=" * 60)
    print()
    print(f"総合スコア: {result.total_score:.1f}/100")
    print(f"グレード: {result.grade}")
    print(f"合格: {'はい' if result.passed else 'いいえ'}")
    print()
    print("-" * 60)
    print("軸別スコア")
    print("-" * 60)

    for axis in result.axes:
        status = "✅" if axis.passed else "❌"
        print(
            f"{status} {axis.name}: {axis.score:.1f}/{axis.max_score} "
            f"(閾値: {axis.threshold})"
        )
        for detail in axis.details:
            print(f"   - {detail}")

    if result.ng_words_found:
        print()
        print("-" * 60)
        print("検出されたNGワード")
        print("-" * 60)
        for word in result.ng_words_found:
            print(f"❌ {word}")

    if result.improvement_suggestions:
        print()
        print("-" * 60)
        print("改善提案")
        print("-" * 60)
        for suggestion in result.improvement_suggestions:
            print(f"→ {suggestion}")

    print()
    print("=" * 60)


def main() -> int:
    """メイン関数"""
    if len(sys.argv) < 2:
        print("Usage: python validate_script.py <script_file>")
        print("Example: python validate_script.py script.md")
        print("         python validate_script.py slides.md  # Marpファイルの場合はスピーカーノートを評価")
        return 1

    script_path = Path(sys.argv[1])
    if not script_path.exists():
        print(f"Error: File not found: {script_path}")
        return 1

    content = script_path.read_text(encoding="utf-8")

    # Marpファイルの場合はスピーカーノートを抽出
    if is_marp_file(content):
        print("Marpファイルを検出: スピーカーノートを抽出して評価します")
        print()
        content = extract_speaker_notes(content)
        if not content.strip():
            print("Error: スピーカーノートが見つかりません")
            return 1

    result = evaluate_script(content)
    print_result(result)

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
