"""四柱推命の命式計算モジュール。

sxtwl の暦計算（節気起算の年柱・月柱、真太陽時補正なしの時柱）を使い、
日干から見た通変星と地支蔵干を算出する。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import sxtwl

TENGAN = "甲乙丙丁戊己庚辛壬癸"
CHISHI = "子丑寅卯辰巳午未申酉戌亥"

TENGAN_GOGYO: dict[str, tuple[str, str]] = {
    "甲": ("木", "陽"), "乙": ("木", "陰"),
    "丙": ("火", "陽"), "丁": ("火", "陰"),
    "戊": ("土", "陽"), "己": ("土", "陰"),
    "庚": ("金", "陽"), "辛": ("金", "陰"),
    "壬": ("水", "陽"), "癸": ("水", "陰"),
}

CHISHI_ZOKAN: dict[str, list[str]] = {
    "子": ["癸"],
    "丑": ["己", "癸", "辛"],
    "寅": ["甲", "丙", "戊"],
    "卯": ["乙"],
    "辰": ["戊", "乙", "癸"],
    "巳": ["丙", "庚", "戊"],
    "午": ["丁", "己"],
    "未": ["己", "丁", "乙"],
    "申": ["庚", "壬", "戊"],
    "酉": ["辛"],
    "戌": ["戊", "辛", "丁"],
    "亥": ["壬", "甲"],
}

# 五行相生（左が右を生ずる）と相克（左が右を克す）
SEI = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
KOKU = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}


def tsuhensei(nikkan: str, target_tengan: str) -> str:
    """日干から見たtarget天干の通変星名を返す。"""
    n_go, n_yin = TENGAN_GOGYO[nikkan]
    t_go, t_yin = TENGAN_GOGYO[target_tengan]
    same_yin = n_yin == t_yin
    if n_go == t_go:
        return "比肩" if same_yin else "劫財"
    if SEI[n_go] == t_go:
        return "食神" if same_yin else "傷官"
    if KOKU[n_go] == t_go:
        return "偏財" if same_yin else "正財"
    if KOKU[t_go] == n_go:
        return "偏官" if same_yin else "正官"
    if SEI[t_go] == n_go:
        return "偏印" if same_yin else "正印"
    raise ValueError(f"不正な天干関係: {nikkan} → {target_tengan}")


@dataclass
class Pillar:
    name: str            # 年柱/月柱/日柱/時柱
    tengan: str          # 天干
    chishi: str          # 地支
    tengan_tsuhensei: Optional[str] = None  # 日柱は自分自身なのでNone
    zokan: List[str] = field(default_factory=list)
    zokan_tsuhensei: List[str] = field(default_factory=list)


@dataclass
class Meishiki:
    year: Pillar
    month: Pillar
    day: Pillar
    hour: Optional[Pillar]
    nikkan: str
    nikkan_gogyo: str
    nikkan_yinyang: str

    @property
    def pillars(self) -> List[Pillar]:
        return [p for p in (self.year, self.month, self.day, self.hour) if p is not None]


def _make_pillar(name: str, tg: str, dz: str, nikkan: Optional[str]) -> Pillar:
    zokan = CHISHI_ZOKAN[dz].copy()
    p = Pillar(name=name, tengan=tg, chishi=dz, zokan=zokan)
    if nikkan is not None:
        p.tengan_tsuhensei = tsuhensei(nikkan, tg) if tg != nikkan or name != "日柱" else None
        p.zokan_tsuhensei = [tsuhensei(nikkan, z) for z in zokan]
    return p


def calc_meishiki(
    year: int,
    month: int,
    day: int,
    hour: Optional[int] = None,
) -> Meishiki:
    """グレゴリオ暦の生年月日（時は0-23、省略可）から命式を計算。

    sxtwl の getYearGZ / getMonthGZ は節気起算（立春で年が変わる）。
    時は0-23の24時間制で渡す（深夜0時台は前日の子の刻ではなく当日扱い）。
    """
    d = sxtwl.fromSolar(year, month, day)
    y_gz, m_gz, dy_gz = d.getYearGZ(), d.getMonthGZ(), d.getDayGZ()

    y_tg, y_dz = TENGAN[y_gz.tg], CHISHI[y_gz.dz]
    m_tg, m_dz = TENGAN[m_gz.tg], CHISHI[m_gz.dz]
    d_tg, d_dz = TENGAN[dy_gz.tg], CHISHI[dy_gz.dz]
    nikkan = d_tg

    year_p = _make_pillar("年柱", y_tg, y_dz, nikkan)
    month_p = _make_pillar("月柱", m_tg, m_dz, nikkan)
    day_p = _make_pillar("日柱", d_tg, d_dz, nikkan)
    day_p.tengan_tsuhensei = None  # 日干は自分自身

    hour_p: Optional[Pillar] = None
    if hour is not None:
        if not 0 <= hour <= 23:
            raise ValueError("時は0〜23の範囲で指定")
        h_gz = d.getHourGZ(hour)
        h_tg, h_dz = TENGAN[h_gz.tg], CHISHI[h_gz.dz]
        hour_p = _make_pillar("時柱", h_tg, h_dz, nikkan)

    go, yin = TENGAN_GOGYO[nikkan]
    return Meishiki(
        year=year_p,
        month=month_p,
        day=day_p,
        hour=hour_p,
        nikkan=nikkan,
        nikkan_gogyo=go,
        nikkan_yinyang=yin,
    )
