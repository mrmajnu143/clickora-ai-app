from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for
)

import sqlite3
import hashlib
import os
import re
from functools import wraps
from PIL import Image


# =========================================================
# APP CONFIGURATION
# =========================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "thumora-development-secret-change-later"
)

DATABASE = "thumora.db"

UPLOAD_FOLDER = "uploads"

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


# Create uploads folder automatically
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================================================
# DATABASE
# =========================================================

def get_db():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = get_db()

    # Users table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
    """)

    # Analyses table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analyses (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            title TEXT NOT NULL,

            hook TEXT NOT NULL,

            platform TEXT NOT NULL,

            thumbnail_score INTEGER NOT NULL,

            hook_score INTEGER NOT NULL,

            overall_score INTEGER NOT NULL,

            thumbnail_name TEXT,

            thumbnail_width INTEGER,

            thumbnail_height INTEGER,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(user_id)
            REFERENCES users(id)

        )
    """)

    conn.commit()

    conn.close()


# =========================================================
# PASSWORD HASHING
# =========================================================

def hash_password(password):

    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()


# =========================================================
# LOGIN REQUIRED DECORATOR
# =========================================================

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:

            return redirect(
                url_for("login")
            )

        return function(*args, **kwargs)

    return wrapper


# =========================================================
# FILE VALIDATION
# =========================================================

