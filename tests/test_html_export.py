from vocab_collector import html_export


def test_render_escapes_malicious_values():
    rows = [("<b>&x", "中文", "AI", "2026-01-01T00:00:00+00:00")]
    output = html_export.render(rows)

    assert "&lt;b&gt;&amp;x" in output
    assert "<b>&x" not in output


def test_render_is_utf8_and_complete_document():
    output = html_export.render([("w", "中文", "AI", "t")])
    assert "<!doctype html>" in output
    assert 'charset="utf-8"' in output
    assert "中文" in output


def test_render_supports_emoji_and_escapes_junk():
    output = html_export.render([("w", "🙂 & <x>", "AI", "t")])
    assert "🙂" in output
    assert "&lt;x&gt;" in output


def test_render_has_all_headers():
    output = html_export.render([])
    for header in ("english", "chinese", "domain", "created_at"):
        assert f"<th>{header}</th>" in output


def test_write_atomic_replaces_and_leaves_no_tmp(tmp_path):
    target = tmp_path / "vocabulary.html"

    html_export.write_atomic(target, "one")
    assert target.read_text(encoding="utf-8") == "one"

    html_export.write_atomic(target, "two")
    assert target.read_text(encoding="utf-8") == "two"
    assert not (tmp_path / "vocabulary.html.tmp").exists()