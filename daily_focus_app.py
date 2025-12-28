import os
import psycopg2
import streamlit as st
import socket
from datetime import date
from urllib.parse import urlparse

# ---------- PAGE SETUP ----------
st.set_page_config(page_title="Daily Focus", layout="wide")
st.title("🗓️ Daily Focus")

# ---------- DATABASE ----------
DATABASE_URL = os.getenv("DATABASE_URL")


@st.cache_resource
def get_connection():
    return psycopg2.connect(
        os.getenv("DATABASE_URL"),
        sslmode="require"
    )


def init_db():
    conn = get_connection()
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_tasks (
            id SERIAL PRIMARY KEY,
            task_date DATE NOT NULL,
            slot INT NOT NULL,
            task TEXT,
            status TEXT,
            UNIQUE (task_date, slot)
        );
    """)

    cur.close()


init_db()
def save_task(task_date, slot, task, status):
    conn = get_connection()
    conn.autocommit = True
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

# ---------- UI ----------
selected_date = st.date_input("Select day", value=date.today())

st.subheader("Top 5 things for the day")

statuses = ["Not Started", "In Progress", "Done"]

conn = get_connection()
cur = conn.cursor()

for slot in range(1, 6):
    col1, col2 = st.columns([3, 1])

    task = st.text_input(
        f"Task {slot}",
        key=f"task_{selected_date}_{slot}"
    )

    status = st.selectbox(
        "Status",
        ["Not Started", "In Progress", "Done"],
        key=f"status_{selected_date}_{slot}"
    )

    if task.strip():
        save_task(selected_date, slot, task, status)

conn.commit()
cur.close()

st.success("Saved automatically ✅")





