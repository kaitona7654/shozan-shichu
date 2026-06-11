"""LINE Bot webhook (FastAPI)。

起動:
  uvicorn app.main:app --host 0.0.0.0 --port 8000
環境変数(.envまたはシェル):
  LINE_CHANNEL_ACCESS_TOKEN
  LINE_CHANNEL_SECRET
"""
from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from linebot.v3 import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from .bazi import calc_meishiki
from .formatter import HELP_TEXT, format_meishiki_text
from .judgment import free_excerpt, generate as generate_judgment
from .parser import parse_birth
from .shozan import reading as shozan_reading

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("shichu_bot")

CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
ANTHROPIC_ENABLED = bool(os.getenv("ANTHROPIC_API_KEY"))
# フリーミアム: 既定で無料モード（性格傾向のみ返却）。FREEMIUM_MODE=false で全文返却（開発用）
FREEMIUM_MODE = os.getenv("FREEMIUM_MODE", "true").lower() in ("true", "1", "yes")

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    log.warning("LINE_CHANNEL_ACCESS_TOKEN / LINE_CHANNEL_SECRET が未設定です（/healthのみ動作）")
if not ANTHROPIC_ENABLED:
    log.warning("ANTHROPIC_API_KEY 未設定: 命式のみ返却（鑑定文生成はスキップ）")

parser = WebhookParser(CHANNEL_SECRET) if CHANNEL_SECRET else None
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN) if CHANNEL_ACCESS_TOKEN else None

app = FastAPI(title="Shichu Suimei LINE Bot")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/callback")
async def callback(request: Request, x_line_signature: str = Header(default="")):
    if parser is None or configuration is None:
        raise HTTPException(status_code=503, detail="LINE credentials not configured")

    body = (await request.body()).decode("utf-8")
    try:
        events = parser.parse(body, x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    with ApiClient(configuration) as api_client:
        messaging = MessagingApi(api_client)
        for event in events:
            if not isinstance(event, MessageEvent):
                continue
            if not isinstance(event.message, TextMessageContent):
                continue
            reply_texts = _handle_text(event.message.text)
            messaging.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=t) for t in reply_texts],
                )
            )
    return {"status": "ok"}


def _handle_text(text: str) -> list[str]:
    """ユーザー入力から返信メッセージ列を作る。LINEは1 replyで最大5件まで送れる。"""
    text = text.strip()
    if text in ("help", "ヘルプ", "使い方", "?", "？"):
        return [HELP_TEXT]
    birth = parse_birth(text)
    if birth is None:
        return [
            "生年月日を読み取れませんでした。\n"
            "例: 1985/5/20 10\n\n"
            "「ヘルプ」と送ると使い方を表示します。"
        ]
    try:
        m = calc_meishiki(birth.year, birth.month, birth.day, birth.hour)
    except Exception as e:
        log.exception("calc failed: %s", e)
        return ["命式の算出に失敗しました。日付をご確認ください。"]

    messages = [format_meishiki_text(m)]

    if ANTHROPIC_ENABLED:
        # 大運計算には性別が必要。未指定はデフォルト男性として進めつつ警告
        sex = birth.sex or "M"
        try:
            r = shozan_reading(
                m,
                year=birth.year,
                month=birth.month,
                day=birth.day,
                sex=sex,
            )
            judgment = generate_judgment(
                m, r, name=birth.name, sex=birth.sex
            )
            # フリーミアム: 無料ユーザーには性格セクション+完全鑑定案内のみ
            if FREEMIUM_MODE:
                judgment = free_excerpt(judgment)
                header = "🔮 象山流鑑定（無料版）"
            else:
                header = "🔮 象山流鑑定"
            if not birth.sex:
                header += "（性別未指定のため男性で算出）"
            messages.append(f"{header}\n\n{judgment}")
        except Exception as e:
            log.exception("judgment failed: %s", e)
            # 命式は返しているので致命的ではない
    return messages
