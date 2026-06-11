"""命式をLINE返信用のテキストに整形する。"""
from __future__ import annotations

from .bazi import Meishiki, Pillar


def _pillar_line(p: Pillar) -> str:
    tg_t = p.tengan_tsuhensei or "—"
    zokan_str = "・".join(f"{z}({t})" for z, t in zip(p.zokan, p.zokan_tsuhensei)) if p.zokan_tsuhensei else "・".join(p.zokan)
    return f"【{p.name}】{p.tengan}{p.chishi}　天干:{tg_t}　蔵干:{zokan_str}"


def format_meishiki_text(m: Meishiki) -> str:
    lines = [
        f"◆ 命式（四柱）",
        f"日干: {m.nikkan}（{m.nikkan_gogyo}・{m.nikkan_yinyang}）",
        "",
    ]
    for p in m.pillars:
        lines.append(_pillar_line(p))
    lines.append("")
    lines.append("※ 結果は娯楽目的です。重要な判断の根拠にはなさらないでください。")
    return "\n".join(lines)


HELP_TEXT = (
    "🔮 象山流四柱推命Bot へようこそ\n\n"
    "生年月日（時刻・名前・性別もあれば）を送ってください。\n"
    "例:\n"
    "・1976/5/4 4 中井利幸 男\n"
    "・1985-05-20 10:30 女\n"
    "・1985年5月20日\n\n"
    "・時刻不明 → 省略可（時柱なしで鑑定）\n"
    "・名前あり → 起名学（漢字五行）評価が追加\n"
    "・性別あり → 大運（10年運勢）が正確に算出\n\n"
    "※ 西暦（新暦）でお願いします。旧暦は不可。"
)
