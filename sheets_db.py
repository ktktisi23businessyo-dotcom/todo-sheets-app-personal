import os
import uuid
from datetime import datetime, date

import gspread
from google.oauth2.service_account import Credentials

SERVICE_ACCOUNT_FILE = "secrets/service_account.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ↓あなたのスプレッドシートURLに合わせておく（test_sheets.pyと同じでOK）
SHEET_URL = "https://docs.google.com/spreadsheets/d/1qm2cpeQ0_5VUFlWZomolY1dwpxRAX2alx_2CtJN50Is/edit?gid=0#gid=0"
WORKSHEET_NAME = "todos"


def _get_worksheet():
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES,
    )
    gc = gspread.authorize(creds)
    ss = gc.open_by_url(SHEET_URL)

    print("DEBUG SHEET_URL:", SHEET_URL)
    print("DEBUG WORKSHEETS:", [ws.title for ws in ss.worksheets()])

    return ss.worksheet(WORKSHEET_NAME)



def list_todos() -> list[dict]:
    ws = _get_worksheet()
    rows = ws.get_all_records()  # 1行目をヘッダーとしてdict化
    # due_dateは文字列で入ってる前提。空なら空。
    return rows


def add_todo(title: str, body: str, due_date: date) -> str:
    ws = _get_worksheet()
    now = datetime.now().isoformat(timespec="seconds")

    todo_id = str(uuid.uuid4())
    ws.append_row(
        [
            todo_id,
            title,
            body,
            due_date.isoformat(),  # YYYY-MM-DD
            now,
            now,
        ],
        value_input_option="USER_ENTERED",
    )
    return todo_id


def update_todo(todo_id: str, title: str, body: str, due_date: date) -> None:
    ws = _get_worksheet()
    all_rows = ws.get_all_values()

    # all_rows[0] がヘッダー、データは2行目以降
    target_row_index = None  # 1始まり（Google Sheetsの行番号）
    for i in range(1, len(all_rows)):
        if len(all_rows[i]) > 0 and all_rows[i][0] == todo_id:
            target_row_index = i + 1
            break

    if target_row_index is None:
        raise ValueError(f"todo_id not found: {todo_id}")

    now = datetime.now().isoformat(timespec="seconds")

    # 列: A=id, B=title, C=body, D=due_date, E=created_at, F=updated_at
    ws.update(f"B{target_row_index}:F{target_row_index}", [[
        title,
        body,
        due_date.isoformat(),
        all_rows[target_row_index - 1][4] if len(all_rows[target_row_index - 1]) >= 5 else "",
        now,
    ]])
