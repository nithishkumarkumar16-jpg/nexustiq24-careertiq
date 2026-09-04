from typing import Any
from src.database import connection


def rows_as_dicts(rows):
    return [dict(row) for row in rows]


def list_customers() -> list[dict[str, Any]]:
    conn = connection()
    rows = conn.execute("SELECT customer_id, full_name, account_status FROM customers ORDER BY customer_id").fetchall()
    conn.close()
    return rows_as_dicts(rows)


def customer_context(customer_id: str) -> dict[str, Any] | None:
    conn = connection()
    customer = conn.execute("SELECT * FROM customers WHERE customer_id=?", (customer_id,)).fetchone()
    if not customer:
        conn.close(); return None
    service = conn.execute("SELECT * FROM service_accounts WHERE customer_id=?", (customer_id,)).fetchone()
    billing = conn.execute("SELECT * FROM billing_accounts WHERE customer_id=?", (customer_id,)).fetchone()
    tickets = conn.execute("SELECT * FROM tickets WHERE customer_id=? ORDER BY updated_at DESC", (customer_id,)).fetchall()
    conn.close()
    return {"customer": dict(customer), "service": dict(service) if service else {}, "billing": dict(billing) if billing else {}, "tickets": rows_as_dicts(tickets)}


def get_messages(customer_id: str, session_id: str) -> list[dict[str, Any]]:
    conn = connection()
    rows = conn.execute("SELECT role, content, created_at FROM conversation_messages WHERE customer_id=? AND session_id=? ORDER BY message_id", (customer_id, session_id)).fetchall()
    conn.close()
    return rows_as_dicts(rows)


def add_message(customer_id: str, session_id: str, role: str, content: str) -> None:
    conn = connection()
    conn.execute("INSERT INTO conversation_messages(session_id,customer_id,role,content) VALUES(?,?,?,?)", (session_id, customer_id, role, content))
    conn.commit(); conn.close()
