import os
import psycopg2
import streamlit as st
from datetime import date

# ==============================
# PAGE SETUP
# ==============================
st.set_page_config(page_title="Daily Focus", layout="wide")
st.title("🗓️ Daily Focus")

# ==============================
# DATABASE CONFIG
# ==============================
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    st.error("DATABASE_URL is not set in Streamlit Secrets.")
    st.stop()


@st.cache_resource
def get_connection():
    """
    Cached connection for Streamlit Cloud.
    Works correctly with Supabase Shared Pooler (IPv4).
    """
    conn = psycopg2.connect(
        DATABASE_URL,
        sslmode="require"
    )
    conn.autocommit = True
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_tasks (
            id SERIAL PRIMARY KEY,
            task_date DATE NOT NULL,
            slot INTEGER NOT NULL,
            task TEXT NOT NULL,
            status TEXT NOT NULL,
            UNIQUE (task_date, slot)
        );
    """)

    cur.close()


def save_task(task_date, slot, task, status):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO daily_tasks (task_date, slot, task, status)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (task_date, slot)
        DO UPDATE SET
            task = EXCLUDED.task,
            status = EXCLUDED.status;
    """, (task_date, slot, task, status))

    cur.close()


def load_tasks(task_date):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT slot, task, status
        FROM daily_tasks
        WHERE task_date = %s
        ORDER BY slot;
    """, (task_date,))

    rows = cur.fetchall()
    cur.close()

    return {slot: {"task": task, "status": status} for slot, task, status in rows}


# ==============================
# INITIALIZE DATABASE
# ==============================
init_db()

# ==============================
# UI
# ==============================
selected_date = st.date_input("Select day", value=date.today())

st.subheader("Top 5 things for the day")

statuses = ["Not Started", "In Progress", "Done"]

existing_data = load_tasks(selected_date)

for slot in range(1, 6):
    col1, col2 = st.columns([4, 2])

    with col1:
        task = st.text_input(
            f"Task {slot}",
            value=existing_data.get(slot, {}).get("task", ""),
            key=f"task_{selected_date}_{slot}"
        )

    with col2:
        status = st.selectbox(
            "Status",
            statuses,
            index=statuses.index(
                existing_data.get(slot, {}).get("status", "Not Started")
            ),
            key=f"status_{selected_date}_{slot}"
        )

    if task.strip():
        save_task(selected_date, slot, task.strip(), status)

st.success("Saved automatically ✅")
