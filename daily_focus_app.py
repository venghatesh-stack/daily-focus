import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_tasks (
            id SERIAL PRIMARY KEY,
            task_date DATE,
            slot TEXT,
            task_name TEXT,
            status TEXT
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
