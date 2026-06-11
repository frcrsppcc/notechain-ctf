import os
import secrets
import sqlite3
from flask import Flask, render_template, request, redirect, make_response

app = Flask(__name__)

DB = os.environ.get("DB_PATH", "/app/data/database.db")

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    db = get_db()
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
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
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            csrf_token TEXT NOT NULL
        );
    """)
    if not db.execute("SELECT id FROM users WHERE username='admin'").fetchone():
        db.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                     ("admin", "s3cur3_admin_p4ssw0rd_1337", "admin@notchain.ctf"))
        uid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute("INSERT INTO notes (user_id, title, content) VALUES (?, ?, ?)",
                     (uid, "Flag Note", "flag is only visible at /flag"))
        db.commit()
    db.close()

init_db()

def get_session(token):
    if not token:
        return None
    conn = get_db()
    r = conn.execute("SELECT username, csrf_token FROM sessions WHERE token=?", [token]).fetchone()
    conn.close()
    if r:
        return dict(r)
    return None

def do_login(username):
    session_token = secrets.token_hex(32)
    csrf = secrets.token_hex(16)
    conn = get_db()
    conn.execute("INSERT INTO sessions (token, username, csrf_token) VALUES (?, ?, ?)",
                 [session_token, username, csrf])
    conn.commit()
    conn.close()
    resp = make_response(redirect("/dashboard"))
    resp.set_cookie("session", session_token, httponly=True)
    resp.set_cookie("csrf_token", csrf, httponly=True)
    return resp

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
            conn.close()
            return do_login(username)
        except sqlite3.IntegrityError:
            conn.close()
            return "username taken"
    return render_template("register.html")

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        conn = get_db()
        u = conn.execute("SELECT * FROM users WHERE username=? AND password=?",
                           [username, password]).fetchone()
        conn.close()
        if u:
            return do_login(username)
        return "wrong credentials"
    return render_template("login.html")

@app.route('/dashboard')
def dashboard():
    sess = get_session(request.cookies.get("session"))
    if not sess:
        return redirect("/login")
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE username=?", [sess["username"]]).fetchone()
    if not u:
        return redirect("/login")
    notes = conn.execute("SELECT * FROM notes WHERE user_id=?", [u["id"]]).fetchall()
    conn.close()
    return render_template("dashboard.html", user=u, notes=notes)

@app.route('/notes/<int:note_id>')
def view_note(note_id):
    sess = get_session(request.cookies.get("session"))
    if not sess:
        return redirect("/login")
    conn = get_db()
    note = conn.execute("SELECT * FROM notes WHERE id=?", [note_id]).fetchone()
    conn.close()
    if not note:
        return "note not found"
    return render_template("note.html", note=note)

@app.route('/create', methods=["POST"])
def create_note():
    sess = get_session(request.cookies.get("session"))
    if not sess:
        return redirect("/login")
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    if not title or not content:
        return "title and content required"
    conn = get_db()
    u = conn.execute("SELECT id FROM users WHERE username=?", [sess["username"]]).fetchone()
    conn.execute("INSERT INTO notes (user_id, title, content) VALUES (?, ?, ?)",
                [u["id"], title, content])
    conn.commit()
    conn.close()
    return redirect("/dashboard")

@app.route('/logout')
def logout():
    token = request.cookies.get("session")
    if token:
        conn = get_db()
        conn.execute("DELETE FROM sessions WHERE token=?", [token])
        conn.commit()
        conn.close()
    resp = make_response(redirect("/"))
    resp.set_cookie("session", "", max_age=0)
    resp.set_cookie("csrf_token", "", max_age=0)
    return resp

@app.route('/cookie/set')
def cookie_set():
    name = request.args.get("name")
    value = request.args.get("value")
    if not name or not value:
        return "?name=X&value=Y"
    resp = make_response("ok")
    resp.set_cookie(name, value, path="/change-password")
    return resp

@app.route('/change-password')
def change_password():
    sess = get_session(request.cookies.get("session"))
    if not sess:
        return redirect("/login")

    new_pass = request.args.get("password")
    csrf = request.args.get("csrf_token")

    if not new_pass or not csrf:
        return "missing password or csrf_token"

    tokens = request.cookies.getlist("csrf_token")
    if csrf not in tokens:
        return "csrf token mismatch"

    conn = get_db()
    conn.execute("UPDATE users SET password=? WHERE username=?", [new_pass, sess["username"]])
    conn.commit()
    conn.close()
    return "password changed!"

@app.route('/flag')
def flag():
    sess = get_session(request.cookies.get("session"))
    if not sess or sess["username"] != "admin":
        return "not authorized"
    pw = request.args.get("password", "")
    conn = get_db()
    row = conn.execute("SELECT password FROM users WHERE username='admin'").fetchone()
    conn.close()
    if not row or row["password"] != pw:
        return "wrong password"
    return os.environ.get("FLAG", "CTF{csrf_and_cookie_tossing_chain}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
