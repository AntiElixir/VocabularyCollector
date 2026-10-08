"""Flask web service for vocabulary browsing."""

from __future__ import annotations

import logging
import sqlite3
import threading
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from . import db
from .config import WebConfig

_LOG = logging.getLogger(__name__)


def create_app(conn: sqlite3.Connection, templates_dir: Path) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder=str(templates_dir),
        static_folder=None,
    )
    app.config["CONN"] = conn
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.jinja_env.auto_reload = True

    @app.route("/")
    def index():
        response = app.make_response(render_template("index.html"))
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @app.route("/api/words")
    def get_words():
        query = request.args.get("q", "").strip()
        offset = request.args.get("offset", 0, type=int)
        limit = request.args.get("limit", 20, type=int)
        limit = min(limit, 100)

        words = db.search_words(conn, query, offset, limit)
        return jsonify({
            "words": [
                {
                    "id": w[0],
                    "english": w[1],
                    "chinese": w[2],
                    "domain": w[3],
                    "created_at": w[4],
                }
                for w in words
            ]
        })

    @app.route("/api/words/<int:word_id>", methods=["DELETE"])
    def delete_word(word_id):
        deleted = db.delete_word(conn, word_id)
        if deleted:
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": "not found"}), 404

    @app.route("/api/words/<int:word_id>", methods=["PUT"])
    def update_word(word_id):
        body = request.get_json(silent=True) or {}
        new_chinese = (body.get("chinese") or "").strip()
        if not new_chinese:
            return jsonify({"ok": False, "error": "chinese is required"}), 400
        updated = db.update_chinese(conn, word_id, new_chinese)
        if updated:
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": "not found"}), 404

    @app.route("/api/stats")
    def get_stats():
        query = request.args.get("q", "").strip()
        total = db.count_words(conn, query)
        weekly = db.get_weekly_count(conn)
        domains = db.get_domain_count(conn)
        return jsonify({
            "total": total,
            "weekly": weekly,
            "domains": domains,
        })

    return app


class WebServer:
    """Background web server that serves the vocabulary UI."""

    def __init__(self, config: WebConfig, conn: sqlite3.Connection, templates_dir: Path):
        self._config = config
        self._conn = conn
        self._templates_dir = templates_dir
        self._app: Flask | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the web server in a background thread."""
        self._app = create_app(self._conn, self._templates_dir)
        self._app.logger.setLevel(logging.WARNING)

        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="web-server",
        )
        self._thread.start()
        _LOG.info("web server started at http://%s:%d/", self._config.host, self._config.port)

    def _run(self) -> None:
        assert self._app is not None
        self._app.run(
            host=self._config.host,
            port=self._config.port,
            debug=False,
            use_reloader=False,
        )

    def stop(self) -> None:
        """Stop the web server (daemon thread will exit with the process)."""
        _LOG.info("web server stopping")
