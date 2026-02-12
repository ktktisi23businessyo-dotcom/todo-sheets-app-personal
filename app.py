import streamlit as st
import pandas as pd
from datetime import date, datetime

from dotenv import load_dotenv
load_dotenv()

from sheets_db import add_todo, list_todos, update_todo, delete_todo

st.set_page_config(page_title="Todoリスト", layout="wide")

st.title("🧠 Todoリスト（Googleスプレッドシート保存）")

# =========================
# 定数
# =========================
PRIORITY_CHOICES = ["High", "Medium", "Low"]
PRIORITY_ORDER = {"High": 3, "Medium": 2, "Low": 1}

# =========================
# ユーティリティ
# =========================
def _to_df(rows):
    # priority列を追加した版
    base_cols = ["id", "title", "body", "due_date", "priority", "created_at", "updated_at"]

    if not rows:
        return pd.DataFrame(columns=base_cols)

    df = pd.DataFrame(rows)

    # 欠けてても落ちないように（旧シートでも動く）
    for c in base_cols:
        if c not in df.columns:
            df[c] = ""

    # due_dateを日付に寄せる（変換できないものはNaT）
    df["due_date"] = pd.to_datetime(df["due_date"], errors="coerce").dt.date
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df["updated_at"] = pd.to_datetime(df["updated_at"], errors="coerce")

    # priority正規化（想定外は空に）
    df["priority"] = df["priority"].fillna("").astype(str)
    df.loc[~df["priority"].isin(PRIORITY_CHOICES), "priority"] = ""

    return df


def _fmt_dt(x):
    if pd.isna(x):
        return ""
    if isinstance(x, (datetime, pd.Timestamp)):
        return x.strftime("%Y-%m-%d %H:%M")
    return str(x)


def _priority_num(p: str) -> int:
    return PRIORITY_ORDER.get(str(p), 0)

# =========================
# データ取得
# =========================
try:
    rows = list_todos()
    df = _to_df(rows)
except Exception as e:
    st.error(f"データ取得エラー: {e}")
    st.stop()

# =========================
# 画面：上段（新規登録）
# =========================
with st.container(border=True):
    st.subheader("➕ 新規登録")

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        new_title = st.text_input("タイトル", placeholder="例：提出用READMEを仕上げる")
        new_body = st.text_area("内容", placeholder="例：手順と公開URL、環境変数の説明を書く", height=100)
    with c2:
        new_due = st.date_input("期日", value=date.today())
    with c3:
        new_priority = st.selectbox("重要度", PRIORITY_CHOICES, index=1)  # Medium default
        st.write("")
        add_clicked = st.button("追加する", type="primary", use_container_width=True)

    if add_clicked:
        if not new_title.strip():
            st.warning("タイトルは必須です。")
        else:
            try:
                add_todo(new_title.strip(), new_body.strip(), new_due, new_priority)
                st.success("追加しました！")
                st.rerun()
            except Exception as e:
                st.error(f"追加エラー: {e}")

st.write("")

