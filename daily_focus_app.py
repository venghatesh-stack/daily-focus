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
                    task_status TEXT NOT NULL,
                    UNIQUE (task_date, slot)
                );
            """)


def load_tasks_from_db(task_date):
    """Always load fresh data from DB"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT slot, task, task_status
                FROM daily_tasks
                WHERE task_date = %s
                ORDER BY slot;
            """, (task_date,))
            rows = cur.fetchall()

    data = {
        slot: {"task": DEFAULT_TASK, "status": DEFAULT_STATUS}
        for slot in range(1, TOTAL_SLOTS + 1)
    }

    for slot, task, status in rows:
        data[slot] = {"task": task, "status": status}

    return data


def save_tasks_to_db(task_date, tasks):
    with get_connection() as conn:
        with conn.cursor() as cur:
            for slot, data in tasks.items():
                task = data.get("task")
                status = data.get("status")

                # Skip defaults
                if not task or not status:
                    continue
                if task == DEFAULT_TASK and status == DEFAULT_STATUS:
                    continue

                cur.execute("""
                    INSERT INTO daily_tasks (task_date, slot, task, task_status)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (task_date, slot)
                    DO UPDATE SET
                        task = EXCLUDED.task,
                        task_status = EXCLUDED.task_status;
                """, (
                    task_date,
                    slot,
                    task,
                    status
                ))

# ==============================
# INIT
# ==============================
init_db()
# ==============================
# DATE HANDLING (CORRECT)
# ==============================
def on_date_change():
    selected = st.session_state.date_picker

    # Clear widget state
    for key in list(st.session_state.keys()):
        if key.startswith("task_") or key.startswith("status_"):
            del st.session_state[key]

    # Load DB data for selected date
    st.session_state.tasks_by_date[selected] = load_tasks_from_db(selected)


# Init containers
if "tasks_by_date" not in st.session_state:
    st.session_state.tasks_by_date = {}

if "date_picker" not in st.session_state:
    st.session_state.date_picker = date.today()

st.date_input(
    "Select day",
    key="date_picker",
    on_change=on_date_change
)

selected_date = st.session_state.date_picker

# Ensure data exists for selected date
if selected_date not in st.session_state.tasks_by_date:
    st.session_state.tasks_by_date[selected_date] = load_tasks_from_db(selected_date)

tasks = st.session_state.tasks_by_date[selected_date]
########################

# ==============================
# TIME SLOT LABEL
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
        tasks[slot]["task"] = st.text_input(
            "Task",
            value=tasks[slot]["task"],
            key=f"task_{selected_date}_{slot}",
            label_visibility="collapsed"
        )

    with col_status:
        tasks[slot]["status"] = st.selectbox(
            "Status",
            STATUSES,
            index=STATUSES.index(tasks[slot]["status"]),
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
        save_tasks_to_db(selected_date, tasks)

        # Reload from DB to guarantee consistency
        st.session_state.tasks_by_date[selected_date] = load_tasks_from_db(selected_date)


    st.success("Day saved successfully ✅")

with col_cancel:
    if st.button("❌ Cancel"):
       st.session_state.tasks_by_date[selected_date] = load_tasks_from_db(selected_date)
       for key in list(st.session_state.keys()):
            if key.startswith("task_") or key.startswith("status_"):
                del st.session_state[key]
        st.info("Changes discarded")





