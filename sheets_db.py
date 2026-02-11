import os
import json
import uuid
from datetime import datetime, date

import gspread
from google.oauth2.service_account import Credentials

# =========================
# Config
# =========================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# RenderのEnvironmentで設定する
SHEET_URL = os.environ["SHEET_URL"]  # 例: https://docs.google.com/spreadsheets/d/xxxx/edit#gid=0
WORKSHEET_NAME = os.environ.get("WORKSHEET_NAME", "todos")

# Render Secret File のマウント先（Environmentで GOOGLE_APPLICATION_CREDENTIALS を設定するのが推奨）
SERVICE_ACCOUNT_PATH = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS",
    "/etc/secrets/service_account.json",
)

# =========================
# Internal helpers
# =========================
def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _get_worksheet():
    """
    Google Service Account JSON を Secret File から読み込み、
    指定したスプレッドシートの指定シート（タブ）を返す。
    """
    with open(SERVICE_ACCOUNT_PATH, "r", encoding="utf-8") as f:
        info = json.load(f)

    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    gc = gspread.authorize(creds)

    ss = gc.open_by_url(SHEET_URL)
    return ss.worksheet(WORKSHEET_NAME)


# =========================
# Public API (CRUD)
# =========================
def list_todos() -> list[dict]:
    """
    todosシートの全データを dict のリストで返す。
    1行目はヘッダーとして扱われる前提（get_all_records）。
    """
    ws = _get_worksheet()
    return ws.get_all_records()


def add_todo(title: str, body: str, due_date: date) -> str:
    """
    Todoを1件追加し、生成したid(UUID)を返す。
    """
    ws = _get_worksheet()

    todo_id = str(uuid.uuid4())
    now = _now_iso()

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
    """
    idで対象行を特定して更新する。
    シート構造（列）は以下を前提：
    A=id, B=title, C=body, D=due_date, E=created_at, F=updated_at
    """
    ws = _get_worksheet()
    all_rows = ws.get_all_values()

    # all_rows[0] がヘッダー、データは2行目以降
    target_row_index = None  # Google Sheets上の行番号（1始まり）
    for i in range(1, len(all_rows)):
        if len(all_rows[i]) > 0 and all_rows[i][0] == todo_id:
            target_row_index = i + 1
            break

    if target_row_index is None:
        raise ValueError(f"todo_id not found: {todo_id}")

    now = _now_iso()

    # created_at は既存値を保持したい
    existing_created_at = ""
    if len(all_rows[target_row_index - 1]) >= 5:
        existing_created_at = all_rows[target_row_index - 1][4]

    # B〜F を更新（A=idは変更しない）
    ws.update(
        f"B{target_row_index}:F{target_row_index}",
        [[
            title,
            body,
            due_date.isoformat(),
            existing_created_at,
            now,
        ]],
    )
