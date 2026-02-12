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

# 新スキーマ（priority追加）
HEADERS = ["id", "title", "body", "due_date", "priority", "created_at", "updated_at"]


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


def _ensure_headers(ws):
    """
    既存シートが旧スキーマでも、ヘッダーにpriority列を追加して整合させる。
    既にHEADERSなら何もしない。
    """
    row1 = ws.row_values(1)
    if not row1:
        ws.append_row(HEADERS)
        return

    # 先頭行がヘッダーだと仮定（運用前提）
    if row1 == HEADERS:
        return

    # 旧ヘッダーの可能性
    # 旧: ["id","title","body","due_date","created_at","updated_at"]
    # 新: priorityを due_date の後ろに入れる
    if "priority" not in row1:
        # 列挿入（5列目=E列にpriorityを入れる）
        # gspreadのinsert_colsは「列配列」を渡す形式
        # ここではヘッダー行だけ追加して、データ行は空でOK（後で編集で埋める）
        ws.insert_cols([["priority"]], col=5)
        # updated_at列などが右にずれるので、ヘッダー行を正しい並びに揃える
        ws.update("A1:G1", [HEADERS])
        return

    # priorityはあるが順序がズレてる場合は揃える（軽く保守）
    # データ並び替えまではしない（MVP）
    ws.update(f"A1:{chr(64+len(HEADERS))}1", [HEADERS])


def _get_worksheet():
    creds = _get_credentials()
    gc = gspread.authorize(creds)
    ss = gc.open_by_url(SHEET_URL)

    try:
        ws = ss.worksheet(WORKSHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        ws = ss.add_worksheet(title=WORKSHEET_NAME, rows=200, cols=len(HEADERS))
        ws.append_row(HEADERS)
        return ws

    _ensure_headers(ws)
    return ws


def list_todos():
    ws = _get_worksheet()
    return ws.get_all_records()


def add_todo(title, body, due_date, priority):
    ws = _get_worksheet()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    todo_id = str(uuid.uuid4())
    ws.append_row([todo_id, title, body, str(due_date), str(priority), now, now])
    return todo_id


def update_todo(todo_id, new_title, new_body, new_due_date, new_priority):
    ws = _get_worksheet()
    rows = ws.get_all_values()

    for i, row in enumerate(rows):
        if row and row[0] == todo_id:
            # 新スキーマ:
            # A:id  B:title  C:body  D:due_date  E:priority  F:created_at  G:updated_at
            r = i + 1
            ws.update(f"B{r}", new_title)
            ws.update(f"C{r}", new_body)
            ws.update(f"D{r}", str(new_due_date))
            ws.update(f"E{r}", str(new_priority))
            ws.update(f"G{r}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
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