# =========================
# 画面：中段（一覧）
# =========================
with st.container(border=True):
    st.subheader("📋 一覧")

    # フィルタ
    f1, f2, f3, f4, f5 = st.columns([2, 1, 1, 1, 1])
    with f1:
        q = st.text_input("検索（タイトル/内容）", placeholder="キーワードで絞り込み")
    with f2:
        show_mode = st.selectbox("表示", ["すべて", "期限ありのみ", "期限なしのみ"])
    with f3:
        pr_filter = st.selectbox("重要度", ["すべて"] + PRIORITY_CHOICES)
    with f4:
        sort_mode = st.selectbox("並び順", ["更新が新しい順", "期限が近い順", "重要度が高い順", "タイトル順"])
    with f5:
        st.write("")
        reload_clicked = st.button("再読み込み", use_container_width=True)

    if reload_clicked:
        st.rerun()

    view = df.copy()

    # 検索
    if q.strip():
        key = q.strip().lower()
        view = view[
            view["title"].fillna("").str.lower().str.contains(key)
            | view["body"].fillna("").str.lower().str.contains(key)
        ]

    # 表示モード
    if show_mode == "期限ありのみ":
        view = view[view["due_date"].notna()]
    elif show_mode == "期限なしのみ":
        view = view[view["due_date"].isna()]

    # priorityフィルタ
    if pr_filter != "すべて":
        view = view[view["priority"] == pr_filter]

    # 並び順
    if sort_mode == "更新が新しい順":
        view = view.sort_values("updated_at", ascending=False)
    elif sort_mode == "期限が近い順":
        # due_dateがNaTのものは最後へ
        view = view.sort_values(["due_date", "updated_at"], ascending=[True, False], na_position="last")
    elif sort_mode == "重要度が高い順":
        view = view.copy()
        view["priority_num"] = view["priority"].apply(_priority_num)
        view = view.sort_values(["priority_num", "due_date", "updated_at"], ascending=[False, True, False], na_position="last")
        view = view.drop(columns=["priority_num"])
    else:
        view = view.sort_values("title", ascending=True)

    # 表示用に整形（編集には元データを使う）
    display = view.copy()
    display["created_at"] = display["created_at"].apply(_fmt_dt)
    display["updated_at"] = display["updated_at"].apply(_fmt_dt)
    display["due_date"] = display["due_date"].astype("string")

    # 選択のためのindexを付与
    display = display.reset_index(drop=True)
    st.caption("行を選んで下の「編集」で更新できます。")

    # data_editor で行選択（チェック）
    display.insert(0, "選択", False)

    edited = st.data_editor(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "選択": st.column_config.CheckboxColumn("選択", width="small"),
            "id": st.column_config.TextColumn("id", disabled=True, width="medium"),
            "title": st.column_config.TextColumn("タイトル", width="large"),
            "body": st.column_config.TextColumn("内容", width="large"),
            "due_date": st.column_config.TextColumn("期日(YYYY-MM-DD)", width="medium"),
            "priority": st.column_config.SelectboxColumn("重要度", options=PRIORITY_CHOICES, width="small"),
            "created_at": st.column_config.TextColumn("作成", disabled=True, width="medium"),
            "updated_at": st.column_config.TextColumn("更新", disabled=True, width="medium"),
        },
        disabled=["id", "created_at", "updated_at"],
        key="table",
    )

st.write("")

# =========================
# 画面：下段（編集）
# =========================
with st.container(border=True):
    st.subheader("✏️ 編集（選択した1件を更新 / 削除）")

    # 選択行を取得
    selected = edited[edited["選択"] == True]  # noqa: E712
    if len(selected) == 0:
        st.info("一覧で1件選択してください。")
        st.stop()
    if len(selected) > 1:
        st.warning("編集は1件ずつです。1件だけ選択してください。")
        st.stop()

    row = selected.iloc[0].to_dict()

    # 入力フォーム
    e1, e2, e3 = st.columns([2, 1, 1])
    with e1:
        etitle = st.text_input("タイトル（編集）", value=row.get("title", ""))
        ebody = st.text_area("内容（編集）", value=row.get("body", ""), height=140)
    with e2:
        # due_date が空文字のことがあるのでケア
        raw_due = row.get("due_date", "")
        try:
            if raw_due:
                due_val = datetime.strptime(str(raw_due), "%Y-%m-%d").date()
            else:
                due_val = date.today()
        except Exception:
            due_val = date.today()

        edue = st.date_input("期日（編集）", value=due_val)

    with e3:
        raw_pr = row.get("priority", "")
        if raw_pr not in PRIORITY_CHOICES:
            raw_pr = "Medium"
        epriority = st.selectbox("重要度（編集）", PRIORITY_CHOICES, index=PRIORITY_CHOICES.index(raw_pr))
        st.write("")
        save_clicked = st.button("更新する", type="primary", use_container_width=True)
        delete_clicked = st.button("削除する", type="secondary", use_container_width=True)

    if save_clicked:
        if not etitle.strip():
            st.warning("タイトルは必須です。")
        else:
            try:
                update_todo(row["id"], etitle.strip(), ebody.strip(), edue, epriority)
                st.success("更新しました！")
                st.rerun()
            except Exception as e:
                st.error(f"更新エラー: {e}")

    if delete_clicked:
        try:
            delete_todo(row["id"])
            st.success("削除しました！")
            st.rerun()
        except Exception as e:
            st.error(f"削除エラー: {e}")
