import os
import re
from datetime import date, timedelta, datetime

from dotenv import load_dotenv
load_dotenv()

from linebot import LineBotApi
from linebot.models import TextSendMessage

from sheets_db import list_todos

# ==========
# 環境変数
# ==========
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_USER_ID = os.environ.get("LINE_USER_ID", "")

if not LINE_CHANNEL_ACCESS_TOKEN:
    raise RuntimeError("LINE_CHANNEL_ACCESS_TOKEN が未設定です")
if not LINE_USER_ID:
    raise RuntimeError("LINE_USER_ID が未設定です（Push通知先）")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)


# ==========
# 日付正規化（表記ゆれに強い）
# ==========
def _normalize_due_date_str(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    if not s:
        return ""

    # 2026/2/12 → 2026-2-12
    s = s.replace("/", "-")

    # YYYY-MM-DD（1桁月日も許容）
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        y, mo, da = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mo, da).strftime("%Y-%m-%d")
        except ValueError:
            return ""

    # 2026-02-12 00:00:00 や ISO形式
    try:
        s2 = s.replace(" ", "T")
        d = datetime.fromisoformat(s2).date()
        return d.strftime("%Y-%m-%d")
    except Exception:
        return ""

    return ""


def _priority_num(p: str) -> int:
    order = {"High": 3, "Medium": 2, "Low": 1}
    return order.get(str(p), 0)


# ==========
# 指定日のタスク取得
# ==========
def fetch_tasks_for_day(target: date):
    rows = list_todos()
    target_str = target.strftime("%Y-%m-%d")

    tasks = []
    for r in rows:
        due = _normalize_due_date_str(r.get("due_date", ""))
        if due == target_str:
            tasks.append(r)

    tasks.sort(
        key=lambda x: (
            -_priority_num(x.get("priority", "")),
            str(x.get("title", "")),
        )
    )
    return tasks


# ==========
# メッセージ整形
# ==========
def format_remind_message(target: date, tasks: list[dict], label: str) -> str:
    dstr = target.strftime("%m/%d").lstrip("0").replace("/0", "/")

    if not tasks:
        return f"【{label} {dstr}】締切タスクは0件。"

    lines = [f"【{label} {dstr}】{len(tasks)}件"]
    for i, t in enumerate(tasks, start=1):
        pr = t.get("priority", "")
        pr_txt = f"({pr}) " if pr else ""
        title = str(t.get("title", "")).strip() or "（無題）"
        lines.append(f"{i}) {pr_txt}{title}")

    return "\n".join(lines)


# ==========
# Push送信
# ==========
def push(text: str):
    line_bot_api.push_message(
        LINE_USER_ID,
        TextSendMessage(text=text)
    )


# ==========
# 実行
# ==========
def main():
    today = date.today()
    tomorrow = today + timedelta(days=1)

    today_tasks = fetch_tasks_for_day(today)
    tomorrow_tasks = fetch_tasks_for_day(tomorrow)

    msg_today = format_remind_message(today, today_tasks, "今日")
    msg_tomorrow = format_remind_message(tomorrow, tomorrow_tasks, "明日")

    push(msg_today + "\n\n" + msg_tomorrow)


if __name__ == "__main__":
    main()
