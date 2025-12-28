import os
import psycopg2
import streamlit as st
from datetime import date

# ==============================
# PAGE SETUP
# ==============================
st.set_page_config(page_title="Daily Focus", layout="wide")
st.title("🗓️ Daily Focus")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    st.error("DATABASE_URL is not set in Streamlit Secrets.")
    st.stop()

# ==============================
# DATABASE HELPERS (POOLER SAFE)
# ==============================
def get_connection():
    conn = psycopg2.connect(
        DATABASE_URL,
        sslmode="require",
        connect_timeout=5
    )
    conn.autocommit = True
    return conn


def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
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


def load_tasks_from_db(task_date):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT slot, task, status
                FROM daily_tasks
                WHERE task_date = %s
                ORDER BY slot;
            """, (task_date,))
            rows = cur.fetchall()

    data = {}
    for slot in range(1, 6):
        data[slot] = {"task": "", "status": "Not Started"}

    for slot, task, status in rows:
        data[slot] = {"task": task, "status": status}

    return data


def save_tasks_to_db(task_date, tasks):
    with get_connection() as conn:
        with conn.cursor() as cur:
            for slot, data in tasks.items():
                if data["task"].strip():
                    cur.execute("""
                        INSERT INTO daily_tasks (task_date, slot, task, status)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (task_date, slot)
                        DO UPDATE SET
                            task = EXCLUDED.task,
                            status = EXCLUDED.status;
                    """, (
                        task_date,
                        slot,
                        data["task"].strip(),
                        data["status"]
                    ))

# ==============================
# INIT
# ==============================
init_db()

# ==============================
# SESSION STATE HELPERS
# ==============================
def load_date_into_state(task_date):
    st.session_state.tasks = load_tasks_from_db(task_date)


# ==============================
# DATE PICKER
# ==============================
selected_date = st.date_input(
    "Select day",
    value=st.session_state.get("selected_date", date.today())
)

# Detect date change
if "selected_date" not in st.session_state:
    st.session_state.selected_date = selected_date
    load_date_into_state(selected_date)

elif selected_date != st.session_state.selected_date:
    st.session_state.selected_date = selected_date
    load_date_into_state(selected_date)

# ==============================
# UI
# ==============================
st.subheader("Top 5 things for the day")

statuses = ["Not Started", "In Progress", "Done"]

for slot in range(1, 6):
    col1, col2 = st.columns([4, 2])

    with col1:
        st.session_state.tasks[slot]["task"] = st.text_input(
            f"Task {slot}",
            value=st.session_state.tasks[slot]["task"],
            key=f"task_{slot}"
        )

    with col2:
        st.session_state.tasks[slot]["status"] = st.selectbox(
            "Status",
            statuses,
            index=statuses.index(st.session_state.tasks[slot]["status"]),
            key=f"status_{slot}"
        )

st.divider()

# ==============================
# ACTION BUTTONS
# ==============================
col_save, col_cancel = st.columns([1, 1])

with col_save:
    if st.button("💾 Save", type="primary"):
        save_tasks_to_db(selected_date, st.session_state.tasks)
        st.success("Saved successfully ✅")

with col_cancel:
    if st.button("❌ Cancel"):
        load_date_into_state(selected_date)
        st.info("Changes discarded")

