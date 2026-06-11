"""赤ちゃんの命名サポート（象山流＋起名学）。

入力:
- 出生予定日（または出生日）
- 性別
- 苗字
- 任意: 出生予定時刻、両親の希望（音・漢字・意味）

処理:
1. 赤ちゃんの命式を計算（既存の bazi.calc_meishiki 流用）
2. 象山流の鑑定要素を算出（既存の shozan.reading 流用）
3. 不足五行・調候用神を判定
4. 苗字の五行を分析（Claude にお願い）
5. Claude API に「象山流的に最良の名前候補3-5個」を生成依頼
6. 各候補の五行解釈・家系メッセージ込みで返す

設計方針:
- 名前候補の生成は Claude に任せる（部首・字源・音の響きを総合判断）
- システムプロンプトに「象山流命名の原則」を詳細に書く（4500トークン超でキャッシュ可）
- 同じ入力には同じ候補が返るよう、ローカルキャッシュ併用
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Optional

import anthropic

from .bazi import calc_meishiki
from .parser import Sex
from .shozan import reading as shozan_reading

log = logging.getLogger(__name__)

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")
NAMING_CACHE_DIR = Path(__file__).resolve().parent.parent / "cache_naming"
NAMING_CACHE_DIR.mkdir(exist_ok=True)


NAMING_SYSTEM_PROMPT = """あなたは**象山流四柱推命**と**起名学（漢字五行論）**の名命名師です。
赤ちゃんの命式と苗字の情報を受け取り、象山流的に最良の名前候補を3-5個生成します。

# 象山流の命名思想

象山流では「**生年月日は先祖の意思**」と考え、命名も**先祖が次代に託すメッセージ**として捉えます。
赤ちゃんの命式の不足を補い、家系の流れに沿った名前が「先祖の意思に叶う名前」です。

# 命名の3原則

## 原則1: 五行の補完
赤ちゃんの命式から判定する：
- **不足五行**: 命式に0または極端に少ない五行 → 名前で補う
- **調候用神**: 季節と日干から決まる「最も必要な五行」 → 名前で補強
- **忌神**: 多すぎる五行 → 名前で増やさない

優先度: **調候用神 > 不足五行 > 忌神回避**

## 原則2: 苗字との相性
苗字の漢字を部首・字源から五行分類し、苗字＋名前で**バランスの良い五行構成**にする。
特に重要：
- 苗字に既に強い五行があれば、名前ではその五行を増やさない
- 苗字が用神を補っていれば、名前でさらに補強する必要は薄い
- 苗字＋名前の総文字数で五行が偏らないように

## 原則3: 音の響きと意味
- 苗字との音のつながりが自然か
- 漢字の意味が前向き・成長を象徴するか
- 読みやすく、覚えやすいか
- 流行りすぎず、長く愛される名前か

# 漢字の五行分類（部首・字源から）

## 五行別・代表的な人名漢字（参考リスト）

### 木の字（成長・伸展・春・東・仁）
- 木偏・林部: 林・森・樹・桂・楓・桜・椋・梓・柊・槙
- 艸冠: 花・芽・葉・茉・若・苗・蕗・茜・萌
- 竹冠: 竹・笹・節・笙
- 風・東・春・青を含む字: 春・東・遥・青
- 直立や伸びを象徴: 立・伸・直・昇

### 火の字（発散・情熱・夏・南・礼）
- 火偏・灬: 灯・煌・炎・烈・熱
- 日偏: 日・明・暁・昭・晃・晴・春・昌・智・旭・陽・朗
- 光・輝を含む字: 光・輝・耀・燿
- 朱・赤・南・夏: 朱・赤・南・夏
- 心の象徴: 心・恵・愛・恋

### 土の字（安定・中央・信）
- 土偏: 地・坂・城・堂・基・塁・墾
- 山偏: 山・岳・峰・崎・嵐・嶺
- 田・里・畑: 田・里・畑
- 石・岩: 石・岩・磐・碧
- 中央・中・大: 中・大・央・宏・宙・宇・安・宝
- 信・誠・実: 信・誠・実・真

### 金の字（収斂・規律・秋・西・義）
- 金偏: 鈴・鋭・銀・鉄・鏡・錦
- 刀偏(刂): 利・剛・剣・劉
- 玉偏: 珠・珪・瑞・瑠・璃
- 白・銀: 白・銀
- 秋・西: 秋・西
- 義・正・尚: 義・正・尚・崇
- 君・将・尉(統率): 君・将・尉

