import math
import os

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from sqlalchemy.exc import IntegrityError

from models import JobSwitchStage, LearningEntry, User, db

app = Flask(__name__)

# ---------- Configuration ----------

# SECRET_KEY signs the login session cookie. It must come from the environment
# (Compose .env locally, a Kubernetes Secret later) and must be identical on every
# replica, otherwise a login on one Pod is rejected by the other. Fail fast if missing.
secret_key = os.environ.get("SECRET_KEY")
if not secret_key:
    raise RuntimeError("SECRET_KEY environment variable must be set")
app.config["SECRET_KEY"] = secret_key
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # blocks cross-site form posts (CSRF)

# Set ALLOW_REGISTRATION=false once your own account exists.
allow_registration = os.environ.get("ALLOW_REGISTRATION", "true").lower() == "true"

# Database: Postgres when these env vars are set, local SQLite otherwise.
db_host = os.environ.get("POSTGRES_HOST")
db_name = os.environ.get("POSTGRES_DB")
db_password = os.environ.get("POSTGRES_PASSWORD")
db_user = os.environ.get("POSTGRES_USER", "postgres")

if db_host and db_name and db_password:
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:5432/{db_name}"
    )
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tracker.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

db.init_app(app)

with app.app_context():
    db.create_all()

# ---------- Login handling ----------

login_manager = LoginManager()
login_manager.init_app(app)

API_PREFIXES = ("/entries", "/stages", "/debug")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    # JSON API callers get a 401; browser pages get sent to the login form.
    if request.path.startswith(API_PREFIXES):
        return jsonify({"error": "authentication required"}), 401
    return redirect(url_for("login"))


@app.context_processor
def inject_flags():
    return {"allow_registration": allow_registration}


# ---------- Health check (no login, for load balancers / monitoring later) ----------

@app.route("/healthz")
def healthz():
    return "ok", 200


# ---------- Pages ----------

@app.route("/")
@login_required
def home():
    entries = (
        LearningEntry.query.filter_by(user_id=current_user.id)
        .order_by(LearningEntry.date.desc(), LearningEntry.id.desc())
        .all()
    )
    total_hours = sum(e.hours_spent for e in entries)
    return render_template("home.html", entries=entries, total_hours=total_hours)


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    if not allow_registration:
        flash("Registration is disabled.")
        return redirect(url_for("login"))

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")

        if not (3 <= len(username) <= 50):
            flash("Username must be 3 to 50 characters.")
        elif not (8 <= len(password) <= 128):
            flash("Password must be 8 to 128 characters.")
        elif User.query.filter_by(username=username).first():
            flash("That username is taken.")
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("That username is taken.")
            else:
                flash("Account created. Please log in.")
                return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("home"))
        flash("Invalid username or password.")  # same message for both cases on purpose
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/add", methods=["POST"])
@login_required
def add_entry_form():
    topic = request.form.get("topic", "").strip()
    notes = request.form.get("notes", "").strip() or None
    try:
        hours = float(request.form.get("hours_spent", ""))
    except ValueError:
        hours = float("nan")

    if not topic or len(topic) > 120 or not math.isfinite(hours) or not (0 <= hours <= 24):
        flash("Enter a topic (up to 120 characters) and hours between 0 and 24.")
        return redirect(url_for("home"))

    db.session.add(
        LearningEntry(topic=topic, hours_spent=hours, notes=notes, user_id=current_user.id)
    )
    db.session.commit()
    return redirect(url_for("home"))


@app.route("/delete/<int:entry_id>", methods=["POST"])
@login_required
def delete_entry_form(entry_id):
    entry = LearningEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for("home"))


# ---------- JSON API: LearningEntry (login required, scoped to the current user) ----------

def own_entry_or_404(entry_id):
    return LearningEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()


@app.route("/entries", methods=["POST"])
@login_required
def create_entry():
    data = request.get_json(silent=True) or {}
    if not data.get("topic"):
        return jsonify({"error": "topic is required"}), 400
    entry = LearningEntry(
        topic=data["topic"],
        hours_spent=data.get("hours_spent", 0.0),
        notes=data.get("notes"),
        user_id=current_user.id,
    )
    db.session.add(entry)
    db.session.commit()
    return jsonify(entry.to_dict()), 201


@app.route("/entries", methods=["GET"])
@login_required
def list_entries():
    entries = LearningEntry.query.filter_by(user_id=current_user.id).all()
    return jsonify([e.to_dict() for e in entries])


@app.route("/entries/<int:entry_id>", methods=["GET"])
@login_required
def get_entry(entry_id):
    return jsonify(own_entry_or_404(entry_id).to_dict())


@app.route("/entries/<int:entry_id>", methods=["PUT"])
@login_required
def update_entry(entry_id):
    entry = own_entry_or_404(entry_id)
    data = request.get_json(silent=True) or {}
    entry.topic = data.get("topic", entry.topic)
    entry.hours_spent = data.get("hours_spent", entry.hours_spent)
    entry.notes = data.get("notes", entry.notes)
    db.session.commit()
    return jsonify(entry.to_dict())


@app.route("/entries/<int:entry_id>", methods=["DELETE"])
@login_required
def delete_entry(entry_id):
    entry = own_entry_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    return "", 204


# ---------- JSON API: JobSwitchStage (login required, scoped to the current user) ----------

def own_stage_or_404(stage_id):
    return JobSwitchStage.query.filter_by(id=stage_id, user_id=current_user.id).first_or_404()


@app.route("/stages", methods=["POST"])
@login_required
def create_stage():
    data = request.get_json(silent=True) or {}
    if not data.get("company") or not data.get("stage_name"):
        return jsonify({"error": "company and stage_name are required"}), 400
    stage = JobSwitchStage(
        company=data["company"],
        stage_name=data["stage_name"],
        status=data.get("status", "active"),
        user_id=current_user.id,
    )
    db.session.add(stage)
    db.session.commit()
    return jsonify(stage.to_dict()), 201


@app.route("/stages", methods=["GET"])
@login_required
def list_stages():
    stages = JobSwitchStage.query.filter_by(user_id=current_user.id).all()
    return jsonify([s.to_dict() for s in stages])


@app.route("/stages/<int:stage_id>", methods=["GET"])
@login_required
def get_stage(stage_id):
    return jsonify(own_stage_or_404(stage_id).to_dict())


@app.route("/stages/<int:stage_id>", methods=["PUT"])
@login_required
def update_stage(stage_id):
    stage = own_stage_or_404(stage_id)
    data = request.get_json(silent=True) or {}
    stage.company = data.get("company", stage.company)
    stage.stage_name = data.get("stage_name", stage.stage_name)
    stage.status = data.get("status", stage.status)
    db.session.commit()
    return jsonify(stage.to_dict())


@app.route("/stages/<int:stage_id>", methods=["DELETE"])
@login_required
def delete_stage(stage_id):
    stage = own_stage_or_404(stage_id)
    db.session.delete(stage)
    db.session.commit()
    return "", 204


# ---------- Debug route ----------

@app.route("/debug/counts")
@login_required
def debug_counts():
    return {
        "learning_entries": LearningEntry.query.filter_by(user_id=current_user.id).count(),
        "job_switch_stages": JobSwitchStage.query.filter_by(user_id=current_user.id).count(),
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
