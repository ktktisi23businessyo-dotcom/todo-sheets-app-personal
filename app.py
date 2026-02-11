import streamlit as st
from datetime import date
import os
import json

from sheets_db import add_todo, list_todos, update_todo

st.set_page_config(page_title="Todoリスト", layout="wide")

st.title("🧠 Todoリスト（Googleスプレッドシート保存）")

# =============================
# 🔎 デバッグ表示（Render確認用）
# =============================
st.subheader("🔍 DEBUG INFO")

cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "(not set)")
st.write("GOOGLE_APPLICATION_CREDENTIALS =", cred_path)

st.write("SHEET_URL exists =", "SHEET_URL" in os.environ)

try:
    if cred_path != "(not set)" and os.path.exists(cred_path):
        with open(cred_path, "r", encoding="utf-8") as f:
            info = json.load(f)

        st.write("SA_KEYS =", sorted(info.keys()))
        st.write("HAS_PRIVATE_KEY =", "private_key" in info)
        st.write("CLIENT_EMAIL =", info.get("client_email"))
    else:
        st.write("Service account file not found.")
except Exception as e:
    st.write("Credential read error:", repr(e))

st.divider()

# =============================
# 📋 Todo一覧表示
# =============================

try:
    rows = list_todos()
except Exception as e:
    st.error(f"データ取得エラー: {e}")
    rows = []

st.subheader("📋 Todo一覧")

if rows:
    for row in rows:
        with st.expander(row["title"]):
            st.write("内容:", row["body"])
            st.write("期限:", row["due_date"])
else:
    st.info("まだタスクがありません")

st.divider()

# =============================
# ➕ 新規追加フォーム
# =============================

st.subheader("➕ 新規タスク追加")

with st.form("add_form"):
    title = st.text_input("タイトル")
    body = st.text_area("内容")
    due = st.date_input("期限", value=date.today())

    submitted = st.form_submit_button("追加")

    if submitted:
        try:
            add_todo(title, body, due)
            st.success("追加しました！")
            st.rerun()
        except Exception as e:
            st.error(f"追加エラー: {e}")
