import gspread
from google.oauth2.service_account import Credentials

SERVICE_ACCOUNT_FILE = "secrets/service_account.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def main():
    # 認証
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES,
    )
    gc = gspread.authorize(creds)

    # 対象スプレッドシートのURL
    sheet_url = "https://docs.google.com/spreadsheets/d/1qm2cpeQ0_5VUFlWZomolY1dwpxRAX2alx_2CtJN50Is/edit?gid=0#gid=0"
    # スプレッドシートを開く
    ss = gc.open_by_url(sheet_url)

    # ★ 今あるタブ名を全部表示（デバッグ用・超重要）
    print("WORKSHEETS:", [ws.title for ws in ss.worksheets()])

    # ★ Todo用シート（タブ名は完全一致）
    sheet = ss.worksheet("todos")

    # ヘッダー確認
    header = sheet.row_values(1)
    print("HEADER:", header)

    # データ確認（先頭5行だけ）
    rows = sheet.get_all_values()
    print("ROWS:", rows[:5])

if __name__ == "__main__":
    main()

