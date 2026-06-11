"""judgment モジュールの単体テスト（API は呼ばない）。"""
from app.bazi import calc_meishiki
from app.judgment import SYSTEM_PROMPT, _build_payload, _format_pillar, _meishiki_key
from app.shozan import reading


def test_system_prompt_size_for_cache():
    # Opus 4.8 のプロンプトキャッシュ最低閾値は 4096 トークン。
    # 日本語トークナイザは概ね文字数 × 1.3〜1.7。4000字超なら確実に閾値を超える。
    assert len(SYSTEM_PROMPT) >= 4000, f"システムプロンプトが短すぎ: {len(SYSTEM_PROMPT)}字"


def test_system_prompt_declares_shozan_ryu():
    assert "象山流" in SYSTEM_PROMPT
    assert "田邊象山" in SYSTEM_PROMPT
    assert "開運法" in SYSTEM_PROMPT
    assert "起名学" in SYSTEM_PROMPT


def test_meishiki_key_is_deterministic():
    m1 = calc_meishiki(1985, 5, 20, 10)
    m2 = calc_meishiki(1985, 5, 20, 10)
    assert _meishiki_key(m1, None, None) == _meishiki_key(m2, None, None)


def test_meishiki_key_differs_by_name():
    m = calc_meishiki(1985, 5, 20, 10)
    assert _meishiki_key(m, None, None) != _meishiki_key(m, "中井利幸", "M")


def test_meishiki_key_differs_by_sex():
    m = calc_meishiki(1985, 5, 20, 10)
    assert _meishiki_key(m, "中井利幸", "M") != _meishiki_key(m, "中井利幸", "F")


def test_payload_for_kaito_has_all_sections():
    """中井さんの命式payloadに必要なセクションが揃うか"""
    m = calc_meishiki(1976, 5, 4, 4)
    r = reading(m, year=1976, month=5, day=4, sex="M")
    payload = _build_payload(m, r, "中井利幸", "M")

    # セクションヘッダ
    assert "# 命式" in payload
    assert "# 五行バランス" in payload
    assert "# 吉神・凶神・空亡" in payload
    assert "# 調候用神" in payload
    assert "# 大運" in payload
    assert "# 名前" in payload

    # 重要な命式要素
    assert "日干: 丙（火・陽・身弱）" in payload
    assert "年柱: 丙辰" in payload
    assert "時柱: 庚寅" in payload
    assert "空亡:子・丑" in payload
    assert "壬・甲" in payload  # 調候用神
    assert "華蓋:有" in payload
    assert "中井利幸（男性）" in payload


def test_payload_without_name_omits_name_section():
    m = calc_meishiki(2000, 1, 1)
    r = reading(m, year=2000, month=1, day=1, sex="F")
    payload = _build_payload(m, r, None, None)
    assert "# 名前" not in payload


def test_format_pillar_day_pillar_has_nikkan_marker():
    m = calc_meishiki(1985, 5, 20, 10)
    line = _format_pillar(m.day, m.nikkan)
    assert "（日主）" in line
    assert "十二運:" in line
