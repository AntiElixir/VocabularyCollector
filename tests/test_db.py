from vocab_collector import db


def _conn(tmp_path):
    conn = db.connect(tmp_path / "vocabulary.db")
    db.init_schema(conn)
    return conn


def test_insert_then_duplicate_is_case_insensitive(tmp_path):
    conn = _conn(tmp_path)
    assert db.insert_word(conn, "robustness", "稳健性", "AI", "2026-01-01T00:00:00+00:00") is True
    assert db.insert_word(conn, "Robustness", "稳健性", "AI", "2026-01-02T00:00:00+00:00") is False

    rows = db.list_all(conn)
    assert len(rows) == 1
    assert rows[0][0] == "robustness"
    assert rows[0][1] == "稳健性"
    assert rows[0][2] == "AI"


def test_init_schema_is_idempotent(tmp_path):
    conn = db.connect(tmp_path / "vocabulary.db")
    db.init_schema(conn)
    db.init_schema(conn)
    assert db.list_all(conn) == []


def test_list_all_is_newest_first(tmp_path):
    conn = _conn(tmp_path)
    db.insert_word(conn, "one", "一", "AI", "2026-01-01T00:00:00+00:00")
    db.insert_word(conn, "two", "二", "AI", "2026-01-03T00:00:00+00:00")
    db.insert_word(conn, "three", "三", "AI", "2026-01-02T00:00:00+00:00")
    assert [row[0] for row in db.list_all(conn)] == ["two", "three", "one"]


def test_reserved_fsrs_columns_exist_and_are_nullable(tmp_path):
    conn = _conn(tmp_path)
    columns = {row[1]: row for row in conn.execute("PRAGMA table_info(vocabulary)")}
    for name in (
        "fsrs_state",
        "fsrs_step",
        "fsrs_stability",
        "fsrs_difficulty",
        "fsrs_due",
        "fsrs_last_review",
    ):
        assert name in columns
    db.insert_word(conn, "w", "中", "AI", "2026-01-01T00:00:00+00:00")
    row = conn.execute("SELECT fsrs_state, fsrs_due FROM vocabulary").fetchone()
    assert row == (None, None)