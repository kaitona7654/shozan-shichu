"""ユーザー入力の生年月日(時)＋名前＋性別パース。

許容例:
  1985/05/20 10
  1985-5-20 10:30
  1985年5月20日 10時
  1985/05/20            # 時刻なし
  1976/5/4 4 中井利幸 男
  1976/5/4 4:30
  中井利幸 M

複数行も可。改行は空白扱い。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional

Sex = Literal["M", "F"]

_DATE_PATTERN = re.compile(
    r"""
    (?P<y>\d{4})\s*[/\-年.]\s*
    (?P<m>\d{1,2})\s*[/\-月.]\s*
    (?P<d>\d{1,2})日?
    (?:
        [\s,、　]+
        (?P<h>\d{1,2})\s*(?:時|:)\s*(?P<mi>\d{1,2})?\s*分?
        |
        [\s,、　]+
        (?P<h2>\d{1,2})\s*時?
    )?
    """,
    re.VERBOSE,
)

# 性別キーワード（単独で出現したもののみ）
_SEX_MAP = {"男": "M", "女": "F", "M": "M", "F": "F", "m": "M", "f": "F"}


@dataclass
class BirthInput:
    year: int
    month: int
    day: int
    hour: Optional[int]
    name: Optional[str] = None
    sex: Optional[Sex] = None


def parse_birth(text: str) -> Optional[BirthInput]:
    text = text.strip()
    m = _DATE_PATTERN.search(text)
    if not m:
        return None
    y, mo, d = int(m["y"]), int(m["m"]), int(m["d"])
    if not (1900 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31):
        return None
    h: Optional[int] = None
    raw_h = m["h"] if m["h"] is not None else m["h2"]
    if raw_h is not None:
        h = int(raw_h)
        if not 0 <= h <= 23:
            return None

    # 日付マッチ後の残り部分から名前・性別を抽出
    rest = (text[: m.start()] + " " + text[m.end():]).strip()

    name: Optional[str] = None
    sex: Optional[Sex] = None

    if rest:
        # トークン化（空白・改行・全角空白・読点で分割）
        tokens = [t for t in re.split(r"[\s、,　]+", rest) if t]
        # 性別キーワードを抜き出す
        remaining: list[str] = []
        for t in tokens:
            if t in _SEX_MAP and sex is None:
                sex = _SEX_MAP[t]  # type: ignore[assignment]
            else:
                remaining.append(t)

        # 残りを名前として結合（複数トークンなら姓+名の想定で結合）
        if remaining:
            joined = "".join(remaining)
            # 妥当性: 2〜20文字、日本語/英字含む
            if 2 <= len(joined) <= 20 and re.search(r"[一-龥ぁ-んァ-ヶa-zA-Z]", joined):
                name = joined

    return BirthInput(year=y, month=mo, day=d, hour=h, name=name, sex=sex)
