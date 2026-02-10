from datetime import date
from sheets_db import add_todo, list_todos

todo_id = add_todo("テスト", "スプレッドシートに保存できるか確認", date.today())
print("added:", todo_id)

rows = list_todos()
print("count:", len(rows))
print("last:", rows[-1] if rows else None)
