import os
import psycopg2
import streamlit as st
from datetime import date

# ---------- PAGE SETUP ----------
st.set_page_config(page_title="Daily Focus", layout="wide")
st.title("🗓️ Daily Focus")

# ---------- DATABASE ----------
DATABASE_URL = os.getenv("DATABASE_URL")

@st.cache_resource
def get_connection():
    result = urlparse(DATABASE_URL)

    return psycopg2.connect(
        dbname=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port,
        sslmode="require",
        options="-c statement_timeout=5000"
    )

import os
import psycopg2
import streamlit as st
from urllib.parse import urlparse

DATABASE_URL = os.getenv("DATABASE_URL")


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_tasks (
            id SERIAL PRIMARY KEY,
            task_date DATE,
            task TEXT,
            status TEXT
        );
    """)
    conn.commit()
    cur.close()

init_db()

# ---------- UI ----------
selected_date = st.date_input("Select day", value=date.today())

st.subheader("Top 5 things for the day")

statuses = ["Not Started", "In Progress", "Done"]

conn = get_connection()
cur = conn.cursor()

for i in range(1, 6):
    col1, col2 = st.columns([3, 1])

    with col1:
        task = st.text_input(f"Task {i}", key=f"task_{i}_{selected_date}")

    with col2:
        status = st.selectbox(
            "Status",
            statuses,
            key=f"status_{i}_{selected_date}"
        )

    if task:
        cur.execute("""
            INSERT INTO daily_tasks (task_date, task, status)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING;
        """, (selected_date, task, status))

conn.commit()
cur.close()

st.success("Saved automatically ✅")


