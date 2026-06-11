from app.parser import parse_birth


def test_slash_with_hour():
    b = parse_birth("1985/5/20 10")
    assert (b.year, b.month, b.day, b.hour) == (1985, 5, 20, 10)
    assert b.name is None and b.sex is None


def test_hyphen_with_colon_minutes():
    b = parse_birth("1985-05-20 10:30")
    assert (b.year, b.month, b.day, b.hour) == (1985, 5, 20, 10)


def test_japanese():
    b = parse_birth("1985年5月20日 10時")
    assert (b.year, b.month, b.day, b.hour) == (1985, 5, 20, 10)


def test_no_hour():
    b = parse_birth("2000/1/1")
    assert b.hour is None


def test_invalid():
    assert parse_birth("こんにちは") is None
    assert parse_birth("1985/13/40") is None


def test_with_name_and_sex():
    b = parse_birth("1976/5/4 4 中井利幸 男")
    assert (b.year, b.month, b.day, b.hour) == (1976, 5, 4, 4)
    assert b.name == "中井利幸"
    assert b.sex == "M"


def test_with_name_only_multiline():
    b = parse_birth("1976/5/4 4\n中井利幸")
    assert b.name == "中井利幸"
    assert b.sex is None


def test_sex_english():
    b = parse_birth("2000/1/1 F")
    assert b.sex == "F"
    assert b.name is None


def test_name_first():
    b = parse_birth("中井利幸 1976/5/4 4 男")
    assert b.name == "中井利幸"
    assert b.sex == "M"
    assert b.year == 1976
