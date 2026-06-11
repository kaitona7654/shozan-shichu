"""_handle_text の単体テスト（LINE SDK を介さない経路）。"""
import os

# main 読み込み前に LINE 資格情報をダミー設定、ANTHROPIC は明示的に外す
os.environ.setdefault("LINE_CHANNEL_ACCESS_TOKEN", "dummy")
os.environ.setdefault("LINE_CHANNEL_SECRET", "dummy")
os.environ.pop("ANTHROPIC_API_KEY", None)

from app import main  # noqa: E402
from app.main import _handle_text  # noqa: E402


def test_help():
    out = _handle_text("ヘルプ")
    assert isinstance(out, list)
    assert any("四柱推命Bot" in m for m in out)


def test_birth_returns_meishiki_only_when_no_api_key():
    # ANTHROPIC_API_KEY なしの初期状態では命式のみ（1メッセージ）
    out = _handle_text("1985/5/20 10")
    assert len(out) == 1
    joined = out[0]
    assert "年柱" in joined and "月柱" in joined and "日柱" in joined and "時柱" in joined
    assert "己未" in joined
    assert "日干: 己" in joined


def test_unparseable():
    out = _handle_text("おはよう")
    assert any("読み取れません" in m for m in out)


def test_birth_with_judgment_full_mode(monkeypatch):
    """FREEMIUM_MODE=False で全文返却を確認"""
    monkeypatch.setattr(main, "ANTHROPIC_ENABLED", True)
    monkeypatch.setattr(main, "FREEMIUM_MODE", False)
    monkeypatch.setattr(
        main,
        "generate_judgment",
        lambda m, r, *, name=None, sex=None: "## 1. 命式概要\nテスト鑑定本文。",
    )
    out = _handle_text("1985/5/20 10 男")
    assert len(out) == 2
    assert "年柱" in out[0]
    assert "象山流鑑定" in out[1]
    assert "テスト鑑定本文" in out[1]


def test_birth_with_judgment_freemium_mode(monkeypatch):
    """FREEMIUM_MODE=True で性格セクションのみ＋案内文"""
    monkeypatch.setattr(main, "ANTHROPIC_ENABLED", True)
    monkeypatch.setattr(main, "FREEMIUM_MODE", True)
    mock_full = (
        "## 1. 命式概要\n命式の説明。\n\n"
        "## 3. 性格傾向\n剛情で派手好み。\n\n"
        "## 4. 才能・適職\nサラリーマン。"
    )
    monkeypatch.setattr(
        main, "generate_judgment", lambda m, r, *, name=None, sex=None: mock_full
    )
    out = _handle_text("1985/5/20 10 男")
    assert len(out) == 2
    assert "無料版" in out[1]
    assert "剛情で派手好み" in out[1]
    # 他セクションは含まれない
    assert "命式の説明" not in out[1]
    assert "サラリーマン" not in out[1]
    # 完全鑑定の案内文
    assert "¥1,500" in out[1] or "完全鑑定" in out[1]


def test_judgment_with_name_passes_name_through(monkeypatch):
    captured = {}

    def fake(m, r, *, name=None, sex=None):
        captured["name"] = name
        captured["sex"] = sex
        return "## 3. 性格傾向\n本文"

    monkeypatch.setattr(main, "ANTHROPIC_ENABLED", True)
    monkeypatch.setattr(main, "FREEMIUM_MODE", False)
    monkeypatch.setattr(main, "generate_judgment", fake)
    out = _handle_text("1976/5/4 4 中井利幸 男")
    assert len(out) == 2
    assert captured["name"] == "中井利幸"
    assert captured["sex"] == "M"


def test_judgment_failure_falls_back_to_meishiki(monkeypatch):
    def boom(m, r, *, name=None, sex=None):
        raise RuntimeError("API down")

    monkeypatch.setattr(main, "ANTHROPIC_ENABLED", True)
    monkeypatch.setattr(main, "generate_judgment", boom)
    out = _handle_text("1985/5/20 10")
    assert len(out) == 1
    assert "年柱" in out[0]


def test_sex_unspecified_warning(monkeypatch):
    monkeypatch.setattr(main, "ANTHROPIC_ENABLED", True)
    monkeypatch.setattr(main, "FREEMIUM_MODE", False)
    monkeypatch.setattr(
        main, "generate_judgment", lambda m, r, *, name=None, sex=None: "鑑定本文"
    )
    out = _handle_text("1985/5/20 10")  # 性別なし
    assert len(out) == 2
    assert "性別未指定" in out[1]
