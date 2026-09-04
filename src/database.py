"""SQLite storage and repeatable fictional demo data."""
import sqlite3
from src.config import DB_PATH, DATA_DIR


def connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database() -> None:
    conn = connection()
    try:
        conn.executescript(
            """
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY, full_name TEXT NOT NULL, email TEXT NOT NULL,
            phone_number TEXT NOT NULL, account_status TEXT NOT NULL, service_address TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS service_accounts (
            service_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, service_type TEXT NOT NULL,
            plan_name TEXT NOT NULL, plan_price REAL NOT NULL, contract_end_date TEXT,
            service_status TEXT NOT NULL, network_area TEXT, usage_summary TEXT,
            FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
        );
        CREATE TABLE IF NOT EXISTS billing_accounts (
            billing_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, current_balance REAL NOT NULL,
            payment_status TEXT NOT NULL, last_invoice_date TEXT, last_invoice_amount REAL,
            recent_charge_summary TEXT, autopay_enabled INTEGER NOT NULL,
            FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
        );
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, category TEXT NOT NULL,
            status TEXT NOT NULL, priority TEXT NOT NULL, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, summary TEXT NOT NULL, actions_taken TEXT NOT NULL,
            resolution TEXT, agent_notes TEXT, escalated_to TEXT,
            FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
        );
        CREATE TABLE IF NOT EXISTS conversation_messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
            customer_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
            """
        )
        if conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0:
            _seed(conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _seed(conn: sqlite3.Connection) -> None:
    customers = [
        ("C001", "Asha Raman", "asha.raman@example.test", "+91 90000 00001", "active", "12 Lake View Road, Chennai", "2023-04-10"),
        ("C002", "Vikram Das", "vikram.das@example.test", "+91 90000 00002", "active", "8 Market Street, Chennai", "2024-01-15"),
        ("C003", "Meera Iyer", "meera.iyer@example.test", "+91 90000 00003", "active", "45 Park Avenue, Chennai", "2022-10-01"),
        ("C004", "Rohan Shah", "rohan.shah@example.test", "+91 90000 00004", "active", "19 Hill Road, Chennai", "2025-02-03"),
        ("C005", "Nila Bose", "nila.bose@example.test", "+91 90000 00005", "active", "3 River Lane, Chennai", "2021-08-19"),
        ("C006", "Arjun Rao", "arjun.rao@example.test", "+91 90000 00006", "active", "78 Station Road, Chennai", "2024-06-11"),
    ]
    services = [
        ("S001", "C001", "broadband", "Home Fibre 100", 799, "2027-04-09", "active", "CHN-NORTH", "Broadband usage normal"),
        ("S002", "C002", "broadband", "Home Fibre 200", 999, "2027-01-14", "outage-affected", "CHN-CENTRAL", "Broadband usage unavailable during outage"),
        ("S003", "C003", "mobile", "Mobile Plus 50GB", 599, "2026-10-01", "active", "CHN-WEST", "32GB of 50GB used this cycle"),
        ("S004", "C004", "mobile", "Mobile Essential 20GB", 399, "2026-02-02", "active", "CHN-SOUTH", "11GB of 20GB used this cycle"),
        ("S005", "C005", "broadband", "Home Fibre 100", 799, "2026-08-18", "active", "CHN-WEST", "Broadband usage normal"),
        ("S006", "C006", "broadband", "Home Fibre 300", 1299, "2027-06-10", "active", "CHN-NORTH", "Broadband usage normal"),
    ]
    billing = [
        ("B001", "C001", 0, "paid", "2026-08-20", 899, "August invoice includes the 799 plan and a one-time 100 router delivery charge.", 1),
        ("B002", "C002", 0, "paid", "2026-08-18", 999, "Regular monthly plan charge only.", 0),
        ("B003", "C003", 0, "paid", "2026-08-12", 599, "Regular monthly plan charge only.", 1),
        ("B004", "C004", 0, "paid", "2026-08-11", 399, "Regular monthly plan charge only; no unrecognized charge recorded.", 1),
        ("B005", "C005", 799, "overdue", "2026-08-17", 799, "August plan charge remains unpaid; no payment is recorded.", 0),
        ("B006", "C006", 0, "paid", "2026-08-19", 1299, "Regular monthly plan charge only.", 1),
    ]
    tickets = [
        ("T001", "C001", "billing", "resolved", "normal", "2026-08-20", "2026-08-20", "Question about August invoice", "Invoice reviewed.", "One-time router delivery charge explained.", "", ""),
        ("T002", "C002", "connectivity", "open", "high", "2026-09-04", "2026-09-04", "Area broadband outage", "No local steps required; outage status confirmed.", None, "Area network operations", ""),
        ("T003", "C005", "billing", "open", "normal", "2026-09-02", "2026-09-02", "Customer says payment was made", "Account checked; payment is not recorded.", None, "", ""),
        ("T004", "C006", "connectivity", "open", "high", "2026-09-01", "2026-09-04", "Broadband remains down", "Router reboot completed; cables checked; router reset completed.", None, "", ""),
    ]
    conn.executemany("INSERT INTO customers VALUES (?,?,?,?,?,?,?)", customers)
    conn.executemany("INSERT INTO service_accounts VALUES (?,?,?,?,?,?,?,?,?)", services)
    conn.executemany("INSERT INTO billing_accounts VALUES (?,?,?,?,?,?,?,?)", billing)
    conn.executemany("INSERT INTO tickets VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", tickets)
