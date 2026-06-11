"""象山流四柱推命 Web版（Streamlit）

起動:
  streamlit run web_app.py

デプロイ:
  Streamlit Cloud (https://streamlit.io/cloud) で
  GitHubリポジトリを連携 → ANTHROPIC_API_KEY を Secrets に設定
"""
from __future__ import annotations

import os
from datetime import date

from dotenv import load_dotenv

# Streamlit Cloud では st.secrets が優先、ローカル開発では .env を使う
load_dotenv()

import streamlit as st  # noqa: E402

# Streamlit Cloud の secrets を環境変数に流す
if "ANTHROPIC_API_KEY" in st.secrets:
    os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
if "ANTHROPIC_MODEL" in st.secrets:
    os.environ["ANTHROPIC_MODEL"] = st.secrets["ANTHROPIC_MODEL"]

from app.bazi import calc_meishiki  # noqa: E402
from app.formatter import format_meishiki_text  # noqa: E402
from app.judgment import free_excerpt, generate as generate_judgment  # noqa: E402
from app.shozan import reading as shozan_reading  # noqa: E402


# ----------------------------------------------------------------------
# ページ設定
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="象山流 四柱推命 | 中国伝統と日本独自の融合鑑定",
    page_icon="🔮",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ----------------------------------------------------------------------
