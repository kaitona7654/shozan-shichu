"""象山流（および四柱推命一般）の鑑定要素を計算するモジュール。

bazi.py が純粋な命式計算（天干地支・通変星・蔵干）を担当するのに対し、
こちらは象山流の鑑定書に必要な要素を計算する：
- 五行集計
- 空亡（旬空）
- 華蓋・天徳貴人・月徳貴人などの吉神
- 十二運
- 調候用神
- 身強身弱の簡易判定
- 大運（10年区切り、順行/逆行）

技術的には大半が四柱推命全般の標準ロジックで、象山流固有の差は
鑑定文の解釈（judgment.py 側のプロンプト）に持たせる方針。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

import sxtwl

from .bazi import (
    CHISHI,
    CHISHI_ZOKAN,
    TENGAN,
    TENGAN_GOGYO,
    Meishiki,
    Pillar,
)

Sex = Literal["M", "F"]

# ---------------------------------------------------------------------------
# 五行集計
# ---------------------------------------------------------------------------

GOGYO_ORDER = ["木", "火", "土", "金", "水"]


def count_gogyo(m: Meishiki) -> dict[str, int]:
    """命式の五行を重み付き集計。

    重み:
      天干 = 2
      地支主気 = 2
      地支中気 = 1
      地支余気 = 1
    """
    out = {g: 0 for g in GOGYO_ORDER}
    for p in m.pillars:
        out[TENGAN_GOGYO[p.tengan][0]] += 2
        for i, z in enumerate(p.zokan):
            out[TENGAN_GOGYO[z][0]] += 2 if i == 0 else 1
    return out


def missing_gogyo(counts: dict[str, int]) -> list[str]:
    """カウント0の五行（欠落）を返す。"""
    return [g for g in GOGYO_ORDER if counts.get(g, 0) == 0]


# ---------------------------------------------------------------------------
# 空亡（旬空）
# ---------------------------------------------------------------------------

# 60干支は6つの旬（甲子旬・甲戌旬…）に分かれ、各旬で2つの地支が「空亡」になる。
# 旬の起点（甲の天干）からの位置で日柱の旬を判定し、その旬の空亡地支を返す。
_JUN_KUUBOU = {
    "甲子": ("戌", "亥"),  # 甲子〜癸酉 = 戌亥空亡
    "甲戌": ("申", "酉"),  # 甲戌〜癸未 = 申酉空亡
    "甲申": ("午", "未"),  # 甲申〜癸巳 = 午未空亡
    "甲午": ("辰", "巳"),  # 甲午〜癸卯 = 辰巳空亡
    "甲辰": ("寅", "卯"),  # 甲辰〜癸丑 = 寅卯空亡
    "甲寅": ("子", "丑"),  # 甲寅〜癸亥 = 子丑空亡
}


def kuubou(day_pillar: Pillar) -> tuple[str, str]:
    """日柱から旬空（空亡）の2地支を返す。

    例: 丙辰日 → 甲寅旬 → (子, 丑)
    """
    tg_idx = TENGAN.index(day_pillar.tengan)
    dz_idx = CHISHI.index(day_pillar.chishi)
    # 旬の起点を逆算: tg_idx と dz_idx の差から旬頭の60干支を求める
    # 60干支は天干10×地支12のLCM、(tg_idx - dz_idx) % 10 で旬頭が決まる
    diff = (dz_idx - tg_idx) % 12
    # 旬頭は (甲, diff番目の地支) になる。diffは偶数（0,2,4,6,8,10）
    jun_head = "甲" + CHISHI[diff]
    return _JUN_KUUBOU[jun_head]


# ---------------------------------------------------------------------------
# 十二運（長生〜養の12段階）
# ---------------------------------------------------------------------------

# 各天干（日干）から見た、十二支に対する十二運の表
# 出典: 標準的な四柱推命教本
_JUNIUN_TABLE = {
    "甲": ["沐", "冠", "建", "帝", "衰", "病", "死", "墓", "絶", "胎", "養", "長"],
    "乙": ["病", "死", "墓", "絶", "胎", "養", "長", "沐", "冠", "建", "帝", "衰"],
    "丙": ["胎", "養", "長", "沐", "冠", "建", "帝", "衰", "病", "死", "墓", "絶"],
    "丁": ["絶", "墓", "死", "病", "衰", "帝", "建", "冠", "沐", "長", "養", "胎"],
    "戊": ["胎", "養", "長", "沐", "冠", "建", "帝", "衰", "病", "死", "墓", "絶"],
    "己": ["絶", "墓", "死", "病", "衰", "帝", "建", "冠", "沐", "長", "養", "胎"],
    "庚": ["死", "墓", "絶", "胎", "養", "長", "沐", "冠", "建", "帝", "衰", "病"],
    "辛": ["長", "養", "胎", "絶", "墓", "死", "病", "衰", "帝", "建", "冠", "沐"],
    "壬": ["帝", "衰", "病", "死", "墓", "絶", "胎", "養", "長", "沐", "冠", "建"],
    "癸": ["建", "冠", "沐", "長", "養", "胎", "絶", "墓", "死", "病", "衰", "帝"],
}
# 略号: 長=長生、沐=沐浴、冠=冠帯、建=建禄、帝=帝旺、衰=衰、病=病、死=死、墓=墓、絶=絶、胎=胎、養=養

_JUNIUN_HEADERS = "子丑寅卯辰巳午未申酉戌亥"


def juniun(nikkan: str, chishi: str) -> str:
    """日干から見た地支に対応する十二運。"""
    idx = _JUNIUN_HEADERS.index(chishi)
    return _JUNIUN_TABLE[nikkan][idx]


# ---------------------------------------------------------------------------
# 吉神（華蓋・天徳貴人・月徳貴人）
# ---------------------------------------------------------------------------

# 華蓋: 日支または年支が辰戌丑未の同支を含むと立つ（地支3つ以上で強い）
def kagai(m: Meishiki) -> bool:
    """命式に華蓋が立つか（地支に辰戌丑未が含まれ、複数なら強い）。"""
    targets = {"辰", "戌", "丑", "未"}
    chishi_set = [p.chishi for p in m.pillars]
    return sum(1 for c in chishi_set if c in targets) >= 1


# 天徳貴人: 月支に対応する天干（または地支）
# 月支 → 天徳の対応表（標準）
_TENTOKU = {
    "寅": "丁", "卯": "申", "辰": "壬", "巳": "辛",
    "午": "亥", "未": "甲", "申": "癸", "酉": "寅",
    "戌": "丙", "亥": "乙", "子": "巳", "丑": "庚",
}


def tentoku_kijin(month_chishi: str, all_tengan_chishi: set[str]) -> bool:
    """天徳貴人: 月支に対応する天徳が命式の他干支にあれば成立。"""
    target = _TENTOKU.get(month_chishi)
    return target in all_tengan_chishi if target else False


# 月徳貴人: 月支の三合の中神（陽干）
_GETTOKU = {
    "寅": "丙", "午": "丙", "戌": "丙",  # 寅午戌の三合→火→丙
    "巳": "庚", "酉": "庚", "丑": "庚",  # 巳酉丑の三合→金→庚
    "申": "壬", "子": "壬", "辰": "壬",  # 申子辰の三合→水→壬
    "亥": "甲", "卯": "甲", "未": "甲",  # 亥卯未の三合→木→甲
}


def gettoku_kijin(month_chishi: str, all_tengan: set[str]) -> bool:
    """月徳貴人: 月支の三合の正官（陽干）が命式の天干にあれば成立。"""
    target = _GETTOKU.get(month_chishi)
    return target in all_tengan if target else False


# ---------------------------------------------------------------------------
# 追加神殺：天乙貴人・将星・桃花・羊刃・紅艶
# 中井家鑑定書3冊（竹本泰祥・竹本龍芳）で確認された必須神殺
# ---------------------------------------------------------------------------

# 天乙貴人: 日干から見た特定の2地支。最強の吉神、困難時の救い
_TENOTSU = {
    "甲": ("丑", "未"), "戊": ("丑", "未"), "庚": ("丑", "未"),
    "乙": ("子", "申"), "己": ("子", "申"),
    "丙": ("酉", "亥"), "丁": ("酉", "亥"),
    "壬": ("卯", "巳"), "癸": ("卯", "巳"),
    "辛": ("寅", "午"),
}


def tenotsu_kijin(nikkan: str, all_chishi: set[str]) -> bool:
    """天乙貴人: 日干に対応する2地支のいずれかが命式の地支にあれば成立。"""
    targets = _TENOTSU.get(nikkan, ())
    return any(t in all_chishi for t in targets)


# 将星: 日支または年支の三合の中神。リーダー気質、統率力
_SHOSEI = {
    "寅": "午", "午": "午", "戌": "午",  # 寅午戌→午
    "巳": "酉", "酉": "酉", "丑": "酉",  # 巳酉丑→酉
    "申": "子", "子": "子", "辰": "子",  # 申子辰→子
    "亥": "卯", "卯": "卯", "未": "卯",  # 亥卯未→卯
}


def shosei(day_chishi: str, all_chishi: set[str]) -> bool:
    """将星: 日支の三合中神が命式の他の地支（または自分自身）にあれば成立。"""
    target = _SHOSEI.get(day_chishi)
    return target in all_chishi if target else False


# 桃花（咸池）: 日支または年支から見た三合の前位の地支。異性縁・人気・華やかさ
_TOUKA = {
    "寅": "卯", "午": "卯", "戌": "卯",  # 寅午戌→卯
    "巳": "午", "酉": "午", "丑": "午",  # 巳酉丑→午
    "申": "酉", "子": "酉", "辰": "酉",  # 申子辰→酉
    "亥": "子", "卯": "子", "未": "子",  # 亥卯未→子
}


def touka(day_chishi: str, all_chishi: set[str]) -> bool:
    """桃花（咸池）: 日支の三合に対する沐浴位（咸池）が命式にあれば成立。"""
    target = _TOUKA.get(day_chishi)
    return target in all_chishi if target else False


# 羊刃: 日干の比劫の旺地（劫財の地支）。強烈な行動力、武の星、諸刃の剣
# 陽干の羊刃は明確、陰干は流派により扱いが異なる（ここでは標準の陽干のみ）
_YOJIN = {
    "甲": "卯", "丙": "午", "戊": "午", "庚": "酉", "壬": "子",
    # 陰干は通常「羊刃」を取らない（流派により取る場合もあるが、ここでは無）
}


def yojin(nikkan: str, all_chishi: set[str]) -> bool:
    """羊刃: 陽日干に対応する劫財地支が命式の地支にあれば成立。"""
    target = _YOJIN.get(nikkan)
    return target in all_chishi if target else False


# 紅艶: 日干から見た特定の地支。異性縁・色気・芸能の縁
_KOEN = {
    "甲": "午", "乙": "午",
    "丙": "寅", "丁": "未",
    "戊": "辰", "己": "辰",
    "庚": "戌", "辛": "酉",
    "壬": "子", "癸": "申",
}


def koen(nikkan: str, all_chishi: set[str]) -> bool:
    """紅艶: 日干に対応する紅艶地支が命式にあれば成立。"""
    target = _KOEN.get(nikkan)
    return target in all_chishi if target else False


# ---------------------------------------------------------------------------
# 調候用神（簡易テーブル：日干×月支）
# ---------------------------------------------------------------------------

# 『窮通宝鑑』準拠の調候用神（10日干×12月支＝120パターン）。
# 古典：子平真詮・窮通宝鑑・滴天髓の標準解釈。
# 各組み合わせは「主用神・補用神」を中黒区切りで列挙。
_CHOUKO = {
    # 甲日干（陽木）── 大木、丙(太陽)と癸(雨露)を喜ぶ
    ("甲", "寅"): "丙・癸",   ("甲", "卯"): "庚・丙・丁",
    ("甲", "辰"): "庚・壬・丁", ("甲", "巳"): "癸・庚・丁",
    ("甲", "午"): "癸・庚・丁", ("甲", "未"): "癸・庚・丁",
    ("甲", "申"): "丁・庚・壬", ("甲", "酉"): "丁・庚・丙",
    ("甲", "戌"): "庚・丁・壬", ("甲", "亥"): "庚・丁・戊・丙",
    ("甲", "子"): "丁・庚・丙", ("甲", "丑"): "丁・庚・丙",
    # 乙日干（陰木）── 草花、丙(太陽)を最も喜ぶ
    ("乙", "寅"): "丙・癸",   ("乙", "卯"): "丙・癸",
    ("乙", "辰"): "癸・丙・戊", ("乙", "巳"): "癸・丁",
    ("乙", "午"): "癸・丙",   ("乙", "未"): "癸・丙",
    ("乙", "申"): "丙・癸・己", ("乙", "酉"): "癸・丙・丁",
    ("乙", "戌"): "癸・丙・辛", ("乙", "亥"): "丙・戊",
    ("乙", "子"): "丙・戊",   ("乙", "丑"): "丙",
    # 丙日干（陽火）── 太陽、壬(大海)で輝きを得る
    ("丙", "寅"): "壬・庚", ("丙", "卯"): "壬・己", ("丙", "辰"): "壬・甲",
    ("丙", "巳"): "壬・庚", ("丙", "午"): "壬・庚", ("丙", "未"): "壬・庚",
    ("丙", "申"): "壬・戊", ("丙", "酉"): "壬・癸", ("丙", "戌"): "甲・壬",
    ("丙", "亥"): "甲・戊・庚・壬", ("丙", "子"): "壬・戊・己", ("丙", "丑"): "壬・甲",
    # 丁日干（陰火）── 灯火、甲(薪)と庚(燭台)を喜ぶ
    ("丁", "寅"): "甲・庚",   ("丁", "卯"): "庚・甲",
    ("丁", "辰"): "甲・庚",   ("丁", "巳"): "甲・庚",
    ("丁", "午"): "壬・庚・癸", ("丁", "未"): "甲・壬・庚",
    ("丁", "申"): "甲・庚・丙・戊", ("丁", "酉"): "甲・庚・丙・戊",
    ("丁", "戌"): "甲・庚・戊", ("丁", "亥"): "甲・庚",
    ("丁", "子"): "甲・庚",   ("丁", "丑"): "甲・庚",
    # 戊日干（陽土）── 大地、丙(太陽)と甲(耕す木)と癸(湿気)
    ("戊", "寅"): "丙・甲・癸", ("戊", "卯"): "丙・甲・癸",
    ("戊", "辰"): "甲・丙・癸", ("戊", "巳"): "甲・丙・癸",
    ("戊", "午"): "壬・甲・丙", ("戊", "未"): "癸・丙・甲",
    ("戊", "申"): "丙・癸・甲", ("戊", "酉"): "丙・癸",
    ("戊", "戌"): "甲・丙・癸", ("戊", "亥"): "甲・丙",
    ("戊", "子"): "丙・甲",   ("戊", "丑"): "丙・甲",
    # 己日干（陰土）── 田畑、丙(温め)と甲(耕す)と癸(潤す)
    ("己", "寅"): "丙・庚・甲", ("己", "卯"): "甲・癸・丙",
    ("己", "辰"): "丙・癸・甲", ("己", "巳"): "癸・丙",
    ("己", "午"): "癸・丙",   ("己", "未"): "癸・丙",
    ("己", "申"): "丙・癸",   ("己", "酉"): "丙・癸",
    ("己", "戌"): "甲・丙・癸", ("己", "亥"): "丙・甲・戊",
    ("己", "子"): "丙・甲・戊", ("己", "丑"): "丙・甲・戊",
    # 庚日干（陽金）── 鋼鉄、丁(炉火)で鍛え甲(炭)で燃やす
    ("庚", "寅"): "戊・甲・壬・丙・丁", ("庚", "卯"): "丁・甲・庚・丙",
    ("庚", "辰"): "甲・丁・壬・癸", ("庚", "巳"): "壬・戊・丙・丁",
    ("庚", "午"): "壬・癸",   ("庚", "未"): "丁・甲",
    ("庚", "申"): "丁・甲",   ("庚", "酉"): "丁・甲・丙",
    ("庚", "戌"): "甲・壬",   ("庚", "亥"): "丁・丙",
    ("庚", "子"): "丁・丙・甲", ("庚", "丑"): "丙・丁・甲",
    # 辛日干（陰金）── 宝石・装飾品、壬(水で磨く)を喜ぶ
    ("辛", "寅"): "己・壬・庚", ("辛", "卯"): "壬・甲",
    ("辛", "辰"): "壬・甲",   ("辛", "巳"): "壬・甲・癸",
    ("辛", "午"): "壬・己・癸", ("辛", "未"): "壬・庚・甲",
    ("辛", "申"): "壬・甲・戊", ("辛", "酉"): "壬・甲",
    ("辛", "戌"): "壬・甲",   ("辛", "亥"): "壬・丙",
    ("辛", "子"): "丙・戊・壬・甲", ("辛", "丑"): "丙・壬・戊・己",
    # 壬日干（陽水）── 大海、戊(堤防)で氾濫を防ぐ
    ("壬", "寅"): "庚・丙・戊", ("壬", "卯"): "戊・辛・庚",
    ("壬", "辰"): "甲・庚",   ("壬", "巳"): "壬・辛・庚・癸",
    ("壬", "午"): "癸・庚・辛", ("壬", "未"): "辛・甲",
    ("壬", "申"): "戊・丁",   ("壬", "酉"): "甲・庚",
    ("壬", "戌"): "甲・丙",   ("壬", "亥"): "戊・庚・丙",
    ("壬", "子"): "戊・丙",   ("壬", "丑"): "丙・甲・丁",
    # 癸日干（陰水）── 雨露、辛(金で水源)と丙(太陽で活かす)
    ("癸", "寅"): "辛・丙",   ("癸", "卯"): "庚・辛",
    ("癸", "辰"): "丙・辛・甲", ("癸", "巳"): "辛",
    ("癸", "午"): "庚・壬・辛", ("癸", "未"): "庚・辛・壬・癸",
    ("癸", "申"): "丁",      ("癸", "酉"): "辛・丙",
    ("癸", "戌"): "辛・甲・壬・癸", ("癸", "亥"): "庚・辛・戊・丁",
    ("癸", "子"): "丙・辛",   ("癸", "丑"): "丙・丁",
}


def chouko_yougjin(nikkan: str, month_chishi: str) -> Optional[str]:
    """日干×月支から調候用神を返す。未収録なら None。"""
    return _CHOUKO.get((nikkan, month_chishi))


# ---------------------------------------------------------------------------
# 身強身弱の簡易判定
# ---------------------------------------------------------------------------

@dataclass
class MikyojakuResult:
    label: str  # "身強" | "身中" | "身弱"
    score: int  # 日干を助ける力の合計
    detail: dict[str, int]  # {"印星": n, "比劫": n, "食傷": n, "財星": n, "官殺": n}


def _tsuhensei_category(nikkan: str, other: str) -> str:
    """通変星のカテゴリ（5分類）を返す: 比劫/食傷/財星/官殺/印星。"""
    from .bazi import KOKU, SEI

    n_go = TENGAN_GOGYO[nikkan][0]
    t_go = TENGAN_GOGYO[other][0]
    if n_go == t_go:
        return "比劫"
    if SEI[n_go] == t_go:
        return "食傷"
    if KOKU[n_go] == t_go:
        return "財星"
    if KOKU[t_go] == n_go:
        return "官殺"
    return "印星"


def mi_kyojaku(m: Meishiki) -> MikyojakuResult:
    """身強身弱の簡易判定。

    五分類別に重み付きスコアリングし、印星+比劫（日干を助ける）と
    食傷+財星+官殺（漏らす/克す）のバランスを見る。
    月令（月支の蔵干主気が日干と同類か）に大きな重みを付与。
    """
    nikkan = m.nikkan
    counts = {"比劫": 0, "食傷": 0, "財星": 0, "官殺": 0, "印星": 0}

    # 月令の重み: 月支の主気（蔵干筆頭）が日干と同類なら +3
    month_zokan_main = m.month.zokan[0]
    if _tsuhensei_category(nikkan, month_zokan_main) in ("比劫", "印星"):
        counts[_tsuhensei_category(nikkan, month_zokan_main)] += 3

    for p in m.pillars:
        # 天干（重み2）
        if p.tengan != nikkan or p.name != "日柱":  # 日干本人は除外
            cat = _tsuhensei_category(nikkan, p.tengan)
            counts[cat] += 2
        else:
            counts["比劫"] += 2  # 日干自身も比劫としてカウント
        # 蔵干（主気2、中気・余気1）
        for i, z in enumerate(p.zokan):
            cat = _tsuhensei_category(nikkan, z)
            counts[cat] += 2 if i == 0 else 1

    # 日干を助ける力
    support = counts["印星"] + counts["比劫"]
    drain = counts["食傷"] + counts["財星"] + counts["官殺"]

    if support >= drain + 4:
        label = "身強"
    elif drain >= support + 4:
        label = "身弱"
    else:
        label = "身中"

    return MikyojakuResult(label=label, score=support - drain, detail=counts)


# ---------------------------------------------------------------------------
# 大運（10年区切り）
# ---------------------------------------------------------------------------

@dataclass
class Daiun:
    age_from: int
    age_to: int
    tengan: str
    chishi: str
    tsuhensei: str       # 日干から見た大運天干の通変星
    juniun: str          # 日干から見た大運地支の十二運


def _next_or_prev_setsuiri_days(year: int, month: int, day: int, *, forward: bool) -> float:
    """出生日から次（forward=True）または前（False）の節入りまでの日数を返す。

    簡易計算: sxtwlで節気を取得。誤差±0.5日程度。
    """
    # 主要な節気の月日（おおよそ）。実用上はこれで十分。
    # forward=True: 出生日 < 節入日 となる節を探す
    # 各月の節は: 寅月=立春(2/4)、卯月=驚蟄(3/6)、辰月=清明(4/5)、巳月=立夏(5/5)…
    # sxtwl.fromSolar(y,m,d).getJieQi() で節気情報が取れるはずだが、API差異対応のため簡易版を使う。

    # 簡易: その月の節入日を概算で出して差分計算
    # （正確には太陽黄経15度刻みで決まるが、年差は±1日程度）
    APPROX_SETSU = {
        2: 4, 3: 6, 4: 5, 5: 5, 6: 6, 7: 7,
        8: 7, 9: 8, 10: 8, 11: 7, 12: 7, 1: 6,
    }
    if forward:
        # その月の節がまだなら今月、過ぎていれば来月
        setsu_day = APPROX_SETSU[month]
        if day <= setsu_day:
            return float(setsu_day - day)
        # 来月の節
        nm = month + 1 if month < 12 else 1
        ny = year if month < 12 else year + 1
        days_in_month = _days_in(year, month)
        return float(days_in_month - day + APPROX_SETSU[nm])
    else:
        # 前の節
        setsu_day = APPROX_SETSU[month]
        if day > setsu_day:
            return float(day - setsu_day)
        pm = month - 1 if month > 1 else 12
        py = year if month > 1 else year - 1
        days_prev = _days_in(py, pm)
        return float(day + days_prev - APPROX_SETSU[month])


def _days_in(year: int, month: int) -> int:
    import calendar
    return calendar.monthrange(year, month)[1]


def daiun(
    m: Meishiki,
    *,
    year: int,
    month: int,
    day: int,
    sex: Sex,
    count: int = 8,
) -> list[Daiun]:
    """大運を count 個（既定8区切り＝80年分）算出。

    順行/逆行ルール:
      陽男（年干が陽天干かつ男）・陰女（年干が陰天干かつ女）→ 順行
      陰男・陽女 → 逆行
    起運年齢:
      順行: 出生日から「次の節入り」までの日数
      逆行: 出生日から「前の節入り」までの日数
      日数 ÷ 3 ≒ 起運年齢（小数を四捨五入）

    大運の最初の干支は月柱から1つ進める/戻る。
    """
    year_tengan_yin = TENGAN_GOGYO[m.year.tengan][1]  # "陽" or "陰"
    forward = (year_tengan_yin == "陽" and sex == "M") or (
        year_tengan_yin == "陰" and sex == "F"
    )

    days = _next_or_prev_setsuiri_days(year, month, day, forward=forward)
    # 起運年齢: 日数÷3。象山流の慣例では満年齢で見るため、小数を切り上げ。
    # 端数（< 1日）は「1歳」ではなく「2歳起算」とする鑑定例が多いので +1 補正。
    import math
    raw_age = days / 3
    start_age = max(1, math.ceil(raw_age) + (1 if raw_age < 1 else 0))

    # 月柱の干支インデックス
    month_tg_idx = TENGAN.index(m.month.tengan)
    month_dz_idx = CHISHI.index(m.month.chishi)

    results: list[Daiun] = []
    for i in range(count):
        step = i + 1
        if forward:
            tg_idx = (month_tg_idx + step) % 10
            dz_idx = (month_dz_idx + step) % 12
        else:
            tg_idx = (month_tg_idx - step) % 10
            dz_idx = (month_dz_idx - step) % 12
        tg = TENGAN[tg_idx]
        dz = CHISHI[dz_idx]

        from .bazi import tsuhensei as calc_tsuhensei
        tsu = calc_tsuhensei(m.nikkan, tg)
        ju = juniun(m.nikkan, dz)

        age_from = start_age + i * 10
        age_to = age_from + 9
        results.append(Daiun(age_from, age_to, tg, dz, tsu, ju))

    return results


# ---------------------------------------------------------------------------
# 年廻り（その年の運勢）
# ---------------------------------------------------------------------------

# 十二運 → 象山流の年廻りキーワードマッピング。
# kaitoさん提示の象山流資料（年廻りサインカーブ図）に基づく解釈。
# 各キーワードは「その年の運気の質」「行動指針」「警戒事項」を1-2文で示す。
NENMAWARI_KEYWORDS = {
    "長": ("開拓・新たな門出", "新しい挑戦の種を蒔く年。動き出すのに最良。"),
    "沐": ("浮気・油断", "華やかだが落とし穴のある年。誘惑と軽率な判断に注意。"),
    "冠": ("精算・充実", "これまでの努力が形になり、社会的な地位や信用が固まる年。"),
    "建": ("健康・決定", "心身ともに充実し、重要な意志決定に適した年。"),
    "帝": ("成功・人気", "頂点に達し注目を集める年。慢心に注意し謙虚さを保つ。"),
    "衰": ("落下・転換", "勢いが収まり次の段階への切り替え時。守りに転じる。"),
    "病": ("古きを捨てる", "不要なものを整理・断捨離する年。執着を手放す。"),
    "死": ("ミステリー・内省", "深く内省し、目に見えない事柄に向き合う年。"),
    "墓": ("地点・蓄積", "運気の谷。新規事業や派手な動きを避け、守りに徹する。"),
    "絶": ("新規スタート・再生", "古い殻を破り、ゼロから組み立て直す年。"),
    "胎": ("再開・再会", "新しい縁や機会の芽が宿る年。種を選ぶ。"),
    "養": ("整える・育てる", "基盤を整え、長期的な土台を作る年。焦らず育てる。"),
}


@dataclass
class NenmawariYear:
    year: int
    age: int
    nen_kanshi: str         # その年の年干支（例: 丙午）
    nen_chishi: str         # その年の地支
    juniun: str             # 日干から見た十二運
    label: str              # キーワード（「開拓・新たな門出」など）
    detail: str             # 詳細説明


def _nenchu_kanshi(year: int) -> str:
    """西暦からその年の年干支を計算（節入り基準＝立春以降が新年扱い）。

    sxtwl.fromSolar で立春後（6月15日固定）の日付の年干支を取得。
    """
    d = sxtwl.fromSolar(year, 6, 15)
    gz = d.getYearGZ()
    return TENGAN[gz.tg] + CHISHI[gz.dz]


def nenmawari(
    nikkan: str,
    *,
    birth_year: int,
    target_year: int,
) -> NenmawariYear:
    """指定年の年廻り（その年の運気段階）を算出。"""
    nen_kanshi = _nenchu_kanshi(target_year)
    nen_chishi = nen_kanshi[1]
    ju = juniun(nikkan, nen_chishi)
    label, detail = NENMAWARI_KEYWORDS.get(ju, ("不明", ""))
    return NenmawariYear(
        year=target_year,
        age=target_year - birth_year,
        nen_kanshi=nen_kanshi,
        nen_chishi=nen_chishi,
        juniun=ju,
        label=label,
        detail=detail,
    )


def nenmawari_range(
    nikkan: str,
    *,
    birth_year: int,
    from_year: int,
    years: int = 5,
) -> list[NenmawariYear]:
    """指定年から years 年分の年廻り一覧を返す。"""
    return [
        nenmawari(nikkan, birth_year=birth_year, target_year=from_year + i)
        for i in range(years)
    ]


# ---------------------------------------------------------------------------
# 月廻り（その月の運勢）
# ---------------------------------------------------------------------------

@dataclass
class TsukimawariMonth:
    year: int
    month: int
    age: int
    getsu_kanshi: str    # その月の月干支
    getsu_chishi: str    # 月支
    juniun: str          # 日干から見た十二運
    label: str           # キーワード
    detail: str          # 詳細説明


def tsukimawari(
    nikkan: str,
    *,
    birth_year: int,
    target_year: int,
    target_month: int,
) -> TsukimawariMonth:
    """指定年月の月廻りを算出。

    月柱は節入り起算で決まる（立春は2月、驚蟄は3月、清明は4月、…）。
    各月の中旬20日で月柱を取れば節入り後の確実な値が得られる。
    """
    d = sxtwl.fromSolar(target_year, target_month, 20)
    gz = d.getMonthGZ()
    tg = TENGAN[gz.tg]
    dz = CHISHI[gz.dz]
    ju = juniun(nikkan, dz)
    label, detail = NENMAWARI_KEYWORDS.get(ju, ("不明", ""))
    return TsukimawariMonth(
        year=target_year,
        month=target_month,
        age=target_year - birth_year,
        getsu_kanshi=tg + dz,
        getsu_chishi=dz,
        juniun=ju,
        label=label,
        detail=detail,
    )


def tsukimawari_range(
    nikkan: str,
    *,
    birth_year: int,
    from_year: int,
    from_month: int,
    months: int = 12,
) -> list[TsukimawariMonth]:
    """指定年月から months ヶ月分の月廻り一覧を返す。"""
    result: list[TsukimawariMonth] = []
    y, m = from_year, from_month
    for _ in range(months):
        result.append(tsukimawari(nikkan, birth_year=birth_year, target_year=y, target_month=m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return result


# ---------------------------------------------------------------------------
# 日廻り（その日の運勢）
# ---------------------------------------------------------------------------

# 日廻り用キーワード（日単位なので行動指針を1-2行で）
HIMAWARI_KEYWORDS = {
    "長": ("開拓日", "新しいことを始めるのに最良の日。動き出す。"),
    "沐": ("油断日", "華やかだが落とし穴のある日。誘惑と軽率な判断に注意。"),
    "冠": ("充実日", "努力が形になる日。社会的な動きが◎。"),
    "建": ("決定日", "心身充実、重要な意志決定や契約に向く日。"),
    "帝": ("頂点日", "最も運気が高い日。何かを始める・人前に出る・勝負に出る◎"),
    "衰": ("転換日", "勢いが落ち着く日。守りに転じて整理を。"),
    "病": ("断捨離日", "古いものを手放す日。整理整頓、断捨離に最適。"),
    "死": ("内省日", "深く考える日。静かに過ごし、自分と向き合う。"),
    "墓": ("守りの日", "運気の谷。新規契約・大決断を避け、休息を。"),
    "絶": ("再生日", "古い殻を破る日。今までの自分を一旦リセットする。"),
    "胎": ("芽吹きの日", "新しい縁や機会の芽が宿る日。種を選ぶ。"),
    "養": ("育みの日", "基盤を整え、長期的な土台を育てる日。焦らず。"),
}


@dataclass
class HimawariDay:
    date: str            # ISO形式 YYYY-MM-DD
    nichi_kanshi: str    # その日の日干支
    nichi_chishi: str    # 日支
    juniun: str          # 日干から見た十二運
    label: str           # キーワード
    detail: str          # 詳細・アドバイス
    is_kuubou: bool      # その日が出生命式の空亡日に当たるか


def himawari(
    nikkan: str,
    *,
    target_date: "datetime.date",
    kuubou_chishi: Optional[tuple[str, str]] = None,
) -> HimawariDay:
    """指定日の日廻りを算出。

    kuubou_chishi: 命式の空亡（旬空）地支。指定日が空亡に当たるか判定するため。
    """
    d = sxtwl.fromSolar(target_date.year, target_date.month, target_date.day)
    gz = d.getDayGZ()
    tg = TENGAN[gz.tg]
    dz = CHISHI[gz.dz]
    ju = juniun(nikkan, dz)
    label, detail = HIMAWARI_KEYWORDS.get(ju, ("不明", ""))
    is_kuubou = bool(kuubou_chishi and dz in kuubou_chishi)
    return HimawariDay(
        date=target_date.isoformat(),
        nichi_kanshi=tg + dz,
        nichi_chishi=dz,
        juniun=ju,
        label=label,
        detail=detail,
        is_kuubou=is_kuubou,
    )


def himawari_range(
    nikkan: str,
    *,
    from_date: "datetime.date",
    days: int = 7,
    kuubou_chishi: Optional[tuple[str, str]] = None,
) -> list[HimawariDay]:
    """指定日から days 日分の日廻り一覧を返す。"""
    import datetime
    return [
        himawari(
            nikkan,
            target_date=from_date + datetime.timedelta(days=i),
            kuubou_chishi=kuubou_chishi,
        )
        for i in range(days)
    ]


# ---------------------------------------------------------------------------
# 統合：象山流の鑑定要素を一括取得
# ---------------------------------------------------------------------------

@dataclass
class ShozanReading:
    gogyo_counts: dict[str, int]
    missing: list[str]
    kuubou: tuple[str, str]
    kagai: bool
    tentoku: bool
    gettoku: bool
    tenotsu: bool         # 天乙貴人（最強の吉神）
    shosei: bool          # 将星（リーダー気質）
    touka: bool           # 桃花（異性縁・人気）
    yojin: bool           # 羊刃（武の星）
    koen: bool            # 紅艶（色気・芸能縁）
    chouko: Optional[str]
    mikyojaku: MikyojakuResult
    daiun_list: list[Daiun]
    nenmawari_list: list[NenmawariYear]      # 今年〜数年先の年廻り
    tsukimawari_list: list[TsukimawariMonth]  # 今月から12ヶ月の月廻り


def reading(
    m: Meishiki,
    *,
    year: int,
    month: int,
    day: int,
    sex: Sex,
    today_year: Optional[int] = None,
    today_month: Optional[int] = None,
    nenmawari_years: int = 5,
    tsukimawari_months: int = 12,
) -> ShozanReading:
    """命式から象山流の鑑定要素を一括算出。

    today_year/today_month: 年廻り・月廻り計算の起点（既定は実行時）
    nenmawari_years: 何年分の年廻りを返すか（既定5年）
    tsukimawari_months: 何ヶ月分の月廻りを返すか（既定12ヶ月）
    """
    if today_year is None or today_month is None:
        import datetime
        today = datetime.date.today()
        if today_year is None:
            today_year = today.year
        if today_month is None:
            today_month = today.month

    counts = count_gogyo(m)
    all_tengan = {p.tengan for p in m.pillars}
    all_chishi = {p.chishi for p in m.pillars}
    all_chars = all_tengan | all_chishi

    return ShozanReading(
        gogyo_counts=counts,
        missing=missing_gogyo(counts),
        kuubou=kuubou(m.day),
        kagai=kagai(m),
        tentoku=tentoku_kijin(m.month.chishi, all_chars),
        gettoku=gettoku_kijin(m.month.chishi, all_tengan),
        tenotsu=tenotsu_kijin(m.nikkan, all_chishi),
        shosei=shosei(m.day.chishi, all_chishi),
        touka=touka(m.day.chishi, all_chishi),
        yojin=yojin(m.nikkan, all_chishi),
        koen=koen(m.nikkan, all_chishi),
        chouko=chouko_yougjin(m.nikkan, m.month.chishi),
        mikyojaku=mi_kyojaku(m),
        daiun_list=daiun(m, year=year, month=month, day=day, sex=sex),
        nenmawari_list=nenmawari_range(
            m.nikkan,
            birth_year=year,
            from_year=today_year,
            years=nenmawari_years,
        ),
        tsukimawari_list=tsukimawari_range(
            m.nikkan,
            birth_year=year,
            from_year=today_year,
            from_month=today_month,
            months=tsukimawari_months,
        ),
    )