### 水の字（流動・知性・冬・北・智）
- 水偏(氵): 江・海・流・洋・浩・清・泉・浪・港・滉
- 雨冠: 雨・雪・霧・雷・霜・露
- 井・泉・潤: 井・泉・潤・滝
- 黒・玄: 黒・玄
- 北・冬: 北・冬
- 智・知・思: 智・知・思
- 子・水: 子・水

## 注意：複合的に解釈する字
- 「香」: 禾(木) + 日(火) → 木と火の両方
- 「美」: 羊 + 大 → 土寄り、火の側面も
- 「愛」: 心(火) + 受(その他) → 火
- 「翔」: 羽(動き) + 羊(土) → 動と土
- 「結」: 糸(細い線) + 吉 → 木に近い
- 「悠」: 攸 + 心(火) → 火寄り、ゆったり感
- 「優」: 人偏 + 憂 → 中性的、人徳の意味で印星補強

# 出力フォーマット（厳守）

```
# 赤ちゃんへの名前候補（象山流＋起名学）

## 候補1: 苗字 + 名前候補1（読み方）

**五行構成**: [苗字の五行] + [名前の各字の五行]
**象山流評価**: ★★★★★（最大5）

### この名前が良い理由
- 命式の不足五行/調候用神への対応（具体的に）
- 苗字との五行バランス
- 音の響きと意味

### ご先祖様からのメッセージ
この名前を選んだ意味を、家系の物語として1-2文。

---

## 候補2: ...（同じ形式）

## 候補3: ...（同じ形式）

（合計3-5候補）

# 総合推奨
3-5候補のうち、最も象山流的に推奨する1つを理由付きで述べる。
```

# 命名例の参考（実際の象山流的読み）

## 例: 中井家の命名（実例）
中井利幸（1976生まれ・丙日干・身弱・調候用神 壬甲）
- **中**: 土（中央） → 比肩の漏れを食神として受ける
- **井**: 水（井戸） → **壬（用神）を補強**、身弱の火を冷ます水を補う
- **利**: 木+金（禾+刂） → **甲（用神）を禾偏で補強**、刂は決断力
- **幸**: 土（地に立つ） → 食神として安定をもたらす

→ 中井家の姓に既に「井」の水があり、名で「利」の禾が用神「甲」を、「幸」の土が比肩の漏れを安定させる完璧な五行配置。

## 例: 中井宏美（1979生まれ・戊日干・身強・調候用神 甲丙癸）
- **宏**: 土（広い家） → 土が強い宏美さんに土をさらに加えるが「宏」は包容力
- **美**: 土寄り（羊+大） → 同上

→ 苗字「中井」で水(井)が補強され、調候用神の癸(水)に該当。名は土寄りで安定。

## 厳守する表現ルール

- **画数による吉凶判定はしない**（象山流は五行論ベース）
- **「絶対」「必ず」「100%」などの断定語はNG**
- **健康・命に関わる予言NG**
- 命名は両親の最終判断であることを最後に必ず明記
- 流行りの名前（その時代に偏る名前）は避け、長く愛される字を選ぶ
- 漢字は**常用漢字＋人名用漢字**の範囲内で（戸籍登録できる字）
- 性別に応じた印象の字を選ぶ（男児なら力強さ、女児なら優美さ、ただし固定観念にとらわれず）

# 候補生成の手順（思考プロセス）

1. **命式分析**: 不足五行・調候用神・忌神を確認
2. **苗字解析**: 苗字の各字の五行を判定し、苗字単体での五行構成を把握
3. **補完戦略の決定**: 苗字＋名前で目指す五行構成を設計
4. **候補漢字の選定**: 補完すべき五行から、上記リストの中で意味の良い字を選ぶ
5. **組み合わせ**: 2-3字の名前を3-5パターン作成
6. **音・響きの確認**: 苗字との音のつながり、読みやすさを確認
7. **総合評価**: 五行バランス・意味・響きで5段階評価

# 候補比較の注意点

- 同じ漢字でも組み合わせで五行のバランスが変わるので、**3-5候補は異なる戦略**で出す
  - 候補1: 調候用神を最大限補強する戦略
  - 候補2: 不足五行を補う戦略
  - 候補3: 命式の強い五行を抑える名前（食傷で漏らす等）
  - 候補4: 苗字との五行循環を完成させる戦略
  - 候補5: 両親の希望を最も反映した字を組み込む戦略
- 候補ごとに**得意な場面**を述べる（家族重視か、社会で活躍か、芸術系か等）
- 「象山流評価」の★は、五行補完度・音・意味の総合判定

