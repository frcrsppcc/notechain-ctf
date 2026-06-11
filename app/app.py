import os
import hashlib
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, make_response

app = Flask(__name__)

DB = os.environ.get("DB_PATH", "/app/data/database.db")

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    conn = get_db()
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL
        );
    """)
    if not conn.execute("SELECT id FROM users WHERE username='admin'").fetchone():
        flag = os.environ.get("FLAG", "CTF{csrf_and_cookie_tossing_chain}")
        if os.path.exists("/app/flag.txt"):
            flag = open("/app/flag.txt").read().strip()
        conn.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                     ("admin", "s3cur3_admin_p4ssw0rd_1337", "admin@notchain.ctf"))
        uid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("INSERT INTO notes (user_id, title, content) VALUES (?, ?, ?)",
                     (uid, "Flag Note", flag))
        conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if not username or not password:
            return "username and password required"
        conn = get_db()
        try:
            conn.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                        [username, password, username + "@notchain.ctf"])
            conn.commit()
            resp = make_response(redirect("/dashboard"))
            resp.set_cookie("session", username, httponly=True)
            token = hashlib.md5((username + "notchain-salt").encode()).hexdigest()
            resp.set_cookie("csrf_token", token)
            return resp
        except sqlite3.IntegrityError:
            return "username taken"
        finally:
            conn.close()
    return render_template("register.html")

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=?",
                           [username, password]).fetchone()
        conn.close()
        if user:
            resp = make_response(redirect("/dashboard"))
            resp.set_cookie("session", username, httponly=True)
            token = hashlib.md5((username + "notchain-salt").encode()).hexdigest()
            resp.set_cookie("csrf_token", token)
            return resp
        return "wrong credentials"
    return render_template("login.html")

@app.route('/dashboard')
def dashboard():
    username = request.cookies.get("session")
    if not username:
        return redirect("/login")
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username=?", [username]).fetchone()
    if not user:
        return redirect("/login")
    notes = conn.execute("SELECT * FROM notes WHERE user_id=?", [user["id"]]).fetchall()
    conn.close()
    return render_template("dashboard.html", user=user, notes=notes)

@app.route('/notes/<int:note_id>')
def view_note(note_id):
    username = request.cookies.get("session")
    if not username:
        return redirect("/login")
    conn = get_db()
    note = conn.execute("SELECT * FROM notes WHERE id=?", [note_id]).fetchone()
    conn.close()
    if not note:
        return "note not found"
    return render_template("note.html", note=note)

@app.route('/create', methods=["POST"])
def create_note():
    username = request.cookies.get("session")
    if not username:
        return redirect("/login")
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    if not title or not content:
        return "title and content required"
    conn = get_db()
    user = conn.execute("SELECT id FROM users WHERE username=?", [username]).fetchone()
    conn.execute("INSERT INTO notes (user_id, title, content) VALUES (?, ?, ?)",
                [user["id"], title, content])
    conn.commit()
    conn.close()
    return redirect("/dashboard")

@app.route('/logout')
def logout():
    resp = make_response(redirect("/"))
    resp.set_cookie("session", "", max_age=0)
    resp.set_cookie("csrf_token", "", max_age=0)
    return resp

# ===== API — accessible via api.ctf.local =====
@app.route('/cookie/set')
def cookie_set():
    name = request.args.get("name")
    value = request.args.get("value")
    if not name or not value:
        return "?name=X&value=Y"
    resp = make_response("ok")
    # set cookie for entire domain so subdomains share it
    resp.set_cookie(name, value, domain=".ctf.local")
    return resp

# ===== Password change (vulnerable — GET method!) =====
@app.route('/change-password')
def change_password():
    username = request.cookies.get("session")
    if not username:
        return redirect("/login")

    new_pass = request.args.get("password")
    csrf = request.args.get("csrf_token")

    if not new_pass or not csrf:
        return "missing password or csrf_token"

    # Double-submit cookie check
    # accept any matching token — needed for cross-subdomain sharing
    tokens = request.cookies.getlist("csrf_token")
    if csrf not in tokens:
        return "csrf token mismatch"

    conn = get_db()
    conn.execute("UPDATE users SET password=? WHERE username=?", [new_pass, username])
    conn.commit()
    conn.close()
    return "password changed!"

@app.route('/flag')
def flag():
    username = request.cookies.get("session")
    if username == "admin":
        conn = get_db()
        note = conn.execute(
            "SELECT content FROM notes WHERE user_id=(SELECT id FROM users WHERE username='admin') AND title='Flag Note'"
        ).fetchone()
        conn.close()
        if note:
            return note[0]
        return "no flag note found"
    return "not authorized"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
