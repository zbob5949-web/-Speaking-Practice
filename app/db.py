import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  phone TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'user',
  is_active INTEGER NOT NULL DEFAULT 1,
  is_super_admin INTEGER NOT NULL DEFAULT 0,
  last_login_ip TEXT,
  last_login TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_profile (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  learning_goal TEXT NOT NULL,
  total_days INTEGER NOT NULL,
  daily_minutes INTEGER NOT NULL,
  current_level TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS learning_plan (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  profile_id INTEGER NOT NULL,
  day_index INTEGER NOT NULL,
  topic TEXT NOT NULL,
  scenario TEXT NOT NULL,
  objective TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  skill_focus TEXT,
  communicative_task TEXT,
  target_functions_json TEXT,
  success_criteria_json TEXT,
  brief_seed TEXT,
  FOREIGN KEY(profile_id) REFERENCES user_profile(id)
);

CREATE TABLE IF NOT EXISTS daily_sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  plan_day_id INTEGER,
  scenario_id TEXT,
  profile_id INTEGER,
  day_index INTEGER NOT NULL,
  topic TEXT NOT NULL,
  started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ended_at TEXT,
  summary TEXT,
  overall_score INTEGER
);

CREATE TABLE IF NOT EXISTS conversation_turns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  turn_index INTEGER NOT NULL,
  speaker TEXT NOT NULL,
  text TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(session_id) REFERENCES daily_sessions(id)
);

CREATE TABLE IF NOT EXISTS inline_feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  turn_id INTEGER,
  feedback_type TEXT NOT NULL,
  feedback_text TEXT NOT NULL,
  original_fragment TEXT,
  better_expression TEXT,
  reason_zh TEXT,
  example_sentence TEXT,
  severity TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS session_feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  report TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS error_bank (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  original_sentence TEXT NOT NULL,
  corrected_sentence TEXT NOT NULL,
  better_expression TEXT NOT NULL,
  error_type TEXT NOT NULL,
  explanation TEXT NOT NULL,
  source_session_id INTEGER NOT NULL,
  review_count INTEGER NOT NULL DEFAULT 0,
  last_reviewed_at TEXT
);

CREATE TABLE IF NOT EXISTS expression_bank (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  expression TEXT NOT NULL,
  meaning TEXT NOT NULL,
  usage_context TEXT NOT NULL,
  example_sentence TEXT NOT NULL,
  source_session_id INTEGER NOT NULL,
  review_count INTEGER NOT NULL DEFAULT 0,
  last_reviewed_at TEXT
);

CREATE TABLE IF NOT EXISTS memory_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  snapshot TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prompts (
  name TEXT PRIMARY KEY,
  content TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_reviews (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  profile_id INTEGER NOT NULL,
  review_date TEXT NOT NULL,
  status TEXT NOT NULL,
  user_report_json TEXT,
  structured_analysis_json TEXT,
  source_session_ids_json TEXT,
  raw_agent_output TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS memory_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  profile_id INTEGER NOT NULL,
  category TEXT NOT NULL,
  content TEXT NOT NULL,
  evidence TEXT NOT NULL,
  confidence REAL NOT NULL,
  status TEXT NOT NULL,
  source_review_id INTEGER,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS plan_adjustments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  target_plan_day_id INTEGER NOT NULL,
  source_review_id INTEGER NOT NULL,
  adjustment_type TEXT NOT NULL,
  title TEXT NOT NULL,
  rationale TEXT NOT NULL,
  instruction TEXT NOT NULL,
  priority TEXT NOT NULL,
  status TEXT NOT NULL,
  expires_after_days INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS practice_briefs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  plan_day_id INTEGER NOT NULL,
  brief_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS favorites (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  profile_id INTEGER NOT NULL,
  scenario_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(profile_id, scenario_id),
  FOREIGN KEY(profile_id) REFERENCES user_profile(id)
);

CREATE TABLE IF NOT EXISTS agent_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  profile_id INTEGER,
  plan_day_id INTEGER,
  session_id INTEGER,
  agent_name TEXT NOT NULL,
  trigger_source TEXT NOT NULL,
  input_json TEXT NOT NULL,
  tool_calls_json TEXT NOT NULL,
  output_json TEXT NOT NULL,
  validation_status TEXT NOT NULL,
  error_message TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(db_path: Path) -> None:
    with connect(db_path) as connection:
        connection.executescript(SCHEMA)
        try:
            connection.execute("ALTER TABLE daily_sessions ADD COLUMN plan_day_id INTEGER")
            connection.commit()
        except sqlite3.OperationalError:
            pass

        for statement in (
            "ALTER TABLE daily_sessions ADD COLUMN scenario_id TEXT",
            "ALTER TABLE daily_sessions ADD COLUMN profile_id INTEGER",
        ):
            try:
                connection.execute(statement)
                connection.commit()
            except sqlite3.OperationalError:
                pass

        for statement in (
            "ALTER TABLE learning_plan ADD COLUMN skill_focus TEXT",
            "ALTER TABLE learning_plan ADD COLUMN communicative_task TEXT",
            "ALTER TABLE learning_plan ADD COLUMN target_functions_json TEXT",
            "ALTER TABLE learning_plan ADD COLUMN success_criteria_json TEXT",
            "ALTER TABLE learning_plan ADD COLUMN brief_seed TEXT",
        ):
            try:
                connection.execute(statement)
                connection.commit()
            except sqlite3.OperationalError:
                pass

        for statement in (
            "ALTER TABLE inline_feedback ADD COLUMN original_fragment TEXT",
            "ALTER TABLE inline_feedback ADD COLUMN better_expression TEXT",
            "ALTER TABLE inline_feedback ADD COLUMN reason_zh TEXT",
            "ALTER TABLE inline_feedback ADD COLUMN example_sentence TEXT",
            "ALTER TABLE inline_feedback ADD COLUMN severity TEXT",
        ):
            try:
                connection.execute(statement)
                connection.commit()
            except sqlite3.OperationalError:
                pass
                
        # Force prompt reload for inline_feedback updates
        connection.execute("DELETE FROM prompts WHERE name IN ('inline_feedback_system', 'inline_feedback_user_template')")
        connection.commit()

        connection.commit()
