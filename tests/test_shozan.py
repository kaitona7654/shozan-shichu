"""shozan モジュールのテスト。

リファレンス: 竹本泰祥氏（象山流）による中井利幸氏の鑑定書
（1976年5月4日 寅刻、男性、丙辰／壬辰／丙辰／庚寅、身弱）
"""
from app.bazi import calc_meishiki
from app.shozan import (
    count_gogyo,
    daiun,
    gettoku_kijin,
    juniun,
    kagai,
    kuubou,
    mi_kyojaku,
    nenmawari,
    nenmawari_range,
    reading,
    tentoku_kijin,
    chouko_yougjin,
)


def _kaito():
    """kaitoさん（中井利幸氏）の命式: 1976/5/4 寅刻、男性。"""
    return calc_meishiki(1976, 5, 4, 4)


def test_meishiki_matches_takemoto_sheet():
    m = _kaito()
    pillars = [(p.tengan, p.chishi) for p in m.pillars]
    assert pillars == [("丙", "辰"), ("壬", "辰"), ("丙", "辰"), ("庚", "寅")]


def test_kuubou_shi_ushi():
    m = _kaito()
    assert kuubou(m.day) == ("子", "丑")


def test_kagai_present():
    m = _kaito()
    assert kagai(m) is True


def test_tentoku_kijin_present():
    m = _kaito()
    all_chars = {p.tengan for p in m.pillars} | {p.chishi for p in m.pillars}
    assert tentoku_kijin(m.month.chishi, all_chars) is True


def test_gettoku_kijin_present():
    m = _kaito()
    all_tengan = {p.tengan for p in m.pillars}
    assert gettoku_kijin(m.month.chishi, all_tengan) is True


def test_chouko_yougjin_mizu_ki():
    m = _kaito()
    assert chouko_yougjin(m.nikkan, m.month.chishi) == "壬・甲"


def test_身弱():
    m = _kaito()
    result = mi_kyojaku(m)
    assert result.label == "身弱"


def test_daiun_matches_takemoto_sheet():
    """竹本氏鑑定書の大運表と一致するか。"""
    m = _kaito()
    duns = daiun(m, year=1976, month=5, day=4, sex="M", count=8)
    # 2〜11才: 癸巳, 12〜21才: 甲午, 22〜31才: 乙未, 32〜41才: 丙申,
    # 42〜51才: 丁酉, 52〜61才: 戊戌, 62〜71才: 己亥, 72〜81才: 庚子
    expected = [
        (2, 11, "癸", "巳"),
        (12, 21, "甲", "午"),
        (22, 31, "乙", "未"),
        (32, 41, "丙", "申"),
        (42, 51, "丁", "酉"),
        (52, 61, "戊", "戌"),
        (62, 71, "己", "亥"),
        (72, 81, "庚", "子"),
    ]
    actual = [(d.age_from, d.age_to, d.tengan, d.chishi) for d in duns]
    assert actual == expected


def test_juniun_丙_辰():
    # 丙日干から見た辰は「冠帯」
    assert juniun("丙", "辰") == "冠"


def test_count_gogyo_no_missing():
    m = _kaito()
    counts = count_gogyo(m)
    # 重み付き集計では全五行揃う（時柱を含む完全命式）
    assert all(v > 0 for v in counts.values())


def test_reading_integration():
    m = _kaito()
    r = reading(m, year=1976, month=5, day=4, sex="M", today_year=2026)
    assert r.kuubou == ("子", "丑")
    assert r.kagai is True
    assert r.tentoku is True
    assert r.gettoku is True
    assert r.chouko == "壬・甲"
    assert r.mikyojaku.label == "身弱"
    assert len(r.daiun_list) == 8
    assert len(r.nenmawari_list) == 5


def test_nenmawari_2026_kaito():
    """2026年（丙午）の中井さん（丙日干）は帝旺＝成功・人気"""
    n = nenmawari("丙", birth_year=1976, target_year=2026)
    assert n.nen_kanshi == "丙午"
    assert n.juniun == "帝"
    assert "成功" in n.label or "人気" in n.label
    assert n.age == 50


def test_nenmawari_range_returns_consecutive_years():
    years = nenmawari_range("丙", birth_year=1976, from_year=2026, years=3)
    assert [y.year for y in years] == [2026, 2027, 2028]
    assert [y.age for y in years] == [50, 51, 52]


def test_nenmawari_juniun_cycle():
    """十二運は12年周期で循環するはず"""
    n0 = nenmawari("丙", birth_year=1976, target_year=2026)
    n12 = nenmawari("丙", birth_year=1976, target_year=2038)
    assert n0.juniun == n12.juniun  # 12年後は同じ十二運


def test_tsukimawari_2026_06_kaito():
    """2026年6月、kaitoさん（丙日干）は午月 = 帝旺 = 成功・人気"""
    from app.shozan import tsukimawari
    tk = tsukimawari("丙", birth_year=1976, target_year=2026, target_month=6)
    assert tk.getsu_chishi == "午"
    assert tk.juniun == "帝"
    assert "成功" in tk.label or "人気" in tk.label
    assert tk.age == 50


def test_tsukimawari_range_returns_12_months():
    from app.shozan import tsukimawari_range
    months = tsukimawari_range(
        "丙", birth_year=1976, from_year=2026, from_month=6, months=12
    )
    assert len(months) == 12
    assert (months[0].year, months[0].month) == (2026, 6)
    assert (months[-1].year, months[-1].month) == (2027, 5)


def test_tsukimawari_year_rollover():
    """月が12を超えたら翌年1月にロールオーバー"""
    from app.shozan import tsukimawari_range
    months = tsukimawari_range(
        "丙", birth_year=1976, from_year=2026, from_month=11, months=4
    )
    expected_ym = [(2026, 11), (2026, 12), (2027, 1), (2027, 2)]
    assert [(m.year, m.month) for m in months] == expected_ym
