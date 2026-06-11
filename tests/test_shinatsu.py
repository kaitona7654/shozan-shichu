"""神殺（天乙貴人・将星・桃花・羊刃・紅艶）のテスト。

リファレンス:
- 竹本龍芳氏（象山流）による中井常雄氏鑑定書（1951/5/6男）
- 竹本泰祥氏鑑定書（中井宏美氏 1979/5/31女）
"""
from app.bazi import calc_meishiki
from app.shozan import koen, shosei, tenotsu_kijin, touka, yojin


def test_tsuneo_shosei():
    """中井常雄: 鑑定書に将星あり。丙日干の日支午→三合中神午、午あり"""
    m = calc_meishiki(1951, 5, 6)
    all_chishi = {p.chishi for p in m.pillars}
    assert shosei(m.day.chishi, all_chishi) is True


def test_tsuneo_touka():
    """中井常雄: 鑑定書に桃花あり。丙午日→咸池卯、年柱に卯あり"""
    m = calc_meishiki(1951, 5, 6)
    all_chishi = {p.chishi for p in m.pillars}
    assert touka(m.day.chishi, all_chishi) is True


def test_tsuneo_yojin():
    """中井常雄: 丙日干→劫財地支午、日柱午あり"""
    m = calc_meishiki(1951, 5, 6)
    all_chishi = {p.chishi for p in m.pillars}
    assert yojin(m.nikkan, all_chishi) is True


def test_hiromi_tenotsu():
    """中井宏美: 鑑定書に天乙貴人あり。戊日干→丑未、年柱に未あり"""
    m = calc_meishiki(1979, 5, 31, 12)
    all_chishi = {p.chishi for p in m.pillars}
    assert tenotsu_kijin(m.nikkan, all_chishi) is True


def test_hiromi_yojin():
    """中井宏美: 鑑定書に羊刃あり。戊日干→午、時柱戊午に午あり"""
    m = calc_meishiki(1979, 5, 31, 12)
    all_chishi = {p.chishi for p in m.pillars}
    assert yojin(m.nikkan, all_chishi) is True


def test_kaito_no_tenotsu():
    """中井利幸: 丙日干→酉亥、命式に酉亥なし"""
    m = calc_meishiki(1976, 5, 4, 4)
    all_chishi = {p.chishi for p in m.pillars}
    assert tenotsu_kijin(m.nikkan, all_chishi) is False


def test_kaito_koen():
    """中井利幸: 丙日干→紅艶寅、時柱庚寅に寅あり"""
    m = calc_meishiki(1976, 5, 4, 4)
    all_chishi = {p.chishi for p in m.pillars}
    assert koen(m.nikkan, all_chishi) is True


def test_tenotsu_table_covers_all_tengan():
    """天乙貴人テーブルが10日干をカバーするか（辛除く9日干、辛は別エントリ）"""
    from app.shozan import _TENOTSU
    expected_tengan = set("甲乙丙丁戊己庚辛壬癸")
    assert set(_TENOTSU.keys()) == expected_tengan
