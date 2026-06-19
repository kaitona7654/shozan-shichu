"""日干10タイプ診断アプリ（特化版）。

生年月日だけで「あなたの日干」が分かる超シンプル版。
note記事「日干10タイプ」から流入したユーザー向けの最小入口。

起動:
  streamlit run web_app_nikkan.py

デプロイ:
  Streamlit Cloud で別アプリとして公開可能
  （フル機能版と棲み分け：日干特化版＝集客、フル版＝深堀り）
"""
from __future__ import annotations

from datetime import date

import streamlit as st

from app.bazi import calc_meishiki


# ----------------------------------------------------------------------
# 10タイプの解説データ（note記事「日干10タイプ」と完全整合）
# ----------------------------------------------------------------------
NIKKAN_DATA = {
    "甲": {
        "emoji": "🌳",
        "title": "大木の人",
        "gogyo": "陽の木",
        "essence": "まっすぐに伸びる大木。リーダー気質、目標志向、誠実。",
        "strengths": [
            "リーダーシップ、人前に立つ素養",
            "誠実で信頼される",
            "長期的な目標達成力",
        ],
        "weakness": "頑固で融通が利かない傾向",
        "advice": "月1回は人の意見を「全肯定」して聞く日を作る。柔軟性は意識して訓練する。",
        "ok_jobs": "大組織・管理職・教育・建築",
        "ng_jobs": "転職を繰り返す自由業、瞬発力勝負の営業最前線",
        "color": "#2d8659",  # 深緑
    },
    "乙": {
        "emoji": "🌸",
        "title": "草花の人",
        "gogyo": "陰の木",
        "essence": "しなやかに環境に合わせる草花。柔軟性、適応力、粘り強さ。",
        "strengths": [
            "圧倒的な適応力",
            "柔らかな人当たり、好かれる",
            "諦めない粘り強さ",
        ],
        "weakness": "自己主張が弱く、流されやすい",
        "advice": "月初に「今月は何を譲らないか」を3つ決めておく。譲れない軸を明文化する。",
        "ok_jobs": "サービス業、接客、福祉、教育、芸術",
        "ng_jobs": "即断即決を要する経営、規律の厳しい体育会系組織",
        "color": "#a4c639",  # 黄緑
    },
    "丙": {
        "emoji": "☀️",
        "title": "太陽の人",
        "gogyo": "陽の火",
        "essence": "周囲を明るく照らす太陽。明朗、情熱、リーダー気質、社交的。",
        "strengths": [
            "圧倒的な存在感、人を引きつける力",
            "明るく前向き、社交的",
            "情熱的にプロジェクトを進める",
        ],
        "weakness": "派手好きで衝動的、燃え尽きやすい",
        "advice": "「大きな買い物は翌日まで待つルール」を徹底。意識的に休む時間をスケジュールに組み込む。",
        "ok_jobs": "営業、芸能、広報、サービス業、人前に出る仕事",
        "ng_jobs": "地味な裏方作業、長期間一人で集中する研究職",
        "color": "#ff6b35",  # 太陽オレンジ
    },
    "丁": {
        "emoji": "🕯",
        "title": "灯火の人",
        "gogyo": "陰の火",
        "essence": "部屋を静かに照らす灯火。繊細、洞察力、温かさ、奥深さ。",
        "strengths": [
            "鋭い洞察力、人の心が読める",
            "芸術的センス、繊細な美意識",
            "静かに人を支える力",
        ],
        "weakness": "気を遣いすぎて消耗、自分を後回しに",
        "advice": "週1回「自分だけのための時間」を予定に入れる。NoをはっきりNoと言う練習を。",
        "ok_jobs": "クリエイティブ（デザイン・文章・音楽）、カウンセリング、教育、研究",
        "ng_jobs": "大音量・大人数の営業職、判断を即断で求められる職場",
        "color": "#c9302c",  # 灯火の赤
    },
    "戊": {
        "emoji": "🏔",
        "title": "大地の人",
        "gogyo": "陽の土",
        "essence": "動かない大地。包容力、安定感、信義、頑固。",
        "strengths": [
            "包容力、人が頼ってくる",
            "動じない安定感",
            "信義を重んじ、約束を守る",
        ],
        "weakness": "頑固で人の意見を受け入れにくい、行動が遅い",
        "advice": "「3日以内に決める」マイルールを設ける。年に1回は環境を意図的に変える（旅行・引越し等）。",
        "ok_jobs": "公務員、不動産、建築、銀行、長期勤続型の大企業",
        "ng_jobs": "変化の激しいスタートアップ、フリーランス1本",
        "color": "#8b6f47",  # 大地の茶
    },
    "己": {
        "emoji": "🌾",
        "title": "田畑の人",
        "gogyo": "陰の土",
        "essence": "作物を育てる田畑。母性、現実的、世話好き、堅実。",
        "strengths": [
            "育てる力、教える適性",
            "現実的で堅実、計算が立つ",
            "世話好き、人徳がある",
        ],
        "weakness": "自分のことは後回し、保守的すぎてチャンスを逃す",
        "advice": "「自分への投資」を月1万円から始める。新しいことを年4回は挑戦するルール。",
        "ok_jobs": "教育（特に教師）、看護・介護、人事、料理関係",
        "ng_jobs": "冷徹な判断を求められる金融トレーダー、競争激しいスポーツ業界",
        "color": "#d4a574",  # 田畑の黄土色
    },
    "庚": {
        "emoji": "⚔️",
        "title": "刃物の人",
        "gogyo": "陽の金",
        "essence": "鍛え抜かれた刃物。決断力、義理堅さ、武の星、リーダーシップ。",
        "strengths": [
            "圧倒的な決断力・実行力",
            "規律と正義感",
            "リーダーシップ、組織を率いる力",
        ],
        "weakness": "言葉がきつい、対立を生みやすい、白黒つけたがる",
        "advice": "「3秒数えてから言葉を選ぶ」習慣。「灰色」も世の中の知恵だと意識的に学ぶ。",
        "ok_jobs": "軍隊・警察・消防、経営者、外科医、スポーツ選手、士業（特に弁護士）",
        "ng_jobs": "慰めや傾聴を求められるカウンセラー、芸術的繊細さが必要な職",
        "color": "#6c757d",  # 鋼鉄のグレー
    },
    "辛": {
        "emoji": "💎",
        "title": "宝石の人",
        "gogyo": "陰の金",
        "essence": "磨かれた宝石。繊細、美意識、プライド、品格。",
        "strengths": [
            "繊細な美的センス",
            "完璧主義による高い品質",
            "上品で洗練された印象",
        ],
        "weakness": "プライドが高く傷つきやすい、批判精神が強い",
        "advice": "「褒める言葉を1日3回」を習慣化。完璧主義を捨てて「8割でOK」と自分に許可を出す。",
        "ok_jobs": "デザイン、ファッション、宝石・美術・骨董、高級ホテル、外資系企業",
        "ng_jobs": "泥臭い現場仕事、ガサツさが求められる業界",
        "color": "#b8a5d4",  # 宝石のラベンダー
    },
    "壬": {
        "emoji": "🌊",
        "title": "大海の人",
        "gogyo": "陽の水",
        "essence": "流れる大海。知性、適応力、流動性、包容力。",
        "strengths": [
            "深い知性、教養への適性",
            "状況対応力、柔軟性",
            "大局を見る視野の広さ",
        ],
        "weakness": "感情を内に溜め込みやすい、動きが読めない",
        "advice": "月1回、信頼できる人に「いま考えていること」を1時間話す。日記やnoteで言語化する。",
        "ok_jobs": "研究職、ジャーナリスト、貿易、海運、観光、国際関係、教育",
        "ng_jobs": "ルーチンワーク中心の事務職、感情を表に出すパフォーマー業",
        "color": "#0077b6",  # 深い青
    },
    "癸": {
        "emoji": "💧",
        "title": "雨露の人",
        "gogyo": "陰の水",
        "essence": "草花を潤す雨露。優しさ、感受性、清らかさ、控えめ。",
        "strengths": [
            "共感力、人の気持ちを察する",
            "清らかな印象、信頼される",
            "内省的、深い思考力",
        ],
        "weakness": "気を遣いすぎて疲弊する、流されやすい",
        "advice": "月初に「絶対に断る3つのこと」を決める。月1回は完全に自分のための時間を確保。",
        "ok_jobs": "医療・看護、心理カウンセラー、福祉、教育、芸術（特に文学）",
        "ng_jobs": "営業ノルマの厳しい職場、人を蹴落とす競争の激しい環境",
        "color": "#a8dadc",  # 雨露の水色
    },
}

