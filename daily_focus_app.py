import os
import psycopg2
import streamlit as st
from datetime import date, datetime, timedelta

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
# CONSTANTS
# ==============================
TOTAL_SLOTS = 48
DEFAULT_TASK = "Not Planned"
DEFAULT_STATUS = "Not Planned"
STATUSES = ["Not Planned", "Planned", "In Progress", "Done"]

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
    """Load tasks from DB. If none exist, return defaults."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT slot, task, status
                FROM daily_tasks
                WHERE task_date = %s
                ORDER BY slot;
            """, (task_date,))
            rows = cur.fetchall()

    # Default 48 slots
    data = {
        slot: {"task": DEFAULT_TASK, "status": DEFAULT_STATUS}
        for slot in range(1, TOTAL_SLOTS + 1)
    }

    # Override with DB data if present
    for slot, task, status in rows:
        data[slot] = {"task": task, "status": status}

    return data


def save_tasks_to_db(task_date, tasks):
    with get_connection() as conn:
        with conn.cursor() as cur:
            for slot, data in tasks.items():
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
                    data["task"],
                    data["status"]
                ))

# ==============================
# INIT
# ==============================
init_db()

# ==============================
# DATE HANDLING (CRITICAL)
# ==============================
selected_date = st.date_input(
    "Select day",
    value=st.session_state.get("selected_date", date.today())
)

# Date change → reload from DB
if st.session_state.get("selected_date") != selected_date:
    st.session_state.selected_date = selected_date
    st.session_state.tasks = load_tasks_from_db(selected_date)

# First load
if "tasks" not in st.session_state:
    st.session_state.tasks = load_tasks_from_db(selected_date)

# ==============================
# TIME SLOT LABELS
# ==============================
def slot_label(slot):
    start = datetime.combine(date.today(), datetime.min.time()) + timedelta(minutes=(slot - 1) * 30)
    end = start + timedelta(minutes=30)
    return f"{start.strftime('%H:%M')} – {end.strftime('%H:%M')}"

# ==============================
# UI
# ==============================
st.subheader("Daily Plan (30-minute slots)")

for slot in range(1, TOTAL_SLOTS + 1):
    col_time, col_task, col_status = st.columns([2, 6, 2])

    with col_time:
        st.markdown(f"**{slot_label(slot)}**")

    with col_task:
        st.session_state.tasks[slot]["task"] = st.text_input(
            "Task",
            value=st.session_state.tasks[slot]["task"],
            key=f"task_{selected_date}_{slot}",
            label_visibility="collapsed"
        )

    with col_status:
        st.session_state.tasks[slot]["status"] = st.selectbox(
            "Status",
            STATUSES,
            index=STATUSES.index(st.session_state.tasks[slot]["status"]),
            key=f"status_{selected_date}_{slot}",
            label_visibility="collapsed"
        )

st.divider()

# ==============================
# ACTION BUTTONS
# ==============================
col_save, col_cancel = st.columns(2)

with col_save:
    if st.button("💾 Save Day", type="primary"):
        save_tasks_to_db(selected_date, st.session_state.tasks)
        st.success("Day saved successfully ✅")

with col_cancel:
    if st.button("❌ Cancel"):
        st.session_state.tasks = load_tasks_from_db(selected_date)
        st.info("Changes discarded")
