"""Versioned SQLite storage. No model output becomes a confirmed decision implicitly."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from uuid import uuid4


def new_id():
    return uuid4().hex


def now():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


SCHEMA = """
CREATE TABLE projects(id TEXT PRIMARY KEY, name TEXT NOT NULL, goal TEXT NOT NULL,
 instructions TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE sources(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
 title TEXT NOT NULL, kind TEXT NOT NULL, active_version_id TEXT,
 UNIQUE(project_id, title));
CREATE TABLE source_versions(id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(id),
 sha256 TEXT NOT NULL, original BLOB NOT NULL, warnings_json TEXT NOT NULL, imported_at TEXT NOT NULL,
 UNIQUE(source_id, sha256));
CREATE TABLE chunks(id TEXT PRIMARY KEY, version_id TEXT NOT NULL REFERENCES source_versions(id),
 text TEXT NOT NULL, page INTEGER, line_start INTEGER, line_end INTEGER);
CREATE VIRTUAL TABLE chunks_fts USING fts5(chunk_id UNINDEXED, text, tokenize='unicode61 remove_diacritics 2');
CREATE TABLE decisions(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
 text TEXT NOT NULL, confirmed_at TEXT NOT NULL);
CREATE TABLE runs(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
 task TEXT NOT NULL, adapter TEXT NOT NULL, state TEXT NOT NULL
 CHECK(state IN ('running','completed','failed')), context_json TEXT NOT NULL,
 context_hash TEXT NOT NULL, output TEXT, validation_json TEXT, error TEXT,
 created_at TEXT NOT NULL, finished_at TEXT);
"""


class Store:
    def __init__(self, home):
        self.home = Path(home).expanduser()
        self.home.mkdir(parents=True, exist_ok=True)
        self.path = self.home / "atlas.sqlite3"
        with self.connect() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > 1:
                raise ValueError("Database was created by a newer Atlas version")
            if version == 0:
                db.executescript("BEGIN IMMEDIATE;\n" + SCHEMA + "\nPRAGMA user_version=1; COMMIT;")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def projects(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM projects ORDER BY created_at, id")]

    def project(self, project_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
            if not row:
                raise ValueError("Project does not exist")
            return dict(row)

    def create_project(self, name, goal="", instructions=""):
        if not name.strip():
            raise ValueError("Project name is required")
        project_id = new_id()
        with self.connect() as db:
            db.execute("INSERT INTO projects VALUES(?,?,?,?,?)",
                       (project_id, name.strip(), goal, instructions, now()))
        return project_id

    def sources(self, project_id):
        with self.connect() as db:
            return [dict(r) for r in db.execute(
                "SELECT s.*, v.sha256, v.warnings_json, v.imported_at FROM sources s JOIN source_versions v "
                "ON v.id=s.active_version_id WHERE s.project_id=? ORDER BY s.title", (project_id,))]

    def import_source(self, project_id, title, kind, original, chunks, warnings=()):
        """An exact title identifies a source. Re-importing old bytes reactivates its version."""
        self.project(project_id)
        if not title.strip() or not chunks:
            raise ValueError("A source needs a title and extractable content")
        digest = hashlib.sha256(original).hexdigest()
        with self.connect() as db:
            source = db.execute("SELECT * FROM sources WHERE project_id=? AND title=?",
                                (project_id, title)).fetchone()
            source_id = source["id"] if source else new_id()
            if source and source["kind"] != kind:
                raise ValueError("Source kind cannot change under the same title")
            if not source:
                db.execute("INSERT INTO sources VALUES(?,?,?,?,NULL)", (source_id, project_id, title, kind))
            existing = db.execute("SELECT id FROM source_versions WHERE source_id=? AND sha256=?",
                                  (source_id, digest)).fetchone()
            version_id = existing["id"] if existing else new_id()
            if not existing:
                db.execute("INSERT INTO source_versions VALUES(?,?,?,?,?,?)",
                           (version_id, source_id, digest, original, canonical(list(warnings)), now()))
                for chunk in chunks:
                    chunk_id = new_id()
                    db.execute("INSERT INTO chunks VALUES(?,?,?,?,?,?)", (chunk_id, version_id,
                               chunk["text"], chunk.get("page"), chunk.get("line_start"), chunk.get("line_end")))
                    db.execute("INSERT INTO chunks_fts VALUES(?,?)", (chunk_id, chunk["text"]))
            db.execute("UPDATE sources SET active_version_id=? WHERE id=?", (version_id, source_id))
        return source_id, version_id

    def chunks(self, project_id, source_ids):
        available = {s["id"] for s in self.sources(project_id)}
        if not set(source_ids) <= available:
            raise ValueError("Selected source does not belong to this project")
        if not source_ids:
            return []
        marks = ",".join("?" for _ in source_ids)
        with self.connect() as db:
            return [dict(r) for r in db.execute(
                "SELECT c.*, s.id AS source_id, s.title FROM chunks c JOIN sources s "
                f"ON s.active_version_id=c.version_id WHERE s.project_id=? AND s.id IN ({marks}) "
                "ORDER BY s.title, c.page, c.line_start, c.rowid", (project_id, *source_ids))]

    def search_ids(self, project_id, query):
        # Filter by project and active version before ranking.
        with self.connect() as db:
            return [r[0] for r in db.execute(
                "SELECT chunks_fts.chunk_id FROM chunks_fts JOIN chunks c ON c.id=chunks_fts.chunk_id "
                "JOIN sources s ON s.active_version_id=c.version_id "
                "WHERE s.project_id=? AND chunks_fts MATCH ? ORDER BY rank", (project_id, query))]

    def decisions(self, project_id):
        with self.connect() as db:
            return [dict(r) for r in db.execute(
                "SELECT * FROM decisions WHERE project_id=? ORDER BY confirmed_at, id", (project_id,))]

    def confirm_decision(self, project_id, text):
        self.project(project_id)
        if not text.strip():
            raise ValueError("Decision must not be empty")
        with self.connect() as db:
            db.execute("INSERT INTO decisions VALUES(?,?,?,?)", (new_id(), project_id, text.strip(), now()))

    def start_run(self, project_id, packet, adapter):
        self.project(project_id)
        if packet["project"]["id"] != project_id:
            raise ValueError("Context project mismatch")
        encoded = canonical(packet)
        run_id = new_id()
        with self.connect() as db:
            db.execute("INSERT INTO runs(id,project_id,task,adapter,state,context_json,context_hash,created_at) "
                       "VALUES(?,?,?,?,'running',?,?,?)", (run_id, project_id, packet["task"], adapter,
                       encoded, hashlib.sha256(encoded.encode()).hexdigest(), now()))
        return run_id

    def finish_run(self, run_id, *, output=None, validation=None, error=None):
        with self.connect() as db:
            changed = db.execute("UPDATE runs SET state=?, output=?, validation_json=?, error=?, finished_at=? "
                                 "WHERE id=? AND state='running'", (
                                 "failed" if error else "completed", output, canonical(validation or {}),
                                 error, now(), run_id)).rowcount
            if not changed:
                raise ValueError("Run is missing or already finished")

    def runs(self, project_id):
        with self.connect() as db:
            return [dict(r) for r in db.execute(
                "SELECT * FROM runs WHERE project_id=? ORDER BY created_at DESC, id", (project_id,))]