def allowed_file(filename):

    return (
        "." in filename
        and
        filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================================================
# REGISTER PAGE
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":

        return render_template(
            "register.html"
        )

    data = request.get_json()

    if not data:

        return jsonify({
            "success": False,
            "message": "Invalid request."
        }), 400

    name = data.get(
        "name",
        ""
    ).strip()

    email = data.get(
        "email",
        ""
    ).strip().lower()

    password = data.get(
        "password",
        ""
    )

    confirm_password = data.get(
        "confirm_password",
        ""
    )


    # Required fields
    if not name or not email or not password:

        return jsonify({
            "success": False,
            "message": "Please fill all required fields."
        }), 400


    # Email validation
    if not re.match(
        r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        email
    ):

        return jsonify({
            "success": False,
            "message": "Please enter a valid email."
        }), 400


    # Password validation
    if len(password) < 6:

        return jsonify({
            "success": False,
            "message": "Password must contain at least 6 characters."
        }), 400


    if password != confirm_password:

        return jsonify({
            "success": False,
            "message": "Passwords do not match."
        }), 400


    conn = get_db()


    try:

        conn.execute(
            """
            INSERT INTO users
            (name, email, password)

            VALUES (?, ?, ?)
            """,

            (
                name,
                email,
                hash_password(password)
            )
        )

        conn.commit()


    except sqlite3.IntegrityError:

        conn.close()

        return jsonify({
            "success": False,
            "message": "This email is already registered."
        }), 400


    conn.close()


    return jsonify({
        "success": True,
        "message": "Account created successfully."
    })


# =========================================================
# LOGIN PAGE
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":

        return render_template(
            "login.html"
        )


    data = request.get_json()

    if not data:

        return jsonify({
            "success": False,
            "message": "Invalid request."
        }), 400


    email = data.get(
        "email",
        ""
    ).strip().lower()

    password = data.get(
        "password",
        ""
    )


    conn = get_db()


    user = conn.execute(
        """
        SELECT *

        FROM users

        WHERE email = ?
        AND password = ?
        """,

        (
            email,
            hash_password(password)
        )
    ).fetchone()


    conn.close()


    if not user:

        return jsonify({
            "success": False,
            "message": "Invalid email or password."
        }), 401


    # Create session
    session.clear()

    session["user_id"] = user["id"]

    session["user_name"] = user["name"]

    session["user_email"] = user["email"]


    return jsonify({
        "success": True,
        "message": "Login successful."
    })


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
@login_required
def dashboard():

    return render_template(
        "dashboard.html"
    )


# =========================================================
# ANALYZE CONTENT
# =========================================================

@app.route(
    "/analyze",
    methods=["POST"]
)
@login_required
def analyze():

    title = request.form.get(
        "title",
        ""
    ).strip()

    hook = request.form.get(
        "hook",
        ""
    ).strip()

    platform = request.form.get(
        "platform",
        "YouTube"
    ).strip()


    # Validate text
    if not title or not hook:

        return jsonify({
            "success": False,
            "message": "Title and hook are required."
        }), 400


    thumbnail_score = 50


    # =====================================================
    # THUMBNAIL IMAGE
    # =====================================================

    thumbnail = request.files.get(
        "thumbnail"
    )

    thumbnail_name = None

    image_width = None

    image_height = None


    if thumbnail and thumbnail.filename:

        if not allowed_file(
            thumbnail.filename
        ):

            return jsonify({
                "success": False,
                "message": "Only PNG, JPG, JPEG and WEBP images are allowed."
            }), 400


        try:

            image = Image.open(
                thumbnail
            )

            image.verify()

            thumbnail.seek(0)

            image = Image.open(
                thumbnail
            )

            image_width, image_height = image.size


            # Resolution score
            if image_width >= 1280:
                thumbnail_score += 15

            if image_height >= 720:
                thumbnail_score += 10


            # Aspect ratio check
            ratio = image_width / image_height

            if 1.6 <= ratio <= 1.9:
                thumbnail_score += 10


            # Save image
            safe_name = (
                str(session["user_id"])
                + "_"
                + os.path.basename(
                    thumbnail.filename
                )
            )

            thumbnail_path = os.path.join(
                UPLOAD_FOLDER,
                safe_name
            )

            thumbnail.save(
                thumbnail_path
            )

            thumbnail_name = safe_name


        except Exception:

            return jsonify({
                "success": False,
                "message": "Invalid image file."
            }), 400


    else:

        # No image uploaded
        thumbnail_score += 5


    thumbnail_score = min(
        thumbnail_score,
        100
    )


    # =====================================================
    # HOOK ANALYSIS
    # =====================================================

    hook_score = 50


    hook_length = len(hook)


    # Good hook length
    if 20 <= hook_length <= 100:

        hook_score += 15


    # Question creates curiosity
    if "?" in hook:

        hook_score += 10


    curiosity_words = [

        "how",
        "why",
        "secret",
        "mistake",
        "truth",
        "best",
        "easy",
        "tips",
        "hack",
        "before",
        "never",
        "hidden",
        "reason"

    ]


    for word in curiosity_words:

        if word in hook.lower():

            hook_score += 2


    # Numbers can make hooks more specific
    if any(
        character.isdigit()
        for character in hook
    ):

        hook_score += 5


    hook_score = min(
        hook_score,
        100
    )


    # =====================================================
    # TITLE ANALYSIS
    # =====================================================

    if len(title) <= 60:

        thumbnail_score += 5


    if any(
        character.isdigit()
        for character in title
    ):

        thumbnail_score += 5


    thumbnail_score = min(
        thumbnail_score,
        100
    )


    # =====================================================
    # OVERALL SCORE
    # =====================================================

    overall_score = round(
        (
            thumbnail_score
            +
            hook_score
        ) / 2
    )


    # =====================================================
    # SUGGESTIONS
    # =====================================================

    suggestions = []


    if thumbnail_score < 70:

        suggestions.append(
            "Improve thumbnail resolution and visual clarity."
        )


    if hook_score < 70:

        suggestions.append(
            "Make the hook more curiosity-driven."
        )


    if len(hook) < 20:

        suggestions.append(
            "Try making your hook more descriptive."
        )


    if "?" not in hook:

        suggestions.append(
            "Consider using a question to create curiosity."
        )


    if len(title) > 60:

        suggestions.append(
            "Keep your title concise and easy to read."
        )


    if not suggestions:

        suggestions.append(
            "Your content idea has strong optimization signals."
        )


    # =====================================================
    # SAVE ANALYSIS
    # =====================================================

    conn = get_db()


    cursor = conn.execute(
        """
        INSERT INTO analyses
        (
            user_id,
            title,
            hook,
            platform,
            thumbnail_score,
            hook_score,
            overall_score,
            thumbnail_name,
            thumbnail_width,
            thumbnail_height
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,

        (
            session["user_id"],
            title,
            hook,
            platform,
            thumbnail_score,
            hook_score,
            overall_score,
            thumbnail_name,
            image_width,
            image_height
        )
    )


    analysis_id = cursor.lastrowid


    conn.commit()

    conn.close()


    # =====================================================
    # RESPONSE
    # =====================================================

    return jsonify({

        "success": True,

        "analysis_id":
            analysis_id,

        "thumbnail_score":
            thumbnail_score,

        "hook_score":
            hook_score,

        "overall_score":
            overall_score,

        "suggestions":
            suggestions
    })


# =========================================================
# RESULT PAGE
# =========================================================

@app.route(
    "/result/<int:analysis_id>"
)
@login_required
def result(analysis_id):

    conn = get_db()


    analysis = conn.execute(
        """
        SELECT *

        FROM analyses

        WHERE id = ?
        AND user_id = ?
        """,

        (
            analysis_id,
            session["user_id"]
        )
    ).fetchone()


    conn.close()


    if not analysis:

        return redirect(
            url_for("dashboard")
        )


    return render_template(
        "result.html",
        analysis=analysis
    )


# =========================================================
# HISTORY PAGE
# =========================================================

@app.route("/history")
@login_required
def history():

    conn = get_db()


    analyses = conn.execute(
        """
        SELECT *

        FROM analyses

        WHERE user_id = ?

        ORDER BY id DESC
        """,

        (
            session["user_id"],
        )
    ).fetchall()


    conn.close()


    return render_template(
        "history.html",
        analyses=analyses
    )

# =========================================================
# PROFILE PAGE
# =========================================================

@app.route("/profile")
@login_required
def profile_page():

    conn = get_db()

    user = conn.execute(
        """
        SELECT
            id,
            name,
            email,
            created_at
        FROM users
        WHERE id = ?
        """,
        (session["user_id"],)
    ).fetchone()

    conn.close()

    return render_template(
        "profile.html",
        user=user
    )


# =========================================================
# PROFILE API
# =========================================================

@app.route("/api/profile")
@login_required
def profile():

    conn = get_db()


    user = conn.execute(
        """
        SELECT
            id,
            name,
            email,
            created_at

        FROM users

        WHERE id = ?
        """,

        (
            session["user_id"],
        )
    ).fetchone()


    conn.close()


    return jsonify({
        "success": True,
        "user": dict(user)
    })


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":

    init_db()

    app.run(
        debug=True
    )