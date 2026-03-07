"""
ACEest Fitness & Gym - Flask Web Application
Converted from tkinter desktop app (Aceestver-3.2.4.py) to Flask web app.
"""

import sqlite3
import os
from datetime import date
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, g, jsonify
)

# ─────────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "aceest-secret-2025")

DB_NAME = os.environ.get("DB_PATH", "aceest_fitness.db")

# Fitness programs (same data from original app)
PROGRAMS = {
    "Fat Loss": {
        "factor": 22,
        "workout": "Mon: Back Squat 5x5 + Core\nTue: EMOM 20min Assault Bike\nWed: Bench Press + 21-15-9\nThu: Deadlift + Box Jumps\nFri: Zone 2 Cardio 30min",
        "diet": "Breakfast: Egg Whites + Oats\nLunch: Grilled Chicken + Brown Rice\nDinner: Fish Curry + Millet Roti\nTarget: ~2000 kcal"
    },
    "Muscle Gain": {
        "factor": 35,
        "workout": "Mon: Squat 5x5\nTue: Bench 5x5\nWed: Deadlift 4x6\nThu: Front Squat 4x8\nFri: Incline Press 4x10\nSat: Barbell Rows 4x10",
        "diet": "Breakfast: Eggs + Peanut Butter Oats\nLunch: Chicken Biryani\nDinner: Mutton Curry + Rice\nTarget: ~3200 kcal"
    },
    "Beginner": {
        "factor": 26,
        "workout": "Full Body Circuit:\n- Air Squats\n- Ring Rows\n- Push-ups\nFocus: Technique & Consistency",
        "diet": "Balanced Tamil Meals\nIdli / Dosa / Rice + Dal\nProtein Target: 120g/day"
    }
}

WORKOUT_TYPES = ["Strength", "Hypertrophy", "Cardio", "Mobility"]

# ─────────────────────────────────────────────
# DATABASE HELPERS
# ─────────────────────────────────────────────
def get_db():
    """
    Open a database connection stored on Flask's 'g' object (per-request).
    When using :memory: (tests), reuse a single module-level connection so
    all requests in a test share the same in-memory database.
    """
    if DB_NAME == ":memory:":
        # In-memory DB: use a single module-level connection
        if not hasattr(app, "_test_db"):
            conn = sqlite3.connect(DB_NAME, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            app._test_db = conn
        return app._test_db

    if "db" not in g:
        g.db = sqlite3.connect(DB_NAME)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    """Close the database connection at end of each request (file DB only)."""
    if DB_NAME != ":memory:":
        db = g.pop("db", None)
        if db is not None:
            db.close()


def init_db():
    """Create all tables and seed a default admin user."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # For :memory: mode, store this connection so get_db() reuses it
    if DB_NAME == ":memory:":
        app._test_db = conn
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role     TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS clients (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            name              TEXT UNIQUE NOT NULL,
            age               INTEGER,
            height            REAL,
            weight            REAL,
            program           TEXT,
            calories          INTEGER,
            target_weight     REAL,
            target_adherence  INTEGER,
            membership_status TEXT DEFAULT 'Active',
            membership_end    TEXT
        );

        CREATE TABLE IF NOT EXISTS progress (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            week        TEXT NOT NULL,
            adherence   INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS workouts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name  TEXT NOT NULL,
            date         TEXT NOT NULL,
            workout_type TEXT,
            duration_min INTEGER,
            notes        TEXT
        );

        CREATE TABLE IF NOT EXISTS metrics (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            date        TEXT NOT NULL,
            weight      REAL,
            waist       REAL,
            bodyfat     REAL
        );
    """)

    # Seed default admin
    cur.execute("SELECT 1 FROM users WHERE username = 'admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO users VALUES ('admin', 'admin123', 'Admin')")

    conn.commit()
    if DB_NAME != ":memory:":
        conn.close()


