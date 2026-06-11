"""命名サポートモジュールのテスト（API呼び出しはモック想定）。"""
from app.naming import NAMING_SYSTEM_PROMPT, _build_naming_payload, _name_key


def test_naming_system_prompt_size():
    """Opus 4.8 のキャッシュ最低閾値 4096 トークンを超えるか"""
    # 2800字超なら日本語1.5倍計算で4200トークン超え、確実にキャッシュされる
    assert len(NAMING_SYSTEM_PROMPT) >= 2800


def test_naming_prompt_has_key_concepts():
    """命名プロンプトの必須概念が含まれるか"""
    must_have = [
        "象山流",
        "起名学",
        "先祖の意思",
        "五行の補完",
        "調候用神",
        "苗字との相性",
        "音の響きと意味",
        "画数による吉凶判定はしない",
    ]
    for kw in must_have:
        assert kw in NAMING_SYSTEM_PROMPT, f"必須概念がない: {kw}"


def test_name_key_deterministic():
    k1 = _name_key("中井", 2026, 7, 15, None, "M", "")
    k2 = _name_key("中井", 2026, 7, 15, None, "M", "")
    assert k1 == k2


def test_name_key_differs_by_surname():
    k1 = _name_key("中井", 2026, 7, 15, None, "M", "")
    k2 = _name_key("田中", 2026, 7, 15, None, "M", "")
    assert k1 != k2


def test_build_payload_contains_meishiki_and_surname():
    payload = _build_naming_payload(
        surname="中井",
        year=2026,
        month=7,
        day=15,
        hour=None,
        sex="M",
        parent_wish="",
    )
    assert "苗字: 中井" in payload
    assert "性別: 男性" in payload
    assert "# 命式" in payload
    assert "# 五行バランス" in payload
    assert "# 調候用神" in payload
    assert "- 中" in payload
    assert "- 井" in payload


def test_build_payload_includes_parent_wish():
    payload = _build_naming_payload(
        surname="中井",
        year=2026,
        month=7,
        day=15,
        hour=None,
        sex="M",
        parent_wish="読み方は「あ」で始めたい、優しい印象の漢字を希望",
    )
    assert "# 両親の希望" in payload
    assert "優しい印象" in payload