# 日干の漢字は小学校で習わない難しい字（戊・己・庚・辛・壬・癸 など）が多いので、
# 読みがなを添えてやさしく見せる。キャラ画像と揃えて音読み表記にする。
NIKKAN_YOMI = {
    "甲": "きのえ",
    "乙": "きのと",
    "丙": "ひのえ",
    "丁": "ひのと",
    "戊": "つちのえ",
    "己": "つちのと",
    "庚": "かのえ",
    "辛": "かのと",
    "壬": "みずのえ",
    "癸": "みずのと",
}


# ----------------------------------------------------------------------
# ページ設定
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="あなたの日干を調べる | 四柱推命10タイプ診断",
    page_icon="🔮",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ----------------------------------------------------------------------
# ブラウザに「日本語ページ」と宣言（Chrome自動翻訳の誤動作防止）＋
# Google Analytics 4 計測タグ（ページビュー・ユーザー数・流入元）
# Streamlitはiframe内でコードが動くため、親ドキュメントに注入する
# ----------------------------------------------------------------------
import streamlit.components.v1 as components

GA_MEASUREMENT_ID = "G-37X4KD65XS"

components.html(
    f"""
    <script>
      const w = window.parent;
      const doc = w.document;

      // --- React × Google翻訳 クラッシュ防止パッチ ---
      // 翻訳がテキストノードを<font>等で包み替えると、React(Streamlit)の再描画時に
      // insertBefore/removeChild が「対象が子でない」NotFoundError でアプリ全体を落とす。
      // これらのDOMメソッドを安全化し、翻訳が効いていても落ちないようにする（定番の回避策）。
      if (w.Node && w.Node.prototype && !w.__nodePatchApplied) {{
        w.__nodePatchApplied = true;
        const _insertBefore = w.Node.prototype.insertBefore;
        w.Node.prototype.insertBefore = function (newNode, referenceNode) {{
          if (referenceNode && referenceNode.parentNode !== this) {{
            return this.appendChild(newNode);
          }}
          return _insertBefore.call(this, newNode, referenceNode);
        }};
        const _removeChild = w.Node.prototype.removeChild;
        w.Node.prototype.removeChild = function (child) {{
          if (child && child.parentNode !== this) {{
            return child;
          }}
          return _removeChild.call(this, child);
        }};
      }}

      // 日本語ページ宣言（Chrome自動翻訳の誤動作防止）
      // translate="no" は Chrome 翻訳を最も強く抑止する属性。lang=ja と併用。
      doc.documentElement.lang = 'ja';
      doc.documentElement.setAttribute('translate', 'no');
      doc.documentElement.classList.add('notranslate');
      if (!doc.querySelector('meta[name="google"][content="notranslate"]')) {{
        const meta = doc.createElement('meta');
        meta.name = 'google';
        meta.content = 'notranslate';
        doc.head.appendChild(meta);
      }}
      // GA4 計測タグ（二重挿入防止つき）
      if (!doc.getElementById('ga4-script')) {{
        const s = doc.createElement('script');
        s.id = 'ga4-script';
        s.async = true;
        s.src = 'https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}';
        doc.head.appendChild(s);
        const inline = doc.createElement('script');
        inline.textContent = "window.dataLayer = window.dataLayer || [];" +
          "function gtag(){{dataLayer.push(arguments);}}" +
          "gtag('js', new Date());" +
          "gtag('config', '{GA_MEASUREMENT_ID}');";
        doc.head.appendChild(inline);
      }}
    </script>
    """,
    height=0,
)