# ─────────────────────────────────────────────
# AUTH DECORATOR
# ─────────────────────────────────────────────
def login_required(f):
    """Redirect to login page if user is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
# ROUTES — AUTH
# ─────────────────────────────────────────────
@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        db = get_db()
        user = db.execute(
            "SELECT role FROM users WHERE username = ? AND password = ?",
            (username, password)
        ).fetchone()

        if user:
            session["username"] = username
            session["role"] = user["role"]
            flash(f"Welcome back, {username}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ─────────────────────────────────────────────
# ROUTES — DASHBOARD
# ─────────────────────────────────────────────
@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    clients = db.execute(
        "SELECT name, program, membership_status FROM clients ORDER BY name"
    ).fetchall()

    total_clients  = len(clients)
    active_clients = sum(1 for c in clients if c["membership_status"] == "Active")

    return render_template(
        "dashboard.html",
        clients=clients,
        total_clients=total_clients,
        active_clients=active_clients,
        username=session["username"],
        role=session["role"]
    )


# ─────────────────────────────────────────────
# ROUTES — CLIENTS
# ─────────────────────────────────────────────
@app.route("/clients/add", methods=["GET", "POST"])
@login_required
def add_client():
    if request.method == "POST":
        name    = request.form.get("name", "").strip()
        age     = request.form.get("age") or None
        height  = request.form.get("height") or None
        weight  = request.form.get("weight") or None
        program = request.form.get("program", "").strip()
        t_weight = request.form.get("target_weight") or None
        t_adhere = request.form.get("target_adherence") or None
        mem_end  = request.form.get("membership_end") or None

        if not name:
            flash("Client name is required.", "danger")
            return render_template("add_client.html", programs=PROGRAMS)

        # Calculate calories if weight and program selected
        calories = None
        if weight and program and program in PROGRAMS:
            calories = int(float(weight) * PROGRAMS[program]["factor"])

        db = get_db()
        try:
            db.execute(
                """INSERT INTO clients
                   (name, age, height, weight, program, calories,
                    target_weight, target_adherence, membership_status, membership_end)
                   VALUES (?,?,?,?,?,?,?,?,'Active',?)""",
                (name, age, height, weight, program, calories,
                 t_weight, t_adhere, mem_end)
            )
            db.commit()
            flash(f"Client '{name}' added successfully!", "success")
            return redirect(url_for("client_detail", name=name))
        except sqlite3.IntegrityError:
            flash(f"A client named '{name}' already exists.", "danger")

    return render_template("add_client.html", programs=PROGRAMS)


@app.route("/clients/<name>")
@login_required
def client_detail(name):
    db = get_db()
    client = db.execute("SELECT * FROM clients WHERE name = ?", (name,)).fetchone()
    if not client:
        flash(f"Client '{name}' not found.", "danger")
        return redirect(url_for("dashboard"))

    workouts = db.execute(
        "SELECT * FROM workouts WHERE client_name = ? ORDER BY date DESC LIMIT 10",
        (name,)
    ).fetchall()

    progress = db.execute(
        "SELECT week, adherence FROM progress WHERE client_name = ? ORDER BY id",
        (name,)
    ).fetchall()

    program_info = PROGRAMS.get(client["program"], None)

    return render_template(
        "client_detail.html",
        client=client,
        workouts=workouts,
        progress=progress,
        program_info=program_info,
        workout_types=WORKOUT_TYPES,
        today=date.today().isoformat()
    )


@app.route("/clients/<name>/edit", methods=["GET", "POST"])
@login_required
def edit_client(name):
    db = get_db()
    client = db.execute("SELECT * FROM clients WHERE name = ?", (name,)).fetchone()
    if not client:
        flash("Client not found.", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        age      = request.form.get("age") or None
        height   = request.form.get("height") or None
        weight   = request.form.get("weight") or None
        program  = request.form.get("program", "").strip()
        t_weight = request.form.get("target_weight") or None
        t_adhere = request.form.get("target_adherence") or None
        mem_status = request.form.get("membership_status", "Active")
        mem_end    = request.form.get("membership_end") or None

        calories = None
        if weight and program and program in PROGRAMS:
            calories = int(float(weight) * PROGRAMS[program]["factor"])

        db.execute(
            """UPDATE clients SET age=?, height=?, weight=?, program=?,
               calories=?, target_weight=?, target_adherence=?,
               membership_status=?, membership_end=? WHERE name=?""",
            (age, height, weight, program, calories,
             t_weight, t_adhere, mem_status, mem_end, name)
        )
        db.commit()
        flash("Client updated successfully!", "success")
        return redirect(url_for("client_detail", name=name))

    return render_template("edit_client.html", client=client, programs=PROGRAMS)


@app.route("/clients/<name>/delete", methods=["POST"])
@login_required
def delete_client(name):
    db = get_db()
    db.execute("DELETE FROM clients WHERE name = ?", (name,))
    db.execute("DELETE FROM workouts WHERE client_name = ?", (name,))
    db.execute("DELETE FROM progress WHERE client_name = ?", (name,))
    db.execute("DELETE FROM metrics WHERE client_name = ?", (name,))
    db.commit()
    flash(f"Client '{name}' deleted.", "info")
    return redirect(url_for("dashboard"))


# ─────────────────────────────────────────────
# ROUTES — WORKOUTS
# ─────────────────────────────────────────────
@app.route("/clients/<name>/workout/add", methods=["POST"])
@login_required
def add_workout(name):
    workout_date = request.form.get("workout_date", date.today().isoformat())
    workout_type = request.form.get("workout_type", "")
    duration     = request.form.get("duration_min") or 60
    notes        = request.form.get("notes", "")

    db = get_db()
    db.execute(
        "INSERT INTO workouts (client_name, date, workout_type, duration_min, notes) VALUES (?,?,?,?,?)",
        (name, workout_date, workout_type, duration, notes)
    )
    db.commit()
    flash("Workout logged!", "success")
    return redirect(url_for("client_detail", name=name))


# ─────────────────────────────────────────────
# ROUTES — PROGRESS
# ─────────────────────────────────────────────
@app.route("/clients/<name>/progress/add", methods=["POST"])
@login_required
def add_progress(name):
    week      = request.form.get("week", "").strip()
    adherence = request.form.get("adherence", 0)

    if not week:
        flash("Week label is required.", "danger")
        return redirect(url_for("client_detail", name=name))

    db = get_db()
    db.execute(
        "INSERT INTO progress (client_name, week, adherence) VALUES (?,?,?)",
        (name, week, adherence)
    )
    db.commit()
    flash("Progress entry added!", "success")
    return redirect(url_for("client_detail", name=name))


# ─────────────────────────────────────────────
# ROUTES — API (JSON) — Used by tests & charts
# ─────────────────────────────────────────────
@app.route("/api/clients")
@login_required
def api_clients():
    db = get_db()
    rows = db.execute("SELECT name, program, membership_status FROM clients").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/clients/<name>/progress")
@login_required
def api_progress(name):
    db = get_db()
    rows = db.execute(
        "SELECT week, adherence FROM progress WHERE client_name = ? ORDER BY id",
        (name,)
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "app": "ACEest Fitness"})


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
