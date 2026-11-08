-- OMEGA AI — SQLite memory schema (v0.1.0, 2026-11-07)
-- Mirrors YAHYA_AI_COMMAND_CENTER memory/long_term.py concepts.
-- Seed from ~/workspace/muse_omega/MUSE_MEMORY/ (real rows only; empty stays empty).

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS projects (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  name          TEXT NOT NULL UNIQUE,
  objective     TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','planning','running','waiting','testing','completed','failed')),
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tasks (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id    INTEGER NOT NULL REFERENCES projects(id),
  agent_id      TEXT NOT NULL,
  title         TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','planning','running','waiting','testing','completed','failed')),
  result_path   TEXT,
  error         TEXT,
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS decisions (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  title         TEXT NOT NULL,
  rationale     TEXT,
  decided_at    TEXT NOT NULL DEFAULT (datetime('now')),
  superseded_by INTEGER REFERENCES decisions(id)
);

CREATE TABLE IF NOT EXISTS memory_entries (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  kind          TEXT NOT NULL
                CHECK (kind IN ('instruction','project','decision','tool','error','research','finding')),
  title         TEXT NOT NULL,
  body          TEXT NOT NULL,
  source        TEXT,
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_memory_kind ON memory_entries(kind);
CREATE INDEX IF NOT EXISTS idx_memory_created ON memory_entries(created_at);

CREATE TABLE IF NOT EXISTS tools (
  id            TEXT PRIMARY KEY,
  name          TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'unverified'
                CHECK (status IN ('verified','unverified','broken')),
  last_verified TEXT,
  notes         TEXT
);

CREATE TABLE IF NOT EXISTS errors (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id       INTEGER REFERENCES tasks(id),
  message       TEXT NOT NULL,
  solution      TEXT,
  occurred_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS activity_log (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  actor         TEXT NOT NULL,
  action        TEXT NOT NULL,
  detail        TEXT,
  at            TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_activity_at ON activity_log(at);
