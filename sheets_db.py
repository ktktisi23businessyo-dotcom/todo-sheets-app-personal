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

# スプレッドシートURL（必須）
SHEET_URL = os.environ["SHEET_URL"]

# 認証ファイルパス
# Renderでは /etc/secrets/service_account.json
# ローカルでは secrets/service_account.json を使う
SERVICE_ACCOUNT_PATH = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS",
    "secrets/service_account.json"
)


def _get_credentials():
    if not os.path.exists(SERVICE_ACCOUNT_PATH):
        raise FileNotFoundError(
            f"Service account file not found: {SERVICE_ACCOUNT_PATH}"
        )

    with open(SERVICE_ACCOUNT_PATH, "r", encoding="utf-8") as f:
        info = json.load(f)

    if "private_key" not in info:
        raise ValueError("private_key not found in service account json")

    return Credentials.from_service_account_info(info, scopes=SCOPES)


def _get_worksheet():
    creds = _get_credentials()
    gc = gspread.authorize(creds)

    ss = gc.open_by_url(SHEET_URL)

    try:
        return ss.worksheet("todos")
    except gspread.exceptions.WorksheetNotFound:
        # なければ自動作成
        ws = ss.add_worksheet(title="todos", rows=100, cols=6)
        ws.append_row(["id", "title", "body", "due_date", "created_at", "updated_at"])
        return ws


def list_todos():
    ws = _get_worksheet()
    return ws.get_all_records()


def add_todo(title, body, due_date):
    ws = _get_worksheet()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    todo_id = str(uuid.uuid4())

    ws.append_row([
        todo_id,
        title,
        body,
        str(due_date),
        now,
        now,
    ])

    return todo_id


def update_todo(todo_id, new_title, new_body):
    ws = _get_worksheet()
    rows = ws.get_all_values()

    for i, row in enumerate(rows):
        if row and row[0] == todo_id:
            ws.update(f"B{i+1}", new_title)
            ws.update(f"C{i+1}", new_body)
            ws.update(f"F{i+1}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            break
