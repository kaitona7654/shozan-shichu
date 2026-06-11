"""フリーミアム抽出ロジックのテスト。

リファレンス鑑定文ドラフト（tests/reference_judgment_kaito.md の本文部分）を
モックの「完全鑑定文」として使い、性格抽出と完全版案内の組み立てを検証。
"""
from app.judgment import FREE_SECTIONS, extract_section, free_excerpt

# モック完全鑑定文（9セクションを模した最小サンプル）
MOCK_FULL = """## 1. 命式概要

丙辰／壬辰／丙辰／庚寅の四柱です。

## 2. 五行バランスと吉神

木5・火5・土7・金2・水5。

## 3. 性格傾向

剛情で派手なものを好み、自分の社会的位置に敏感な性質を持ちます。明朗で表情に出やすく、衣食住への美意識が高い。

## 4. 才能・適職

サラリーマン、サービス業（観光・接客・小売・デパート系）。

## 5. 大運の流れ（今と未来）

現在52-61才は戊戌大運（食神・墓）。

## 6. 今年〜近未来の年廻り

2026年は丙午・帝旺。

## 7. 開運法（象山流の真髄）

1. 青・水色・黒・濃緑の小物を意識的に取り入れる
2. 北方位を味方に

## 8. 起名学評価

井の水と利の禾が調候用神を補う構造。

## 9. 家系・先祖からのメッセージ

派手に動くより、丁寧に蓄える生き方が家系から託されています。

※ 本鑑定は象山流四柱推命の参考鑑定です。
"""


def test_extract_section_3_personality():
    out = extract_section(MOCK_FULL, 3)
    assert "## 3. 性格傾向" in out
    assert "剛情で派手なものを好み" in out
    # 隣接セクションの内容は含まない
    assert "サラリーマン" not in out
    assert "戊戌大運" not in out


def test_extract_section_7_kaiunho():
    out = extract_section(MOCK_FULL, 7)
    assert "開運法" in out
    assert "青・水色・黒・濃緑" in out
    assert "北方位" in out


def test_extract_section_missing_returns_empty():
    assert extract_section(MOCK_FULL, 99) == ""


def test_extract_section_9_last_section():
    out = extract_section(MOCK_FULL, 9)
    assert "家系" in out
    assert "派手に動くより、丁寧に蓄える" in out


def test_free_excerpt_contains_only_personality():
    out = free_excerpt(MOCK_FULL)
    # 性格セクションは含まれる
    assert "剛情で派手なものを好み" in out
    # 他セクションは含まれない（適職・大運・開運法・起名学など）
    assert "サラリーマン" not in out
    assert "戊戌大運" not in out
    assert "青・水色・黒・濃緑" not in out
    assert "井の水と利の禾" not in out
    # 完全鑑定の案内文は含まれる
    assert "完全鑑定" in out
    assert "¥1,500" in out


def test_free_sections_constant():
    assert FREE_SECTIONS == [3]  # 当面は性格傾向のみが無料
