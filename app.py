import streamlit as st
import pandas as pd
from datetime import date, datetime

from sheets_db import add_todo, list_todos, update_todo

st.set_page_config(page_title="Todoリスト", layout="wide")
st.title("🧠 Todoリスト（Google Sheets保存）")

# --- ヘルパー ---
def to_df(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["id", "title", "body", "due_date", "created_at", "updated_at"])
    df = pd.DataFrame(rows)

    # 型を整える（表示と並び替えが楽になる）
    if "due_date" in df.columns:
        df["due_date"] = pd.to_datetime(df["due_date"], errors="coerce").dt.date
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    if "updated_at" in df.columns:
        df["updated_at"] = pd.to_datetime(df["updated_at"], errors="coerce")

    return df


# --- サイドバー：ページ切替 ---
page = st.sidebar.radio("メニュー", ["一覧", "新規登録", "編集"])

# --- データ取得 ---
rows = list_todos()
df = to_df(rows)

# 期限が近い順（空は最後）
if not df.empty:
    df["_due_sort"] = pd.to_datetime(df["due_date"], errors="coerce")
    df = df.sort_values(by="_due_sort", na_position="last").drop(columns=["_due_sort"])

# --- ページ：一覧 ---
if page == "一覧":
    st.subheader("📋 一覧")

    # ちょいUX：検索
    q = st.text_input("検索（タイトル/内容）", "")
    view_df = df.copy()
    if q and not view_df.empty:
        mask = (
            view_df["title"].astype(str).str.contains(q, case=False, na=False)
            | view_df["body"].astype(str).str.contains(q, case=False, na=False)
        )
        view_df = view_df[mask]

    # 期限切れ警告
    if not view_df.empty:
        overdue = view_df[view_df["due_date"].notna() & (view_df["due_date"] < date.today())]
        if not overdue.empty:
            st.warning(f"期限切れが {len(overdue)} 件あります（今日: {date.today().isoformat()}）")

    st.dataframe(
        view_df[["title", "body", "due_date", "updated_at"]] if not view_df.empty else view_df,
        use_container_width=True,
        hide_index=True,
    )

# --- ページ：新規登録 ---
elif page == "新規登録":
    st.subheader("➕ 新規登録")

    with st.form("create_form"):
        title = st.text_input("タイトル（必須）", placeholder="例：課題の提出")
        body = st.text_area("内容（必須）", placeholder="例：READMEを書いて、デプロイURLを貼る")
        due = st.date_input("期日（必須）", value=date.today())

        submitted = st.form_submit_button("登録する")

    if submitted:
        # バリデーション（UX：わかりやすく）
        if not title.strip():
            st.error("タイトルが空です。入力してください。")
            st.stop()
        if not body.strip():
            st.error("内容が空です。入力してください。")
            st.stop()

        todo_id = add_todo(title.strip(), body.strip(), due)
        st.success(f"登録しました ✅（id: {todo_id}）")
        st.info("左のメニューから「一覧」に戻って確認できます。")

# --- ページ：編集 ---
else:
    st.subheader("✏️ 編集")

    if df.empty:
        st.info("まだTodoがありません。先に「新規登録」から追加してください。")
        st.stop()

    # 編集対象を選ぶ（タイトルだけだと被るので、idも見せる）
    options = [
        f"{row['title']} ｜{row['due_date']}｜{row['id']}"
        for _, row in df.iterrows()
    ]
    selected = st.selectbox("編集するTodoを選択", options)

    # idを抜く
    selected_id = selected.split("｜")[-1].strip()

    target = df[df["id"] == selected_id].iloc[0]

    with st.form("edit_form"):
        new_title = st.text_input("タイトル（必須）", value=str(target["title"]))
        new_body = st.text_area("内容（必須）", value=str(target["body"]))
        new_due = st.date_input(
            "期日（必須）",
            value=target["due_date"] if pd.notna(target["due_date"]) else date.today(),
        )
        submitted = st.form_submit_button("更新する")

    if submitted:
        if not new_title.strip():
            st.error("タイトルが空です。入力してください。")
            st.stop()
        if not new_body.strip():
            st.error("内容が空です。入力してください。")
            st.stop()

        update_todo(selected_id, new_title.strip(), new_body.strip(), new_due)
        st.success("更新しました ✅")
        st.info("一覧に戻ると反映が見えます。")
