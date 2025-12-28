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
    st.error("DATABASE_URL is not set")
    st.stop()

TOTAL_SLOTS = 48
DEFAULT_TASK = "Not Planned"
DEFAULT_STATUS = "Not Planned"
STATUSES = ["Not Planned", "Planned", "In Progress", "Done"]

# ==============================
# DB
# ==============================
def get_connection():
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    conn.autocommit = True
    return conn


def load_tasks(task_date):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT slot, task, task_status
                FROM daily_tasks
                WHERE task_date = %s
            """, (task_date,))
            rows = cur.fetchall()

    data = {
        i: {"task": DEFAULT_TASK, "status": DEFAULT_STATUS}
        for i in range(1, TOTAL_SLOTS + 1)
    }

    for slot, task, status in rows:
        data[slot] = {"task": task, "status": status}

    return data


def save_tasks(task_date, tasks):
    with get_connection() as conn:
        with conn.cursor() as cur:
            for slot, v in tasks.items():
                if v["task"] == DEFAULT_TASK and v["status"] == DEFAULT_STATUS:
                    continue
                cur.execute("""
                    INSERT INTO daily_tasks (task_date, slot, task, task_status)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (task_date, slot)
                    DO UPDATE SET
                        task = EXCLUDED.task,
                        task_status = EXCLUDED.task_status
                """, (task_date, slot, v["task"], v["status"]))


# ==============================
# DATE
# ==============================
selected_date = st.date_input("Select day", date.today())

if "tasks" not in st.session_state or st.session_state.get("loaded_date") != selected_date:
    st.session_state.tasks = load_tasks(selected_date)
    st.session_state.loaded_date = selected_date

tasks = st.session_state.tasks

# ==============================
# FORM (THIS IS THE FIX)
# ==============================
with st.form("daily_form"):
    for slot in range(1, TOTAL_SLOTS + 1):
        c1, c2, c3 = st.columns([2, 6, 2])

        start = (datetime.min + timedelta(minutes=(slot - 1) * 30)).time()
        end = (datetime.min + timedelta(minutes=slot * 30)).time()

        c1.write(f"{start.strftime('%H:%M')}–{end.strftime('%H:%M')}")

        tasks[slot]["task"] = c2.text_input(
            "Task",
            value=tasks[slot]["task"],
            key=f"task_{slot}",
            label_visibility="collapsed"
        )

        tasks[slot]["status"] = c3.selectbox(
            "Status",
            STATUSES,
            index=STATUSES.index(tasks[slot]["status"]),
            key=f"status_{slot}",
            label_visibility="collapsed"
        )

    col1, col2 = st.columns(2)
    save = col1.form_submit_button("💾 Save")
    cancel = col2.form_submit_button("❌ Cancel")

# ==============================
# ACTIONS
# ==============================
if save:
    save_tasks(selected_date, tasks)
    st.session_state.tasks = load_tasks(selected_date)
    st.success("Saved")

if cancel:
    st.session_state.tasks = load_tasks(selected_date)
    st.info("Changes discarded")