# CSS（雰囲気作り）
# ----------------------------------------------------------------------
st.markdown(
    """
    <style>
      .main {background-color: #faf7f2;}
      h1 {color: #2c2c2c; font-family: 'Yu Mincho', serif;}
      h2 {color: #6b4423; border-bottom: 2px solid #6b4423; padding-bottom: 4px;}
      .stButton button {
        background-color: #6b4423; color: white; border: none;
        padding: 12px 32px; font-size: 1.1em; border-radius: 4px;
      }
      .stButton button:hover {background-color: #8b5a33;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------
# ヘッダー
# ----------------------------------------------------------------------
st.title("🔮 象山流 四柱推命")
st.markdown(
    "**田邊象山創始の日本独自流派による命式鑑定**　"
    "生年月日（とお名前）から、性格・適職・運勢を読み解きます。"
)


# ----------------------------------------------------------------------
# 入力フォーム
# ----------------------------------------------------------------------
with st.form("birth_form"):
    st.subheader("📝 生年月日を入力してください")

    col1, col2, col3 = st.columns(3)
    with col1:
        year = st.number_input("生年（西暦）", min_value=1900, max_value=2026, value=1990, step=1)
    with col2:
        month = st.number_input("月", min_value=1, max_value=12, value=1, step=1)
    with col3:
        day = st.number_input("日", min_value=1, max_value=31, value=1, step=1)

    col4, col5 = st.columns(2)
    with col4:
        hour_options = ["不明"] + [f"{h}時台" for h in range(24)]
        hour_label = st.selectbox("出生時刻（任意）", hour_options, index=0)
        hour = None if hour_label == "不明" else int(hour_label.replace("時台", ""))
    with col5:
        sex_label = st.radio("性別", ["男性", "女性"], horizontal=True)
        sex = "M" if sex_label == "男性" else "F"

    name = st.text_input(
        "お名前（任意・起名学評価が追加されます）",
        max_chars=20,
        placeholder="例：中井利幸",
    )

    st.markdown(
        "<small>※ 西暦（新暦）でご入力ください。出生時刻が分かれば時柱まで含めた精度の高い鑑定になります。</small>",
        unsafe_allow_html=True,
    )

    submitted = st.form_submit_button("鑑定する", use_container_width=True)


# ----------------------------------------------------------------------
# 鑑定処理
# ----------------------------------------------------------------------
FREEMIUM_MODE = os.getenv("FREEMIUM_MODE", "true").lower() in ("true", "1", "yes")

if submitted:
    try:
        m = calc_meishiki(int(year), int(month), int(day), hour)
    except Exception as e:
        st.error(f"命式の算出に失敗しました：{e}")
        st.stop()

    # 命式計算機モード：API無しでも全データを表示
    import datetime
    r = shozan_reading(
        m,
        year=int(year),
        month=int(month),
        day=int(day),
        sex=sex,
        today_year=datetime.date.today().year,
        today_month=datetime.date.today().month,
    )

    # 命式表示
    st.markdown("---")
    st.markdown("### 📜 命式")
    st.code(format_meishiki_text(m), language=None)

    # 五行バランス
    st.markdown("### 🌳 五行バランス")
    gogyo_cols = st.columns(5)
    for i, (g, c) in enumerate(r.gogyo_counts.items()):
        with gogyo_cols[i]:
            st.metric(g, c)
    if r.missing:
        st.warning(f"⚠️ 欠落している五行: {', '.join(r.missing)}")

    # 吉神・空亡
    st.markdown("### ✨ 吉神・凶神・空亡")
    kichi_cols = st.columns(4)
    badges = [
        ("華蓋", r.kagai), ("天徳貴人", r.tentoku), ("月徳貴人", r.gettoku),
        ("天乙貴人", r.tenotsu), ("将星", r.shosei), ("桃花", r.touka),
        ("羊刃", r.yojin), ("紅艶", r.koen),
    ]
    for i, (name_, has) in enumerate(badges):
        with kichi_cols[i % 4]:
            st.write(f"{'🟢' if has else '⚪'} {name_}")
    st.info(f"🌑 空亡: {r.kuubou[0]}・{r.kuubou[1]}（この地支の年・月・日は契約・大決断を避ける）")

    # 調候・身強身弱
    st.markdown("### 🎯 調候用神 & 身強身弱")
    col_l, col_r = st.columns(2)
    with col_l:
        st.metric("調候用神", r.chouko or "標準テーブル外")
    with col_r:
        st.metric("身強身弱", r.mikyojaku.label)

    # 大運
    st.markdown("### 📅 大運（10年単位の運勢）")
    daiun_data = []
    for d in r.daiun_list:
        daiun_data.append({
            "期間": f"{d.age_from}〜{d.age_to}才",
            "干支": f"{d.tengan}{d.chishi}",
            "通変": d.tsuhensei,
            "十二運": d.juniun,
        })
    st.dataframe(daiun_data, use_container_width=True, hide_index=True)

    # 年廻り
    st.markdown("### 🌸 年廻り（今年からの運気波形）")
    nen_data = []
    for n in r.nenmawari_list:
        nen_data.append({
            "年": f"{n.year}（{n.age}才）",
            "年干支": n.nen_kanshi,
            "十二運": n.juniun,
            "運気段階": n.label,
            "アドバイス": n.detail,
        })
    st.dataframe(nen_data, use_container_width=True, hide_index=True)

    # 月廻り
    st.markdown("### 🌙 月廻り（今月からの月別運勢）")
    tk_data = []
    for tk in r.tsukimawari_list:
        tk_data.append({
            "月": f"{tk.year}年{tk.month:2d}月",
            "干支": tk.getsu_kanshi,
            "十二運": tk.juniun,
            "運気段階": tk.label,
            "アドバイス": tk.detail,
        })
    st.dataframe(tk_data, use_container_width=True, hide_index=True)

    # 日廻り（今日から7日間）
    from app.shozan import himawari_range
    st.markdown("### ☀️ 今日からの7日間の運勢")
    days = himawari_range(
        m.nikkan,
        from_date=datetime.date.today(),
        days=7,
        kuubou_chishi=r.kuubou,
    )
    himi_data = []
    for h in days:
        himi_data.append({
            "日付": h.date,
            "干支": h.nichi_kanshi,
            "十二運": h.juniun,
            "運気段階": h.label,
            "アドバイス": h.detail + (" ⚠️空亡日" if h.is_kuubou else ""),
        })
    st.dataframe(himi_data, use_container_width=True, hide_index=True)

    # AI鑑定文セクション（API key設定時のみ）
    st.markdown("---")
    if not os.getenv("ANTHROPIC_API_KEY"):
        st.markdown("### 💎 さらに深い鑑定をご希望の方へ")
        st.info(
            "**性格・適職・金運・仕事運・結婚運・開運法・起名学・家系メッセージ・ライフプラン**など、"
            "象山流ならではの**13セクション完全鑑定**は、ココナラ／noteで個別受付しております。\n\n"
            "▶ note: https://note.com/great_thyme4680\n"
            "▶ ココナラ: 準備中"
        )
        st.stop()

    with st.spinner("象山流の鑑定文を生成しています…（10〜30秒）"):
        try:
            r = shozan_reading(
                m, year=int(year), month=int(month), day=int(day), sex=sex
            )
            full_judgment = generate_judgment(
                m, r, name=name or None, sex=sex
            )
        except Exception as e:
            st.error(f"鑑定文の生成に失敗しました：{e}")
            st.stop()

    # フリーミアム判定
    st.markdown("---")
    if FREEMIUM_MODE:
        st.markdown("### 🔮 象山流鑑定（無料版）")
        st.markdown(free_excerpt(full_judgment))

        st.markdown("---")
        st.markdown("### 💎 完全鑑定（¥1,500）")
        st.markdown(
            "無料版では性格傾向のみご覧いただけます。"
            "**全9セクション**を読みたい方は、完全鑑定をお求めください。"
        )
        st.info(
            "📌 決済機能は準備中です。リリースまでもう少々お待ちください。"
        )
    else:
        st.markdown("### 🔮 象山流鑑定（完全版）")
        st.markdown(full_judgment)


# ----------------------------------------------------------------------
# フッター
# ----------------------------------------------------------------------
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #888; font-size: 0.85em;'>
      © 2026 象山流四柱推命Bot — 田邊象山創始の日本独自流派<br>
      ※ 本鑑定は娯楽・参考目的です。重要な意思決定の根拠とはなさらないでください。<br>
      問い合わせ：（準備中）／ 特定商取引法に基づく表記：（準備中）
    </div>
    """,
    unsafe_allow_html=True,
)
