from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable

from flask import Flask, jsonify, redirect, render_template, request, url_for

DB_PATH = Path("templates.db")

app = Flask(__name__)


@dataclass
class ResponseTemplate:
    id: int
    name: str
    body: str


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS response_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            body TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def fetch_templates() -> list[ResponseTemplate]:
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, body FROM response_templates ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [ResponseTemplate(id=row["id"], name=row["name"], body=row["body"]) for row in rows]


def extract_keywords(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
    stop_words = {
        "this",
        "that",
        "with",
        "from",
        "have",
        "would",
        "about",
        "your",
        "thanks",
        "hello",
        "regards",
        "please",
    }
    return {w for w in words if w not in stop_words}


def score_template(incoming_email: str, template_body: str) -> float:
    keyword_overlap = len(extract_keywords(incoming_email) & extract_keywords(template_body))
    ratio = SequenceMatcher(None, incoming_email.lower(), template_body.lower()).ratio()
    # Weighted score balancing semantic overlap and fuzzy similarity.
    return (keyword_overlap * 0.7) + (ratio * 10)


def improvement_suggestions(email_text: str, template_text: str) -> list[str]:
    suggestions: list[str] = []
    email_has_question = "?" in email_text
    template_has_question_response = bool(
        re.search(r"(can|could|will|we can|i can|let me)", template_text.lower())
    )

    if email_has_question and not template_has_question_response:
        suggestions.append("Address the sender's question directly with a clear yes/no or next step.")

    if len(template_text.split()) < 30:
        suggestions.append("Add more context so the reply does not feel too brief.")

    if "thank" not in template_text.lower():
        suggestions.append("Add a short appreciation line to keep the tone warm.")

    if not re.search(r"(next step|timeline|date|by )", template_text.lower()):
        suggestions.append("Include a concrete timeline or next step for clarity.")

    if not suggestions:
        suggestions.append("Template is already strong. Consider personalizing with the sender's name.")

    return suggestions


def rank_templates(incoming_email: str, templates: Iterable[ResponseTemplate]) -> list[dict]:
    ranked: list[dict] = []
    for template in templates:
        score = score_template(incoming_email, template.body)
        ranked.append(
            {
                "id": template.id,
                "name": template.name,
                "body": template.body,
                "score": round(score, 2),
                "suggestions": improvement_suggestions(incoming_email, template.body),
            }
        )

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked


@app.route("/", methods=["GET"])
def home():
    templates = fetch_templates()
    return render_template("index.html", templates=templates)


@app.route("/templates", methods=["POST"])
def create_template():
    name = request.form.get("name", "").strip()
    body = request.form.get("body", "").strip()

    if not name or not body:
        return redirect(url_for("home"))

    conn = get_db()
    conn.execute(
        "INSERT INTO response_templates (name, body) VALUES (?, ?)",
        (name, body),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("home"))


@app.route("/analyze", methods=["POST"])
def analyze_email():
    incoming_email = request.form.get("incoming_email", "").strip()
    if not incoming_email:
        return jsonify({"error": "incoming_email is required"}), 400

    ranked = rank_templates(incoming_email, fetch_templates())
    best_match = ranked[0] if ranked else None

    return render_template(
        "analysis.html",
        incoming_email=incoming_email,
        best_match=best_match,
        all_matches=ranked,
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
