import streamlit as st
from datetime import date

from sheets_db import add_todo, list_todos, update_todo

st.set_page_config(page_title="Todoリスト", layout="wide")
st.title("🧠 Todoリスト（Googleスプレッドシート保存）")

st.subheader("📋 Todo一覧")

try:
    rows = list_todos()
except Exception as e:
    st.error(f"データ取得エラー: {e}")
    rows = []

if rows:
    for row in rows:
        with st.expander(row["title"]):
            st.write("内容:", row.get("body", ""))
            st.write("期限:", row.get("due_date", ""))

            st.markdown("### ✏️ 編集")
            new_title = st.text_input("タイトル（編集）", value=row["title"], key=f"t_{row['id']}")
            new_body = st.text_area("内容（編集）", value=row.get("body", ""), key=f"b_{row['id']}")

            if st.button("更新", key=f"u_{row['id']}"):
                try:
                    update_todo(row["id"], new_title, new_body)
                    st.success("更新しました！")
                    st.rerun()
                except Exception as e:
                    st.error(f"更新エラー: {e}")
else:
    st.info("まだタスクがありません")

st.divider()

st.subheader("➕ 新規タスク追加")

with st.form("add_form"):
    title = st.text_input("タイトル")
    body = st.text_area("内容")
    due = st.date_input("期限", value=date.today())
    submitted = st.form_submit_button("追加")

    if submitted:
        if not title.strip():
            st.warning("タイトルを入力してください")
        else:
            try:
                add_todo(title.strip(), body.strip(), due)
                st.success("追加しました！")
                st.rerun()
            except Exception as e:
                st.error(f"追加エラー: {e}")
