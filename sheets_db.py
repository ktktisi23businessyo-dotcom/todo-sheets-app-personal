import os
import json
import uuid
from datetime import datetime, date

import gspread
from google.oauth2.service_account import Credentials

# ローカル用（Renderでは無視されてもOK）
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ローカルは .env で、Renderは Environment Variables で入る
SHEET_URL = os.getenv("SHEET_URL")
if not SHEET_URL:
    raise KeyError("SHEET_URL")

WORKSHEET_NAME = os.getenv("WORKSHEET_NAME", "todos")

# Renderでは Secret File を /etc/secrets/service_account.json にマウントする前提
# ローカルでは .env で GOOGLE_APPLICATION_CREDENTIALS=secrets/service_account.json を渡す
SERVICE_ACCOUNT_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/etc/secrets/service_account.json")

if not SERVICE_ACCOUNT_PATH:
    # ローカル優先パス（存在すれば）
    local_path = os.path.join("secrets", "service_account.json")
    SERVICE_ACCOUNT_PATH = local_path if os.path.exists(local_path) else "/etc/secrets/service_account.json"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _get_worksheet():
    with open(SERVICE_ACCOUNT_PATH, "r", encoding="utf-8") as f:
        info = json.load(f)

    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    gc = gspread.authorize(creds)

    ss = gc.open_by_url(SHEET_URL)
    return ss.worksheet(WORKSHEET_NAME)


def list_todos() -> list[dict]:
    ws = _get_worksheet()
    return ws.get_all_records()


def add_todo(title: str, body: str, due_date: date) -> str:
    ws = _get_worksheet()

    todo_id = str(uuid.uuid4())
    now = _now_iso()

    ws.append_row(
        [todo_id, title, body, due_date.isoformat(), now, now],
        value_input_option="USER_ENTERED",
    )
    return todo_id


def update_todo(todo_id: str, title: str, body: str, due_date: date) -> None:
    ws = _get_worksheet()
    all_rows = ws.get_all_values()

    target_row_index = None
    for i in range(1, len(all_rows)):  # 1行目はヘッダー
        if len(all_rows[i]) > 0 and all_rows[i][0] == todo_id:
            target_row_index = i + 1
            break

    if target_row_index is None:
        raise ValueError(f"todo_id not found: {todo_id}")

    now = _now_iso()
    existing_created_at = all_rows[target_row_index - 1][4] if len(all_rows[target_row_index - 1]) >= 5 else ""

    ws.update(
        f"B{target_row_index}:F{target_row_index}",
        [[title, body, due_date.isoformat(), existing_created_at, now]],
    )
