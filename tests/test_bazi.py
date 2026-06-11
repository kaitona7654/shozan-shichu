"""bazi.py のスモークテスト。

検算は「四柱推命 鑑定」「高島暦」など公開鑑定サイトの値と突き合わせて確認。
ここでは代表的な3ケース（節気跨ぎ含む）で四柱の天干地支を固定する。
"""
from app.bazi import calc_meishiki, tsuhensei


def test_tsuhensei_basic():
    # 甲（陽木）から見た関係
    assert tsuhensei("甲", "甲") == "比肩"   # 同五行同陰陽
    assert tsuhensei("甲", "乙") == "劫財"   # 同五行異陰陽
    assert tsuhensei("甲", "丙") == "食神"   # 木生火・同陽
    assert tsuhensei("甲", "丁") == "傷官"   # 木生火・異陰陽
    assert tsuhensei("甲", "戊") == "偏財"   # 木克土・同陽
    assert tsuhensei("甲", "己") == "正財"
    assert tsuhensei("甲", "庚") == "偏官"   # 金克木・同陽（七殺）
    assert tsuhensei("甲", "辛") == "正官"
    assert tsuhensei("甲", "壬") == "偏印"   # 水生木・同陽
    assert tsuhensei("甲", "癸") == "正印"


def test_meishiki_1985_05_20_10():
    # 1985-05-20 10時生まれ（立夏=5/6を過ぎているので月柱は辛巳、日柱は万年暦で己未）
    m = calc_meishiki(1985, 5, 20, 10)
    assert m.year.tengan + m.year.chishi == "乙丑"
    assert m.month.tengan + m.month.chishi == "辛巳"
    assert m.day.tengan + m.day.chishi == "己未"
    assert m.hour is not None
    # 甲己日の巳刻は「己巳」（五子元遁の遁干法）
    assert m.hour.tengan + m.hour.chishi == "己巳"
    assert m.nikkan == "己"
    assert m.nikkan_gogyo == "土"


def test_meishiki_without_hour():
    m = calc_meishiki(2000, 1, 1)
    assert m.hour is None
    assert m.nikkan in "甲乙丙丁戊己庚辛壬癸"


def test_setsuiri_boundary_before_risshun():
    # 2024-02-03 は立春(2/4 17:27頃)の前 → 年柱は前年の癸卯
    m = calc_meishiki(2024, 2, 3, 12)
    assert m.year.tengan + m.year.chishi == "癸卯"


def test_setsuiri_boundary_after_risshun():
    # 2024-02-05 は立春後 → 年柱は甲辰
    m = calc_meishiki(2024, 2, 5, 12)
    assert m.year.tengan + m.year.chishi == "甲辰"


def test_zokan_present():
    m = calc_meishiki(1985, 5, 20, 10)
    # 巳の蔵干は丙・庚・戊
    assert m.month.zokan == ["丙", "庚", "戊"]
    # それぞれに通変星が振られている
    assert len(m.month.zokan_tsuhensei) == 3
