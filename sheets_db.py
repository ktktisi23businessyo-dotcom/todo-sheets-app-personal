import os
import json
from datetime import datetime
import uuid

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_URL = os.environ["SHEET_URL"]
WORKSHEET_NAME = os.getenv("WORKSHEET_NAME", "todos")


def _pick_service_account_path() -> str:
    p = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if p and os.path.exists(p):
        return p

    candidates = [
        "/etc/secrets/service_account.json",
        "/etc/secrets/service-account.json",
        "/etc/secrets/sa.json",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c

    local = "secrets/service_account.json"
    if os.path.exists(local):
        return local

    raise FileNotFoundError(
        "Service account file not found. Tried: "
        + ", ".join([str(p)] + candidates + [local])
    )


def _get_credentials():
    path = _pick_service_account_path()
    with open(path, "r", encoding="utf-8") as f:
        info = json.load(f)

    if "private_key" not in info:
        raise ValueError("private_key not found in service account json")

    return Credentials.from_service_account_info(info, scopes=SCOPES)


def _get_worksheet():
    creds = _get_credentials()
    gc = gspread.authorize(creds)
    ss = gc.open_by_url(SHEET_URL)

    try:
        return ss.worksheet(WORKSHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        ws = ss.add_worksheet(title=WORKSHEET_NAME, rows=200, cols=6)
        ws.append_row(["id", "title", "body", "due_date", "created_at", "updated_at"])
        return ws


def list_todos():
    ws = _get_worksheet()
    return ws.get_all_records()


def add_todo(title, body, due_date):
    ws = _get_worksheet()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    todo_id = str(uuid.uuid4())
    ws.append_row([todo_id, title, body, str(due_date), now, now])
    return todo_id


def update_todo(todo_id, new_title, new_body, new_due_date):
    ws = _get_worksheet()
    rows = ws.get_all_values()

    for i, row in enumerate(rows):
        if row and row[0] == todo_id:
            ws.update(f"B{i+1}", new_title)
            ws.update(f"C{i+1}", new_body)
            ws.update(f"D{i+1}", str(new_due_date))
            ws.update(f"F{i+1}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return True

    raise ValueError("todo_id not found")


def delete_todo(todo_id):
    ws = _get_worksheet()
    rows = ws.get_all_values()

    for i, row in enumerate(rows):
        if row and row[0] == todo_id:
            # 行削除（ヘッダー行を消さない前提）
            ws.delete_rows(i + 1)
            return True

    raise ValueError("todo_id not found")
