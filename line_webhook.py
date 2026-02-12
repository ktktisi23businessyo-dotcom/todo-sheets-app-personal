import os
from dotenv import load_dotenv
load_dotenv()

import re
from dotenv import load_dotenv
load_dotenv()

from datetime import date, timedelta, datetime

from flask import Flask, request, abort

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 既存DB（Google Sheets）をそのまま利用
from sheets_db import list_todos

# ==========
# 環境変数
# ==========
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    raise RuntimeError(
        "LINE_CHANNEL_ACCESS_TOKEN / LINE_CHANNEL_SECRET が未設定です。"
    )

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

app = Flask(__name__)

# ==========
# 日付パース（日本語：2月14日派 最優先）
# ==========
def parse_date_jp(text: str, today: date | None = None) -> date | None:
    """
    対応（MVP）：
      - '2月14日'（最優先）
      - '2/14' or '2-14'
      - '今日', '明日'
      - '14日'（今月。過去なら翌月）
    """
    if today is None:
        today = date.today()

    t = (text or "").strip()

    # 1) 「2月14日」
    m = re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日", t)
    if m:
        month = int(m.group(1))
        day = int(m.group(2))
        y = today.year
        try:
            d = date(y, month, day)
        except ValueError:
            return None
        # 過去なら来年にスライド（自然な挙動）
        if d < today:
            try:
                d = date(y + 1, month, day)
            except ValueError:
                return None
        return d

    # 2) 「2/14」「2-14」
    m = re.search(r"(\d{1,2})\s*[\/\-]\s*(\d{1,2})", t)
    if m:
        month = int(m.group(1))
        day = int(m.group(2))
        y = today.year
        try:
            d = date(y, month, day)
        except ValueError:
            return None
        if d < today:
            try:
                d = date(y + 1, month, day)
            except ValueError:
                return None
        return d

    # 3) 今日/明日
    if re.search(r"(今日|きょう)", t):
        return today
    if re.search(r"(明日|あした)", t):
        return today + timedelta(days=1)

    # 4) 「14日」だけ（今月。過去なら翌月）
    m = re.search(r"(\d{1,2})\s*日", t)
    if m:
        day = int(m.group(1))
        y = today.year
        month = today.month
        try:
            d = date(y, month, day)
        except ValueError:
            return None
        if d < today:
            # 翌月へ
            month2 = 1 if month == 12 else month + 1
            y2 = y + 1 if month == 12 else y
            try:
                d = date(y2, month2, day)
            except ValueError:
                return None
        return d

    return None


def _normalize_due_date_str(s: str) -> str:
    """
    Sheetsのdue_date文字列を 'YYYY-MM-DD' に寄せる（壊れてても落ちにくい）
    """
    if not s:
        return ""
    s = str(s).strip()
    # すでにYYYY-MM-DDならそのまま
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s
    # Streamlit date_input の str(date) は YYYY-MM-DD なので基本ここは通らない想定
    # 念のため datetime 変換
    try:
        d = datetime.fromisoformat(s).date()
        return d.strftime("%Y-%m-%d")
    except Exception:
        return ""


def _priority_num(p: str) -> int:
    # 既存priorityが無い/空でもOK
    order = {"High": 3, "Medium": 2, "Low": 1}
    return order.get(str(p), 0)


def fetch_tasks_by_date(target: date):
    """
    Sheetsから全件取得→target日付で絞り込み
    """
    rows = list_todos()  # list of dict
    target_str = target.strftime("%Y-%m-%d")

    tasks = []
    for r in rows:
        due = _normalize_due_date_str(r.get("due_date", ""))
        if due == target_str:
            tasks.append(r)

    # priority desc → title asc（好みで変更可）
    tasks.sort(
        key=lambda x: (
            -_priority_num(x.get("priority", "")),
            str(x.get("title", "")),
        )
    )
    return tasks


def format_tasks_reply(target: date, tasks: list[dict]) -> str:
    dstr = target.strftime("%-m/%-d") if hasattr(target, "strftime") else str(target)
    # Windows互換が気になるなら %-m/%-d は避ける（Streamlit CloudはLinuxなのでOK）
    # 互換版:
    dstr = target.strftime("%m/%d").lstrip("0").replace("/0", "/")

    if not tasks:
        return f"予定は0件。\n空きだ。筋トレできる。"

    lines = [f"{len(tasks)}件"]
    for i, t in enumerate(tasks, start=1):
        pr = t.get("priority", "")
        pr_txt = f"({pr}) " if pr else ""
        title = str(t.get("title", "")).strip() or "（無題）"
        body = str(t.get("body", "")).strip()
        body_short = body[:40] + ("…" if len(body) > 40 else "")
        if body_short:
            lines.append(f"{i}) {pr_txt}{title}\n   - {body_short}")
        else:
            lines.append(f"{i}) {pr_txt}{title}")
    return "\n".join(lines)


def build_help_message() -> str:
    return (
        "日付がわからなかった。\n"
        "こう送ってね：\n"
        "・2月14日の予定\n"
        "・2/14の予定\n"
        "・今日の予定\n"
        "・明日の予定\n"
        "・14日の予定"
    )


# ==========
# LINE Webhook
# ==========
@app.route("/health", methods=["GET"])
def health():
    return "ok", 200


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK", 200


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = (event.message.text or "").strip()
    print("USER_ID:", event.source.user_id)

    target = parse_date_jp(text)
    if target is None:
        reply = build_help_message()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    tasks = fetch_tasks_by_date(target)
    reply = format_tasks_reply(target, tasks)
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
