"""
app.py - Flask 主程式 / LINE Webhook 入口

端點：
  POST /webhook      LINE Messaging API Webhook
  GET  /health       健康檢查（供 Keep-Alive 服務 ping）
  POST /daily-report Render Cron Job 觸發每日報告
"""
import logging
import os

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
_SECRET       = os.environ.get("LINE_CHANNEL_SECRET", "")

_configuration = Configuration(access_token=_ACCESS_TOKEN)
_handler       = WebhookHandler(_SECRET)


# ── Webhook ───────────────────────────────────────────────────────────────────

@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature", "")
    body      = request.get_data(as_text=True)
    logger.debug(f"Webhook body: {body[:200]}")
    try:
        _handler.handle(body, signature)
    except InvalidSignatureError:
        logger.warning("Invalid LINE signature")
        abort(400)
    return "OK"


@_handler.add(MessageEvent, message=TextMessageContent)
def on_message(event):
    from commands import process_command

    text    = event.message.text.strip()
    user_id = event.source.user_id
    logger.info(f"[{user_id}] ← {text!r}")

    reply = process_command(text, user_id)
    if reply:
        with ApiClient(_configuration) as api_client:
            MessagingApi(api_client).reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply[:5000])],  # LINE 上限 5000 字
                )
            )


# ── 健康檢查 ──────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return "OK", 200


# ── 每日報告觸發端點（Render Cron Job 呼叫）──────────────────────────────────

@app.route("/daily-report", methods=["GET", "POST"])
def daily_report():
    # 簡單安全驗證：需帶正確的 secret query param 或 header
    secret = os.environ.get("CRON_SECRET", "")
    incoming = request.args.get("secret", "") or request.headers.get("X-Cron-Secret", "")
    if secret and incoming != secret:
        abort(403)

    from scheduler_job import run_daily_report
    result = run_daily_report()
    return jsonify({"status": "ok", "result": result})


# ── 啟動 ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # 本機測試時可選擇啟動 APScheduler
    import os
    if os.environ.get("USE_APSCHEDULER", "false").lower() == "true":
        from scheduler_job import start_scheduler
        start_scheduler()

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
