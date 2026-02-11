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

# スプレッドシートURL（環境変数から取得）
SHEET_URL = os.environ["SHEET_URL"]

# ローカル用パス
SERVICE_ACCOUNT_PATH = "secrets/service_account.json"


def _get_credentials():
    """
    Renderでは SERVICE_ACCOUNT_JSON を使う
    ローカルでは secrets/service_account.json を使う
    """

    # ===== Render用 =====
    if "SERVICE_ACCOUNT_JSON" in os.environ:
        print("DEBUG MODE: Using SERVICE_ACCOUNT_JSON from environment")
        info = json.loads(os.environ["SERVICE_ACCOUNT_JSON"])

        print("DEBUG SA_KEYS:", sorted(list(info.keys())))
        print("DEBUG HAS_PRIVATE_KEY:", "private_key" in info)
        print("DEBUG CLIENT_EMAIL:", info.get("client_email"))

        return Credentials.from_service_account_info(info, scopes=SCOPES)

    # ===== ローカル用 =====
    print("DEBUG MODE: Using local service_account.json")
    print("DEBUG SERVICE_ACCOUNT_PATH:", SERVICE_ACCOUNT_PATH)

    with open(SERVICE_ACCOUNT_PATH, "r", encoding="utf-8") as f:
        info = json.load(f)

    print("DEBUG SA_KEYS:", sorted(list(info.keys())))
    print("DEBUG HAS_PRIVATE_KEY:", "private_key" in info)
    print("DEBUG CLIENT_EMAIL:", info.get("client_email"))

    return Credentials.from_service_account_info(info, scopes=SCOPES)


def _get_worksheet():
    creds = _get_credentials()
    gc = gspread.authorize(creds)

    ss = gc.open_by_url(SHEET_URL)

    print("DEBUG WORKSHEETS:", [ws.title for ws in ss.worksheets()])

    return ss.worksheet("todos")


def list_todos():
    ws = _get_worksheet()
    rows = ws.get_all_records()
    return rows


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
