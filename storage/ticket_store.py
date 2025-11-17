import sqlite3
import json
from config.settings import DB_PATH

class TicketStore:

    def __init__(self):
        self.conn = sqlite3.connect(
            DB_PATH,
            check_same_thread=False,
            timeout=30
        )
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jira_key TEXT,
                summary TEXT,
                embedding BLOB,
                occurrences INTEGER DEFAULT 1
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS occurrences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER,
                trace TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS exception_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER,

                priority TEXT,
                summary TEXT,
                cause TEXT,
                suggestions TEXT,
                documentation_links TEXT,
                exception_class TEXT,

                trace TEXT,
                canonical_trace TEXT,
                snippet TEXT,

                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)


        
        self.conn.commit()

    def add_new_ticket(self, jira_key, summary, embedding):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO tickets (jira_key, summary, embedding) VALUES (?, ?, ?)",
            (jira_key, summary, embedding)
        )
        ticket_id = cur.lastrowid
        self.conn.commit()
        return ticket_id

    def add_occurrence(self, ticket_id, trace):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO occurrences (ticket_id, trace) VALUES (?, ?)",
            (ticket_id, trace)
        )
        cur.execute(
            "UPDATE tickets SET occurrences = occurrences + 1 WHERE id = ?",
            (ticket_id,)
        )
        self.conn.commit()

    def fetch_all_embeddings(self):
        cur = self.conn.cursor()
        cur.execute("SELECT id, summary, embedding FROM tickets")
        return cur.fetchall()

    def add_exception_details(self, ticket_id, analysis, trace, canonical, snippet):
        cur = self.conn.cursor()

        cur.execute("""
            INSERT INTO exception_details
            (ticket_id, priority, summary, cause, suggestions, documentation_links, 
            exception_class, trace, canonical_trace, snippet)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticket_id,
            analysis["priority"],
            analysis["summary"],
            analysis["cause"],
            json.dumps(analysis.get("suggestions", [])),
            json.dumps(analysis.get("documentation_link", [])),
            analysis.get("exception_class", "Unknown"),
            trace,
            canonical,
            snippet,
        ))

        self.conn.commit()

