import os
from flask import Flask, request, jsonify
from models import db, LearningEntry, JobSwitchStage

app = Flask(__name__)

# Read connection details from environment variables (set via ConfigMap/Secret in Kubernetes).
# Falls back to local SQLite if these aren't set, so the app still runs fine
# outside Kubernetes (e.g. plain `docker run` from earlier weeks).
db_host = os.environ.get("POSTGRES_HOST")
db_name = os.environ.get("POSTGRES_DB")
db_password = os.environ.get("POSTGRES_PASSWORD")
db_user = os.environ.get("POSTGRES_USER", "postgres")

if db_host and db_name and db_password:
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"postgresql://{db_user}:{db_password}@{db_host}:5432/{db_name}"
    )
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tracker.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()


@app.route("/")
def home():
    return "Learning tracker is alive, Huuhuuu!!!"


# ---------- LearningEntry CRUD ----------

@app.route("/entries", methods=["POST"])
def create_entry():
    data = request.get_json()
    entry = LearningEntry(
        topic=data.get("topic"),
        hours_spent=data.get("hours_spent", 0.0),
        notes=data.get("notes"),
    )
    db.session.add(entry)
    db.session.commit()
    return jsonify(entry.to_dict()), 201


@app.route("/entries", methods=["GET"])
def list_entries():
    entries = LearningEntry.query.all()
    return jsonify([e.to_dict() for e in entries])


@app.route("/entries/<int:entry_id>", methods=["GET"])
def get_entry(entry_id):
    entry = LearningEntry.query.get_or_404(entry_id)
    return jsonify(entry.to_dict())


@app.route("/entries/<int:entry_id>", methods=["PUT"])
def update_entry(entry_id):
    entry = LearningEntry.query.get_or_404(entry_id)
    data = request.get_json()
    entry.topic = data.get("topic", entry.topic)
    entry.hours_spent = data.get("hours_spent", entry.hours_spent)
    entry.notes = data.get("notes", entry.notes)
    db.session.commit()
    return jsonify(entry.to_dict())


@app.route("/entries/<int:entry_id>", methods=["DELETE"])
def delete_entry(entry_id):
    entry = LearningEntry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    return "", 204


# ---------- JobSwitchStage CRUD ----------

@app.route("/stages", methods=["POST"])
def create_stage():
    data = request.get_json()
    stage = JobSwitchStage(
        company=data.get("company"),
        stage_name=data.get("stage_name"),
        status=data.get("status", "active"),
    )
    db.session.add(stage)
    db.session.commit()
    return jsonify(stage.to_dict()), 201


@app.route("/stages", methods=["GET"])
def list_stages():
    stages = JobSwitchStage.query.all()
    return jsonify([s.to_dict() for s in stages])


@app.route("/stages/<int:stage_id>", methods=["GET"])
def get_stage(stage_id):
    stage = JobSwitchStage.query.get_or_404(stage_id)
    return jsonify(stage.to_dict())


@app.route("/stages/<int:stage_id>", methods=["PUT"])
def update_stage(stage_id):
    stage = JobSwitchStage.query.get_or_404(stage_id)
    data = request.get_json()
    stage.company = data.get("company", stage.company)
    stage.stage_name = data.get("stage_name", stage.stage_name)
    stage.status = data.get("status", stage.status)
    db.session.commit()
    return jsonify(stage.to_dict())


@app.route("/stages/<int:stage_id>", methods=["DELETE"])
def delete_stage(stage_id):
    stage = JobSwitchStage.query.get_or_404(stage_id)
    db.session.delete(stage)
    db.session.commit()
    return "", 204


# ---------- Debug route ----------

@app.route("/debug/counts")
def debug_counts():
    return {
        "learning_entries": LearningEntry.query.count(),
        "job_switch_stages": JobSwitchStage.query.count(),
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