def track_event(event_name: str, **params):
    """GA4にカスタムイベントを送信する（診断実行回数などの計測用）。"""
    import json
    params_json = json.dumps(params, ensure_ascii=False)
    components.html(
        f"""
        <script>
          const w = window.parent;
          if (typeof w.gtag === 'function') {{
            w.gtag('event', '{event_name}', {params_json});
          }}
        </script>
        """,
        height=0,
    )


# ----------------------------------------------------------------------
# CSS
# ----------------------------------------------------------------------
st.markdown(
    """
    <style>
      .main {background-color: #faf7f2;}
      h1 {color: #2c2c2c; font-family: 'Yu Mincho', serif; text-align: center;}
      .stButton button {
        background-color: #6b4423; color: white; border: none;
        padding: 12px 32px; font-size: 1.1em; border-radius: 4px;
        width: 100%;
      }
      .stButton button:hover {background-color: #8b5a33;}
      .result-card {
        padding: 24px; border-radius: 8px; color: white;
        text-align: center; margin: 16px 0;
      }
      .result-emoji {font-size: 4em; margin: 8px 0;}
      .result-title {font-size: 1.8em; font-weight: bold; margin: 8px 0;}
      .result-essence {font-size: 1.1em; line-height: 1.6;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------
# ヘッダー
# ----------------------------------------------------------------------
st.title("🔮 あなたの日干を調べる")
st.markdown(
    "<div style='text-align:center; color:#666;'>"
    "象山流四柱推命　── 血液型より深い「10タイプ診断」"
    "</div>",
    unsafe_allow_html=True,
)
st.markdown("")

# ----------------------------------------------------------------------
# 入力フォーム（超シンプル：生年月日のみ）
# ----------------------------------------------------------------------
with st.form("nikkan_form"):
    st.markdown("### 📝 生年月日を入力してください")

    col1, col2, col3 = st.columns(3)
    with col1:
        year = st.number_input("年（西暦）", min_value=1900, max_value=2030, value=1990, step=1)
    with col2:
        month = st.number_input("月", min_value=1, max_value=12, value=1, step=1)
    with col3:
        day = st.number_input("日", min_value=1, max_value=31, value=1, step=1)

    hour_options = ["不明・入力しない"] + [f"{h}時台" for h in range(24)]
    hour_label = st.selectbox(
        "出生時刻（任意）",
        hour_options,
        index=0,
        help="時刻が分かると「時柱」まで含めた四柱（生まれ持った4本の柱）が表示されます",
    )
    hour = None if hour_label == "不明・入力しない" else int(hour_label.replace("時台", ""))

    st.markdown(
        "<small>※ 西暦（新暦）でご入力ください。性別は不要。"
        "**生年月日だけでも、あなたの本質的なタイプが分かります**。"
        "出生時刻も入力すると、四柱（年柱・月柱・日柱・時柱）の完全表示が追加されます。</small>",
        unsafe_allow_html=True,
    )

    submitted = st.form_submit_button("🔮 日干を調べる", use_container_width=True)


# ----------------------------------------------------------------------
# 結果表示
# ----------------------------------------------------------------------
if submitted:
    try:
        m = calc_meishiki(int(year), int(month), int(day), hour)
        nikkan = m.nikkan
        info = NIKKAN_DATA[nikkan]
    except Exception as e:
        st.error(f"計算に失敗しました：{e}")
        st.stop()

    # GA4: 診断実行イベント（何回診断されたか・どの日干が多いかを計測）
    track_event("diagnosis", nikkan=nikkan, with_hour=hour is not None)

    # タイプ別キャラクター（中央に表示）
    from pathlib import Path as _Path
    _char = _Path(__file__).parent / "assets" / "characters" / f"char_{nikkan}.png"
    if _char.exists():
        # 横長バナー（16:9）なので全幅で表示
        st.image(str(_char), use_container_width=True)

    # 結果カード
    st.markdown(
        f"""
        <div class='result-card notranslate' translate='no' style='background-color: {info["color"]};'>
            <div style='font-size:1.2em; opacity:0.9;'>あなたの日干は</div>
            <div class='result-emoji'>{info["emoji"]}</div>
            <div class='result-title'>{info["title"]}</div>
            <div style='font-size:0.95em; opacity:0.9; margin-bottom:6px;'>むかしの呼び名：{nikkan}〔{NIKKAN_YOMI[nikkan]}〕・{info["gogyo"][-1]}タイプ</div>
            <div class='result-essence'>{info["essence"]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 強み
    st.markdown("### ✨ あなたの強み")
    for s in info["strengths"]:
        st.markdown(f"- {s}")

    # 弱みと対策
    st.markdown("### ⚠️ 気をつけたい傾向と対策")
    st.markdown(f"❌ **{info['weakness']}**")
    st.markdown(f"✅ **対策**：{info['advice']}")

    # 職業適性
    st.markdown("### 💼 向く・向かない仕事")
    col_ok, col_ng = st.columns(2)
    with col_ok:
        st.markdown("**向く環境** 🟢")
        st.markdown(info["ok_jobs"])
    with col_ng:
        st.markdown("**向かない環境** 🔴")
        st.markdown(info["ng_jobs"])

    # あなたの四柱（命式）── 時刻入力時は時柱まで、未入力時は三柱
    st.markdown("### 📜 あなたの四柱（命式）")
    if hour is None:
        st.caption("出生時刻を入力すると、4本目の柱「時柱」も表示されます")
    pillar_cols = st.columns(len(m.pillars))
    PILLAR_MEANING = {
        "年柱": "先祖・幼少期",
        "月柱": "仕事・人生の中軸",
        "日柱": "自分自身",
        "時柱": "晩年・潜在才能",
    }
    for i, p in enumerate(m.pillars):
        with pillar_cols[i]:
            st.markdown(
                f"""
                <div style='text-align:center; padding:12px 4px; background:#f5f0e8;
                            border-radius:8px; border:1px solid #d9cfc0;'>
                    <div style='font-size:0.8em; color:#888;'>{p.name}</div>
                    <div style='font-size:2em; font-weight:bold; color:#2c2c2c;
                                font-family: "Yu Mincho", serif;'>{p.tengan}{p.chishi}</div>
                    <div style='font-size:0.7em; color:#999;'>{PILLAR_MEANING.get(p.name, "")}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # CTA：もっと深く見たい
    st.markdown("---")
    st.markdown("### 💎 もっと深く知りたい方へ")
    st.info(
        "**日干は四柱推命の入口です**。\n\n"
        "本格的な鑑定では、命式の全体・五行バランス・大運（10年運勢）・年廻り・月廻り・"
        "日廻り・神殺・調候用神・開運法・適職判定までを総合的に読み解きます。\n\n"
        "▶ **完全鑑定アプリ（準備中）**\n\n"
        "▶ **個別鑑定の受付**：noteメッセージから（https://note.com/great_thyme4680）"
    )

    # シェア促進（ワンクリックでX・LINEに投稿）
    import urllib.parse

    st.markdown("---")
    st.markdown("### 📢 結果をシェアしよう")

    app_url = "https://shozan-nikkan.streamlit.app"
    share_text = (
        f"私の日干は『{info['title']}（{nikkan}・{NIKKAN_YOMI[nikkan]}）』でした！{info['emoji']}\n"
        f"{info['essence']}\n\n"
        f"あなたは何タイプ？\n"
        f"#日干10タイプ診断 #四柱推命"
    )
    tweet_url = (
        "https://twitter.com/intent/tweet"
        f"?text={urllib.parse.quote(share_text)}"
        f"&url={urllib.parse.quote(app_url)}"
    )
    line_url = (
        "https://social-plugins.line.me/lineit/share"
        f"?url={urllib.parse.quote(app_url)}"
        f"&text={urllib.parse.quote(share_text)}"
    )

    col_x, col_line = st.columns(2)
    with col_x:
        st.link_button("𝕏 で結果をポストする", tweet_url, use_container_width=True)
    with col_line:
        st.link_button("💬 LINEで友達に送る", line_url, use_container_width=True)

    with st.expander("📋 テキストをコピーしてシェアする"):
        st.code(f"{share_text}\n{app_url}", language=None)
        st.caption("☝️ 右上のコピーアイコンでコピーできます")


# ----------------------------------------------------------------------
# フッター
# ----------------------------------------------------------------------
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #888; font-size: 0.85em;'>
      🔮 象山流四柱推命「日干10タイプ診断」<br>
      © 2026 kaito ｜ <a href='https://note.com/great_thyme4680'>note</a> ｜
      <a href='#'>記事『血液型より深い日干10タイプ』を読む</a><br>
      ※ 本診断は娯楽・参考目的です。重要な意思決定の根拠とはなさらないでください。
    </div>
    """,
    unsafe_allow_html=True,
)