# 入力フォーマット

ユーザーは以下を渡します：

```
# 赤ちゃんの情報
苗字: 中井
性別: 男性
生年月日: 2026年7月15日
時刻: 不明（または「14時頃」）

# 命式（自動算出済み）
日干: ○（五行・陰陽）
- 年柱: ○○...
- 月柱: ○○...
- 日柱: ○○...

# 五行バランス
木:n 火:n 土:n 金:n 水:n（欠落: ○○）

# 調候用神
○・○

# 苗字の参考解析（あれば）
- 中: 土
- 井: 水

# 両親の希望（任意）
読み方: けんと等、漢字の希望、避けたい字 など
```
"""


def _name_key(surname: str, year: int, month: int, day: int,
              hour: Optional[int], sex: Sex, parent_wish: str) -> str:
    payload = {
        "s": surname, "y": year, "m": month, "d": day, "h": hour,
        "sex": sex, "w": parent_wish,
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _build_naming_payload(
    surname: str,
    year: int,
    month: int,
    day: int,
    hour: Optional[int],
    sex: Sex,
    parent_wish: str,
) -> str:
    m = calc_meishiki(year, month, day, hour)
    r = shozan_reading(m, year=year, month=month, day=day, sex=sex)

    lines = []
    lines.append("# 赤ちゃんの情報")
    lines.append(f"苗字: {surname}")
    lines.append(f"性別: {'男性' if sex == 'M' else '女性'}")
    lines.append(f"生年月日: {year}年{month}月{day}日")
    lines.append(f"時刻: {'不明' if hour is None else f'{hour}時頃'}")
    lines.append("")

    lines.append("# 命式")
    lines.append(f"日干: {m.nikkan}（{m.nikkan_gogyo}・{m.nikkan_yinyang}・{r.mikyojaku.label}）")
    for p in m.pillars:
        tg_t = p.tengan_tsuhensei or "（日主）"
        zokan = "・".join(f"{z}({t})" for z, t in zip(p.zokan, p.zokan_tsuhensei)) if p.zokan_tsuhensei else "・".join(p.zokan)
        lines.append(f"- {p.name}: {p.tengan}{p.chishi}（天干通変:{tg_t}、蔵干:{zokan}）")
    lines.append("")

    lines.append("# 五行バランス")
    gogyo_str = " ".join(f"{g}:{c}" for g, c in r.gogyo_counts.items())
    miss = "、".join(r.missing) if r.missing else "なし"
    lines.append(f"{gogyo_str}（欠落: {miss}）")
    lines.append("")

    lines.append("# 調候用神")
    lines.append(r.chouko or "標準テーブル外")
    lines.append("")

    lines.append("# 苗字の漢字（部首・字源から五行分類してください）")
    for ch in surname:
        lines.append(f"- {ch}")
    lines.append("")

    if parent_wish:
        lines.append("# 両親の希望")
        lines.append(parent_wish)

    return "\n".join(lines)


def generate_names(
    *,
    surname: str,
    year: int,
    month: int,
    day: int,
    hour: Optional[int] = None,
    sex: Sex = "M",
    parent_wish: str = "",
    use_cache: bool = True,
) -> str:
    """赤ちゃんの命名候補3-5個を生成する。"""
    key = _name_key(surname, year, month, day, hour, sex, parent_wish)
    cache_path = NAMING_CACHE_DIR / f"{key}.txt"
    if use_cache and cache_path.exists():
        log.info("naming cache hit: %s", key)
        return cache_path.read_text(encoding="utf-8")

    payload = _build_naming_payload(surname, year, month, day, hour, sex, parent_wish)
    log.info("naming cache miss, calling Claude (model=%s)", MODEL)

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        system=[
            {
                "type": "text",
                "text": NAMING_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": payload}],
    )

    log.info(
        "naming usage: input=%d, cache_read=%d, cache_create=%d, output=%d",
        response.usage.input_tokens,
        response.usage.cache_read_input_tokens or 0,
        response.usage.cache_creation_input_tokens or 0,
        response.usage.output_tokens,
    )

    text = next((b.text for b in response.content if b.type == "text"), "").strip()
    if not text:
        raise RuntimeError("Claude returned empty text")
    text += "\n\n---\n※ 最終的な命名は、ご両親の判断でお決めください。本提案は象山流命名学に基づく参考案です。"

    if use_cache:
        cache_path.write_text(text, encoding="utf-8")
    return text
