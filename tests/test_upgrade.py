"""due_date 칼럼이 없던 DB (add-mvp-core 시절) 를 서버 시작 때 맞추는지."""
import sqlite3

from backend import db


def make_old_db(path):
    c = sqlite3.connect(path)
    c.executescript("""
    CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR(255) UNIQUE, password_hash VARCHAR(255), name VARCHAR(100), created_at DATETIME);
    CREATE TABLE teams (id INTEGER PRIMARY KEY, name VARCHAR(100), invite_code VARCHAR(20) UNIQUE, owner_id INTEGER, created_at DATETIME);
    CREATE TABLE meetings (id INTEGER PRIMARY KEY, team_id INTEGER, title VARCHAR(200), met_at DATETIME, attendees VARCHAR(500),
      body TEXT, summary TEXT, decisions TEXT, author_id INTEGER, created_at DATETIME);
    CREATE TABLE todos (id INTEGER PRIMARY KEY, team_id INTEGER, meeting_id INTEGER, what VARCHAR(500), due_text VARCHAR(100),
      status VARCHAR(10), assignee_id INTEGER, author_id INTEGER, created_at DATETIME);
    INSERT INTO users VALUES (1, 'a@example.com', 'x', '김대리', '2026-11-01 00:00:00');
    INSERT INTO teams VALUES (1, '기획팀', 'MN-AAAA', 1, '2026-11-01 00:00:00');
    INSERT INTO meetings VALUES (1, 1, '회의', '2026-11-12 05:00:00', '', '본문', '', '', 1, '2026-11-12 06:00:00');
    INSERT INTO todos VALUES (1, 1, 1, '목록 정리', '다음 주 금요일', 'OPEN', NULL, 1, '2026-11-12 06:00:00');
    INSERT INTO todos VALUES (2, 1, 1, '조사', '이번 주 안', 'OPEN', NULL, 1, '2026-11-12 06:00:00');
    INSERT INTO todos VALUES (3, 1, NULL, '직접', '내일', 'OPEN', NULL, 1, '2026-11-12 16:00:00');
    INSERT INTO todos VALUES (4, 1, NULL, '기한 없음', '', 'OPEN', NULL, 1, '2026-11-12 16:00:00');
    """)
    c.commit()
    c.close()


def test_upgrade_adds_column_and_fills(tmp_path):
    path = tmp_path / "old.db"
    make_old_db(path)
    db.init_engine(f"sqlite:///{path.as_posix()}")
    db.create_all()
    c = sqlite3.connect(path)
    assert "due_date" in [r[1] for r in c.execute("pragma table_info(todos)")]
    got = dict(c.execute("select id, due_date from todos"))
    assert got == {1: "2026-11-20", 2: None, 3: "2026-11-14", 4: None}  # 3: 등록 UTC 16:00 = 한국 11-13, 그 다음 날
    c.close()

    # 두 번째 시작 - 칼럼을 다시 만들지 않고 값도 그대로
    db.create_all()
    assert dict(sqlite3.connect(path).execute("select id, due_date from todos")) == got


def test_upgrade_keeps_existing_values(tmp_path):
    path = tmp_path / "old.db"
    make_old_db(path)
    c = sqlite3.connect(path)
    c.execute("ALTER TABLE todos ADD COLUMN due_date DATE")
    c.execute("UPDATE todos SET due_date='2030-01-01' WHERE id=1")
    c.commit()
    c.close()
    db.init_engine(f"sqlite:///{path.as_posix()}")
    db.create_all()
    assert dict(sqlite3.connect(path).execute("select id, due_date from todos"))[1] == "2030-01-01"
