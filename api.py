from flask import Flask, jsonify
import sqlite3
from config.settings import DB_PATH

app = Flask(__name__)

def query_db(query, args=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, args)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/tickets")
def tickets():
    return jsonify(query_db("SELECT * FROM tickets"))

@app.get("/exceptions")
def exceptions():
    return jsonify(query_db("SELECT * FROM exception_details ORDER BY created_at DESC LIMIT 500"))

@app.get("/tickets/<int:id>")
def exceptions_by_ticket(id):
    return jsonify(query_db(
        "SELECT * FROM exception_details WHERE ticket_id = ? ORDER BY created_at DESC",
        (id,)
    ))

if __name__ == "__main__":
    app.run(debug=True)
