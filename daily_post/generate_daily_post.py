"""今日の日干別運勢の投稿文を生成する。

毎朝 launchd から呼ばれ、X版（短文）と Threads版（フル）の投稿文を生成。
- 出力先: daily_post/output/YYYY-MM-DD.txt
- X版はクリップボードにコピーされる（post_daily.sh が実施）

運用: 生成は全自動、投稿は kaitoさんが貼り付けるだけ（朝note・Threads noteと同方式）
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

# app パッケージを import できるように親ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sxtwl  # noqa: E402

from app.bazi import CHISHI, TENGAN  # noqa: E402
from app.shozan import HIMAWARI_KEYWORDS, juniun  # noqa: E402

APP_URL = "https://shozan-nikkan.streamlit.app"

# 日干の表示用データ（絵文字・タイプ名）
NIKKAN_LABEL = {
    "甲": ("🌳", "大木"),
    "乙": ("🌸", "草花"),
    "丙": ("☀️", "太陽"),
    "丁": ("🕯", "灯火"),
    "戊": ("🏔", "大地"),
    "己": ("🌾", "田畑"),
    "庚": ("⚔️", "鋼鉄"),
    "辛": ("💎", "宝石"),
    "壬": ("🌊", "大海"),
    "癸": ("💧", "雨露"),
}

ALL_NIKKAN = list("甲乙丙丁戊己庚辛壬癸")


def get_today_kanshi(date: datetime.date) -> tuple[str, str]:
    """今日の日干支（天干・地支）を返す。"""
    d = sxtwl.fromSolar(date.year, date.month, date.day)
    gz = d.getDayGZ()
    return TENGAN[gz.tg], CHISHI[gz.dz]


def build_posts(date: datetime.date) -> tuple[str, str]:
    """X版（短文）と Threads版（フル）の投稿文を生成して返す。"""
    _, day_chishi = get_today_kanshi(date)
    day_tg, _ = get_today_kanshi(date)
    kanshi = day_tg + day_chishi

    # 全日干の今日の十二運を計算
    readings = {}
    for nk in ALL_NIKKAN:
        ju = juniun(nk, day_chishi)
        label, detail = HIMAWARI_KEYWORDS[ju]
        readings[nk] = (ju, label, detail)

    # ピックアップ: 頂点日（帝）・開拓日（長）・守りの日（墓）・再生日（絶）
    groups = [
        ("🎯頂点日", [nk for nk, (ju, _, _) in readings.items() if ju == "帝"]),
        ("🌱開拓日", [nk for nk, (ju, _, _) in readings.items() if ju == "長"]),
        ("🛡守りの日", [nk for nk, (ju, _, _) in readings.items() if ju == "墓"]),
        ("♻️再生日", [nk for nk, (ju, _, _) in readings.items() if ju == "絶"]),
    ]

    def fmt_group(nks: list[str]) -> str:
        return "・".join(
            f"{NIKKAN_LABEL[nk][0]}{nk}（{NIKKAN_LABEL[nk][1]}）" for nk in nks
        )

    md = f"{date.month}月{date.day}日"

    # ---------------- X版（全角140字以内を意識した短文） ----------------
    # 該当日干がいないグループの行は省略
    group_lines = [
        f"{label}: {fmt_group(nks)}" for label, nks in groups if nks
    ]
    x_post = (
        f"【{md}の運勢】今日は{kanshi}の日\n"
        f"\n"
        + "\n".join(group_lines)
        + f"\n\n"
        f"あなたの日干を調べる👇\n"
        f"{APP_URL}\n"
        f"#今日の運勢 #四柱推命"
    )

    # ---------------- Threads版（10日干フル） ----------------
    lines = [f"【{md}の運勢】今日は{kanshi}の日", ""]
    for nk in ALL_NIKKAN:
        emoji, type_name = NIKKAN_LABEL[nk]
        ju, label, detail = readings[nk]
        lines.append(f"{emoji}{nk}（{type_name}の人）→ {label}")
    lines += [
        "",
        "自分の日干（タイプ）が分からない人は、",
        "生年月日だけで調べられます👇",
        APP_URL,
        "",
        "#今日の運勢 #四柱推命 #日干10タイプ診断",
    ]
    threads_post = "\n".join(lines)

    return x_post, threads_post


def main() -> None:
    today = datetime.date.today()
    x_post, threads_post = build_posts(today)

    out_dir = Path(__file__).resolve().parent / "output"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"{today.isoformat()}.txt"

    content = (
        "========== X（Twitter）版 ==========\n"
        f"{x_post}\n"
        "\n"
        "========== Threads版 ==========\n"
        f"{threads_post}\n"
    )
    out_file.write_text(content, encoding="utf-8")

    # 標準出力には X版のみ（post_daily.sh がクリップボードに入れる）
    print(x_post)


if __name__ == "__main__":
    main()
