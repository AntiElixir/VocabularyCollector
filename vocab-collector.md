# vocab-collector - Work Plan

## TL;DR (For humans)

**What you'll get:** A tiny Windows background tool. You highlight an English word anywhere (browser, PDF, VS Code, Obsidian) and press `Ctrl+C+C`; it quietly asks your SJTU LLM for the Chinese meaning and discipline, saves it to a local database, and refreshes a simple web page you can open to browse your words. It starts by double-clicking one file and needs no Python, Node, or installer.

**Why this approach:** The whole thing is one small Python program. It listens passively for the double-copy gesture (it never blocks or replaces normal copying), reads what your own `Ctrl+C` already put on the clipboard, and uses your verified `deepseek-chat` endpoint with strict JSON output. SQLite and the settings file live in the same folder as the program, so the folder is portable.

**What it will NOT do:** No popup, no GUI window, no browser extension, no Anki, no FSRS review logic (fields are reserved only), no reminders, no cloud, no server. Nothing beyond what you asked for.

**Effort:** Medium
**Risk:** Medium - the Windows gesture + first-run packaging are the two places this can bite.
**Decisions to sanity-check:** HTML view is a plain regenerated table (no filter box, no viewer command - deliberately minimal); failed API calls are logged with the word but not retried/queued; the app logs to a file (never a console window).

Your next move: approve, then hand this plan to your Windows agent (or run `$start-work`). Full execution detail follows below.

---

> TL;DR (machine): Medium effort / Medium risk. 18 implementation todos + 4 final-verification tasks. Portable Windows Python tool: pynput passive Ctrl+C+C hook, clipboard freshness-gated read, SJTU OpenAI-compatible `json_schema` strict call, Pydantic validation, SQLite dedup, static regenerated HTML, PyInstaller onedir.

## Scope

### Must have
- **Config:** `config/config.example.toml` committed; real `config/config.toml` gitignored; loaded with stdlib `tomllib`; every key of `{base_url, api_key, model, timeout_seconds, max_retries, max_selection_chars, double_tap_window_ms, clipboard_wait_ms, log_level}` configurable. `config.example.toml` is pre-filled with the verified SJTU endpoint (`https://models.sjtu.edu.cn/api/v1`, model `deepseek-chat`) and a placeholder key.
- **Global gesture:** passive `WH_KEYBOARD_LL` listener (pynput) detecting *Ctrl held + C tapped twice* within a configurable window; matches by **virtual-key code** (`VK_C=0x43`, `VK_LCONTROL=0xA2`, `VK_RCONTROL=0xA3`), requires a key-up between taps, resets on any other key / Ctrl release / timeout. The listener only enqueues work; it never performs slow work in the hook callback.
- **Capture:** record `GetClipboardSequenceNumber()` at the first C tap; on trigger, wait (bounded, configurable) for the sequence to change; if it does not change, **abort - never read a possibly stale clipboard**. Read plain text via `pyperclip` with a bounded retry for clipboard contention. Sanitize: strip, collapse internal whitespace, reject empty / multi-line / over-length / no-ASCII-letter.
- **LLM:** official `openai` SDK against the configured `base_url`. Primary: `response_format={"type":"json_schema","json_schema":{"name":"vocab","strict":true,"schema":{...}}}` (verified HTTP 200 on the vLLM backend). Fallback on a `response_format`-rejection error: `{"type":"json_object"}` with the schema embedded in the prompt. Then strip markdown fences, `json.loads`, validate with a Pydantic v2 model (all three fields non-empty). **Any failure = log the captured word + reason and write nothing to the DB.**
- **Storage:** stdlib `sqlite3`, single file `data/vocabulary.db`. Minimal MVP columns + nullable FSRS-reserved columns (no FSRS logic). Duplicates ignored, first-wins, case-insensitive.
- **HTML:** after every successful insert, regenerate a single self-contained `data/vocabulary.html` (UTF-8, `<meta charset="utf-8">`, all values HTML-escaped, plain table of english/chinese/domain/created_at sorted newest-first). Written atomically (temp file + `os.replace`). No server, no framework, no client-side script.
- **Runtime:** background process, no window; rotating file log `data/collector.log` (1 MB x 3, UTF-8); console logging only when `sys.stdout`/`sys.stderr` exist (dev); `sys.excepthook` + `threading.excepthook` routed to the log so the process never dies silently; `data/` and `config/` created on startup if missing.
- **Packaging:** PyInstaller onedir, `--noconsole`, no UPX, explicit pynput backend hidden imports; `config/` and `data/` resolved beside the exe via `os.path.dirname(sys.executable)` (never `sys._MEIPASS`). Build script copies only `config.example.toml` into `dist/config/`; the real `config.toml` is never bundled.
- **Tests:** pytest; TDD for pure logic; tests-after for wiring; one hermetic Windows E2E using a local stub LLM server + Notepad.

### Must NOT have (guardrails, anti-slop, scope boundaries)
No GUI window, tray icon, popup, toast, sound, or on-hover definition. No browser extension, PDF plugin, OCR. No Anki / AnkiConnect. No FSRS scheduling/algorithm (reserved columns only). No reminders. No Hermes. No auth, accounts, cloud sync, server, online DB. No statistics, tests/quizzes, flashcards, phonetics, TTS, example sentences, difficulty rating, auto-highlight. No HTML filter box / search UI / `view` command (open the generated file directly). No web framework, no JS build chain, no Electron/Node/Qt. No retry queue or offline spool for failed captures. No multi-instance logic. No autostart registration. All of the excluded items live only as a plan TODO comment, never as code.

## Verification strategy
> Zero human intervention - all verification is agent-executed (Windows E2E runs on the Windows host the implementer uses).
- Test decision: **TDD** for `paths`, `config`, `models`, `db`, `clipboard.sanitize`, `llm` parsing (mocked client), `hotkey.TapStateMachine`, `html_export`; **tests-after** for `logging_setup`, `pipeline`, `__main__` wiring. Framework: `pytest` (+ `pytest-mock`), Windows-E2E tests marked `windows_e2e`.
- Evidence: `.omo/evidence/task-<N>-vocab-collector.<ext>` (logs, pytest output, DB dumps, generated HTML, sha256 of dist).
- Hermetic LLM: E2E starts a local `http.server` stub returning canned chat-completions JSON, so tests never depend on network or the real key.
- Build hygiene: `grep` the built `dist/` tree for the real key pattern and for `config/config.toml`; both must be absent.

## Execution strategy
### Parallel execution waves
> 5-8 todos per wave.
- **Wave 1 - Foundation:** T1 scaffold, T2 paths, T3 config, T4 models, T5 db.
- **Wave 2 - Core pipeline:** T6 llm, T7 clipboard, T8 hotkey, T9 logging, T10 pipeline.
- **Wave 3 - Output & entry:** T11 html_export, T12 __main__ entry, T13 README + limitations.
- **Wave 4 - Package & prove:** T14 PyInstaller spec + build script, T15 build hygiene, T16 Windows listener smoke, T17 hermetic E2E, T18 failure-path E2E.

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| T1 | - | T2..T18 | - |
| T2 | T1 | T3,T5,T9,T11 | T4 |
| T3 | T1,T2 | T6,T7,T10 | T4,T5 |
| T4 | T1 | T6,T10 | T3,T5 |
| T5 | T1,T2 | T10,T11 | T3,T4 |
| T6 | T3,T4 | T10 | T7,T8,T9 |
| T7 | T3 | T10 | T6,T8,T9 |
| T8 | T1,T3 | T10 | T6,T7,T9 |
| T9 | T2 | T10,T12 | T6,T7,T8 |
| T10 | T5,T6,T7,T8,T9,T11 | T12,T16,T17,T18 | - |
| T11 | T2,T5 | T10,T12 | T13 |
| T12 | T9,T10 | T14,T16 | T13 |
| T13 | T12 | - | T14 |
| T14 | T12 | T15,T16,T17,T18 | T13 |
| T15 | T14 | T17,T18 | T16 |
| T16 | T12,T14 | T17 | T15 |
| T17 | T10,T14,T15,T16 | T18 | - |
| T18 | T17 | - | - |

## Todos
> Implementation + Test = ONE todo. Never separate.

- [ ] 1. Scaffold the uv project (src layout, deps, gitignore, example config, README stub)
  What to do / Must NOT do: Create the project root `VocabularyCollector/` with `pyproject.toml` (name `vocab-collector`, requires-python `>=3.11`, deps `pynput>=1.8,<2`, `pyperclip>=1.8,<2`, `openai>=1.40`, `pydantic>=2.6,<3`; dev deps `pytest`, `pytest-mock`, `pyinstaller`), `src/vocab_collector/__init__.py`, `tests/`, `packaging/`, `scripts/`, `config/config.example.toml`, `.gitignore`, `README.md` stub. `.gitignore` MUST contain `config/config.toml`, `data/`, `dist/`, `build/`, `*.spec`? (keep `packaging/*.spec` tracked), `__pycache__/`, `.venv/`. `config.example.toml` MUST have all keys from Scope with the verified values and `api_key = "sk-REPLACE_ME"`. Do NOT create `config/config.toml` (gitignored, user-owned). Do NOT add any dependency not listed.
  Parallelization: Wave 1 | Blocked by: none | Blocks: T2..T18
  References: Scope "Must have"; Findings F1/F10/F11; uv `pyproject.toml` docs.
  Acceptance criteria (agent-executable): `uv sync` exits 0; `uv run python -c "import vocab_collector; import pynput, pyperclip, openai, pydantic"` exits 0.
  QA scenarios: happy = `uv sync` then import check passes; failure = `git check-ignore -v config/config.toml data/vocabulary.db` shows both ignored while `config/config.example.toml` is NOT ignored. Evidence `.omo/evidence/task-1-vocab-collector.txt`.
  Commit: Y | chore(scaffold): init uv project, deps, gitignore, example config

- [ ] 2. `paths.py`: portable path resolution (frozen vs source)
  What to do / Must NOT do: Implement `app_dir()` returning `os.path.dirname(sys.executable)` when `getattr(sys,"frozen",False)` else the project root; and `config_path()`, `data_dir()`, `db_path()`, `log_path()`, `html_path()` under it; `ensure_dirs()` creating `config/` and `data/`. MUST never use `sys._MEIPASS`. Do NOT store or log absolute paths anywhere.
  Parallelization: Wave 1 | Blocked by: T1 | Blocks: T3,T5,T9,T11
  References: Findings F8; https://pyinstaller.org/en/stable/runtime-information.html
  Acceptance criteria (agent-executable): pytest test monkeypatches `sys.frozen=True`, `sys.executable=r"C:\x\VocabularyCollector.exe"`, asserts `db_path()`==`r"C:\x\data\vocabulary.db"` and `log_path()` endswith `data\collector.log`; non-frozen test asserts config under the repo.
  QA scenarios: happy = frozen-simulation returns exe-sibling paths; failure = `sys._MEIPASS` is NOT consulted in either mode (assert by making it raise). Evidence `.omo/evidence/task-2-vocab-collector.txt`.
  Commit: Y | feat(paths): portable exe-relative path resolution

- [ ] 3. `config.py`: load + validate `config.toml`
  What to do / Must NOT do: `load_config(path)` using `tomllib`; dataclasses/pydantic `LlmConfig` and `AppConfig`; defaults for every `[app]` key (max_selection_chars=64, double_tap_window_ms=400, clipboard_wait_ms=400, log_level="INFO"); `timeout_seconds=30`, `max_retries=2` defaults. Validate non-empty base_url/api_key/model; reject a placeholder api_key (`sk-REPLACE_ME`) with a clear message. Missing file → raise `ConfigError` with actionable text. Provide `redacted_summary()` that never includes the key. Do NOT read the key from anywhere else (no env override).
  Parallelization: Wave 1 | Blocked by: T1,T2 | Blocks: T6,T7,T10
  References: Scope Config; Findings F1.
  Acceptance criteria (agent-executable): pytest: valid file loads; missing file raises ConfigError naming the path; missing `[llm].api_key` raises; defaults applied when `[app]` absent; `redacted_summary()` does not contain the literal key.
  QA scenarios: happy = example config loads with defaults; failure = file with `api_key="sk-REPLACE_ME"` raises ConfigError; evidence `.omo/evidence/task-3-vocab-collector.txt`.
  Commit: Y | feat(config): tomllib loader with validation and redaction

- [ ] 4. `models.py`: Pydantic v2 `VocabResult`
  What to do / Must NOT do: `class VocabResult(BaseModel)` with `english`, `chinese`, `domain: str` (domain is free-text 学科, NOT an enum); a field validator strips and rejects empty; no extra fields allowed (`model_config = ConfigDict(extra="forbid")`). Do NOT add fields the schema does not have.
  Parallelization: Wave 1 | Blocked by: T1 | Blocks: T6,T10
  References: Scope LLM; Findings F11; pydantic v2 `model_validate`.
  Acceptance criteria (agent-executable): pytest: valid dict validates; whitespace-only field raises ValidationError; extra key raises; JSON round-trip `model_validate_json`.
  QA scenarios: happy = `{"english":"robustness","chinese":"稳健性","domain":"AI"}` validates; failure = empty `chinese` and unknown extra key both rejected; evidence `.omo/evidence/task-4-vocab-collector.txt`.
  Commit: Y | feat(models): Pydantic VocabResult schema

- [ ] 5. `db.py`: SQLite schema, dedup insert, list
  What to do / Must NOT do: `connect(path)` with `busy_timeout=5000`; `init_schema(conn)` idempotent. Table exactly:
  `vocabulary(id INTEGER PRIMARY KEY AUTOINCREMENT, english TEXT NOT NULL COLLATE NOCASE UNIQUE, chinese TEXT NOT NULL, domain TEXT NOT NULL, created_at TEXT NOT NULL, fsrs_state INTEGER, fsrs_step INTEGER, fsrs_stability REAL, fsrs_difficulty REAL, fsrs_due TEXT, fsrs_last_review TEXT)`.
  `insert_word(conn, english, chinese, domain, created_at)` using `INSERT ... ON CONFLICT(english) DO NOTHING`, returning `True` if a row was inserted else `False` (via `cursor.rowcount`). `list_all(conn)` ordered `created_at DESC, id DESC`. `created_at` is passed in (app supplies `datetime.now(timezone.utc).isoformat(timespec="seconds")`). MUST NOT implement any FSRS read/write. MUST NOT add last_seen/count.
  Parallelization: Wave 1 | Blocked by: T1,T2 | Blocks: T10,T11
  References: Findings F7; py-fsrs Card fields `{state, step, stability, difficulty, due, last_review}` (https://open-spaced-repetition.github.io/py-fsrs/fsrs.html) - this is why reps/lapses are omitted.
  Acceptance criteria (agent-executable): pytest on a tmp DB: insert returns True then inserting `"Robustness"` after `"robustness"` returns False and count stays 1; `list_all` returns newest first; schema `PRAGMA table_info` has exactly the 11 columns listed.
  QA scenarios: happy = NOCASE duplicate ignored, first row kept; failure = reopen existing DB and re-run `init_schema` (no error, no data loss); evidence `.omo/evidence/task-5-vocab-collector.txt`.
  Commit: Y | feat(db): minimal schema with NOCASE dedup and FSRS-reserved columns

- [ ] 6. `llm.py`: OpenAI-compatible structured call + fallback + validation
  What to do / Must NOT do: `LLMClient(config)` building `OpenAI(base_url=..., api_key=..., timeout=..., max_retries=...)`. `collect(word) -> Vocabulary(english=word, chinese=..., domain=...)`:
  1. system+user prompt (system: bilingual dictionary; user: `Word: <word>`; ask for Chinese meaning and academic discipline as 学科 e.g. AI / Embodied / Maths).
  2. attempt `response_format={"type":"json_schema","json_schema":{"name":"vocab","strict":True,"schema":{"type":"object","properties":{"english":{"type":"string"},"chinese":{"type":"string"},"domain":{"type":"string"}},"required":["english","chinese","domain"],"additionalProperties":False}}}`.
  3. if the API raises a `response_format`-type error (catch `openai.BadRequestError` whose message mentions `response_format`), retry once with `{"type":"json_object"}` and the schema embedded in the user prompt.
  4. read `choices[0].message.content`; if `finish_reason=="length"` raise `LLMError("truncated")`; strip markdown fences; `json.loads`; `VocabResult.model_validate`.
  5. **The stored `english` is always the sanitized captured `word`** (authoritative); the model's `english` is only cross-checked.
  On any failure raise `LLMError(reason)`. MUST log (caller does) but MUST NOT write the DB here. This todo does NOT make a live network call in unit tests; the E2E (T17) uses the stub.
  Parallelization: Wave 2 | Blocked by: T3,T4 | Blocks: T10
  References: Findings F5/F6/F10; verified: POST `https://models.sjtu.edu.cn/api/v1/chat/completions` with `json_schema strict` returns HTTP 200 on backend `vllm-0.26.0`; `json_object` also returns 200; openai-python `response_format` support.
  Acceptance criteria (agent-executable): pytest with a mocked client: strict-schema happy path parses; fenced ```json content parses; junk content raises LLMError; `finish_reason="length"` raises; rejection error triggers exactly one fallback attempt; empty field raises.
  QA scenarios: happy = mocked strict response → result english==input word; failure = mocked 400 → fallback path, then junk → LLMError; evidence `.omo/evidence/task-6-vocab-collector.txt`.
  Commit: Y | feat(llm): SJTU-compatible structured output with json_object fallback

- [ ] 7. `clipboard.py`: sequence-gated read, retry, sanitize
  What to do / Must NOT do: `get_sequence_number()` via `ctypes.windll.user32.GetClipboardSequenceNumber`; `wait_for_change(prev_seq, timeout_ms, poll_ms=20) -> bool`; `read_text(retries=5, delay_ms=50) -> str` wrapping `pyperclip.paste()` with retry on `PyperclipException`/clipboard-busy; `sanitize(text, max_chars) -> str | None`: strip, collapse whitespace, return None if empty / contains `\n` / len>max_chars / has no `[A-Za-z]`. MUST NOT write the clipboard. MUST NOT synthesize keystrokes. On `wait_for_change` timeout the caller MUST abort (return None up the chain).
  Parallelization: Wave 2 | Blocked by: T3 | Blocks: T10
  References: Findings F3/F4; https://docs.rs/copycopy/latest/copycopy/ (change-counter polling); pyperclip.
  Acceptance criteria (agent-executable): pytest excludes Windows-only ctypes by mocking it: `sanitize` table (leading/trailing space, internal double space, `"a\nb"`, 65-char string, `"1234"` no letter); `wait_for_change` returns False on timeout (monkeypatched clock); `read_text` retries then raises after N.
  QA scenarios: happy = `"  heterogeneous "` → `"heterogeneous"`; failure = clipboard busy for all retries → raises, and timeout → caller aborts without reading; evidence `.omo/evidence/task-7-vocab-collector.txt`.
  Commit: Y | feat(clipboard): freshness-gated, retrying, sanitized read

- [ ] 8. `hotkey.py`: pure double-tap state machine + pynput listener
  What to do / Must NOT do: `TapStateMachine(window_ms)` pure and fully testable: `feed(vk, is_press, now_monotonic) -> Event` where Event ∈ {NONE, FIRST_TAP, TRIGGER}. Rules: track Ctrl via `VK_LCONTROL=0xA2`/`VK_RCONTROL=0xA3` and C via `VK_C=0x43`; a tap = press then release (a press while C is still down, i.e. auto-repeat, is ignored); window measured first-C-press→second-C-press; reset on any other key press, on Ctrl release, or on timeout; after TRIGGER enter a cooldown that suppresses further triggers until Ctrl is released or the window elapses (so a triple tap = exactly ONE trigger). `Listener` wraps `pynput.keyboard.Listener(on_press=..., on_release=...)`: on FIRST_TAP record `clipboard.get_sequence_number()`; on TRIGGER call `on_trigger(seq0)` which must be non-blocking (enqueue). The callback MUST only feed the machine + enqueue. `start()/stop()`; log when the listener stops. MUST match virtual keys, not characters (Dvorak/IME safe). MUST require key-up between taps.
  Parallelization: Wave 2 | Blocked by: T1,T3 | Blocks: T10
  References: Findings F2/F3; pynput docs (https://pynput.readthedocs.io/en/latest/keyboard.html); Metis MUST-FIX on auto-repeat + VK matching.
  Acceptance criteria (agent-executable): pytest synthetic event streams: two taps with release between → one TRIGGER; single tap → none; triple tap → one; C held (down,down,down) → none; other key between taps → reset; Ctrl released between taps → reset; exactly at 399/401 ms → trigger/not-trigger.
  QA scenarios: happy = scripted taps yield exactly one trigger; failure = auto-repeat down-only stream yields zero triggers; evidence `.omo/evidence/task-8-vocab-collector.txt`.
  Commit: Y | feat(hotkey): VK-based Ctrl+C+C tap state machine + listener

- [ ] 9. `logging_setup.py`: file logging that never crashes a windowed exe
  What to do / Must NOT do: `setup_logging(log_path, level)`: `RotatingFileHandler(maxBytes=1_000_000, backupCount=3, encoding="utf-8")`; add a `StreamHandler` ONLY if `sys.stderr is not None` (guard the PyInstaller `--noconsole` case where streams are None). `install_excepthooks(logger)` sets `sys.excepthook` and `threading.excepthook` to log exceptions instead of dying. Logger helper that redacts `api_key`. Do NOT log the key; do NOT assume stdout exists.
  Parallelization: Wave 2 | Blocked by: T2 | Blocks: T10,T12
  References: Metis MUST-FIX (stdout=None under --noconsole).
  Acceptance criteria (agent-executable): pytest with `sys.stderr=None` → setup does not raise and a record still reaches the file; log file is created under a tmp dir; excepthook writes a traceback.
  QA scenarios: happy = record written to file; failure = `sys.stderr` monkeypatched to None → no exception; evidence `.omo/evidence/task-9-vocab-collector.txt`.
  Commit: Y | feat(logging): rotating file log safe under --noconsole

- [ ] 10. `pipeline.py`: worker queue, orchestration, error isolation, HTML refresh
  What to do / Must NOT do: `Collector(config, db_conn, llm, paths)` with a `queue.Queue` and ONE worker thread. `enqueue(seq0)` is the listener callback (non-blocking). Worker per item, each stage inside try/except so the thread NEVER dies: `wait_for_change(seq0)` (False → log `rejected timeout`), `read_text`, `sanitize` (None → log `rejected <reason>`), `llm.collect` (LLMError → log `error <word> <reason>`, no write), `db.insert_word` (False → log `duplicate <word>`; True → log `inserted <word>` then `html_export.write_atomic(html_path, db.list_all(conn))`). Log at INFO for inserted/duplicate, WARNING for rejected, ERROR for llm failures (include the captured word so nothing is unrecoverable). SQLite connection created/used only in the worker thread. Do NOT add retries, queues-on-disk, or stats.
  Parallelization: Wave 2 | Blocked by: T5,T6,T7,T8,T9,T11 | Blocks: T12,T16,T17,T18
  References: Scope Storage/HTML/Runtime; Findings F7; Metis (at-most-once, error-log-with-word, worker resilience).
  Acceptance criteria (agent-executable): pytest with fakes: a successful path inserts + regenerates HTML + logs `inserted`; an LLMError path leaves the DB unchanged and logs the word; a duplicate path logs `duplicate` and does not rewrite HTML; an exception raised by any fake does not kill the worker (subsequent item still processed).
  QA scenarios: happy = fakes → 1 row + HTML contains the word; failure = fake LLM raises then a second item succeeds, proving the worker survived; evidence `.omo/evidence/task-10-vocab-collector.txt`.
  Commit: Y | feat(pipeline): queue worker with isolated stages and HTML refresh

- [ ] 11. `html_export.py`: atomic, escaped, self-contained HTML
  What to do / Must NOT do: `render(rows) -> str` returns a full document with `<!doctype html>`, `<meta charset="utf-8">`, a title, and one `<table>` with headers english / chinese / domain / created_at; every cell `html.escape(str(v))`; rows already newest-first. `write_atomic(path, html)` writes `path + ".tmp"` then `os.replace(tmp, path)`. No JS, no CSS framework, no filter box, no search. MUST escape (a word may contain `<`/`&`). MUST be UTF-8 so Chinese renders.
  Parallelization: Wave 3 | Blocked by: T2,T5 | Blocks: T10,T12
  References: Scope HTML; Metis (escaping, charset, atomic write).
  Acceptance criteria (agent-executable): pytest: a row with `english="<b>&x"`, Chinese text, and emoji → output contains the escaped forms and NOT the raw `<b>`; output contains `charset="utf-8"`; `write_atomic` leaves no `.tmp` file and replaces content atomically (assert via a second write).
  QA scenarios: happy = golden-string assertions pass; failure = malicious `english` value is escaped; evidence `.omo/evidence/task-11-vocab-collector.txt`.
  Commit: Y | feat(html): escaped self-contained vocabulary page with atomic write

- [ ] 12. `__main__.py`: entry point (daemon only)
  What to do / Must NOT do: `main()`: `ensure_dirs()` → `setup_logging(log_path, level)` → `install_excepthooks` → `load_config(config_path)` (on `ConfigError`: log fatal with actionable text and `sys.exit(1)`; never a popup) → `db.connect` + `init_schema` → regenerate HTML once from `list_all` → build `Collector` + start it → start `hotkey.Listener(on_trigger=collector.enqueue)` → log "listening" → `join()` / block. No subcommands, no CLI args beyond none, no console output requirement. MUST never crash the process on a per-item error.
  Parallelization: Wave 3 | Blocked by: T9,T10 | Blocks: T14,T16
  References: Scope Runtime; Metis first-run MUST-FIX.
  Acceptance criteria (agent-executable): pytest: missing config → `SystemExit(1)` and a fatal log line; happy path with fakes → listener started once and HTML regenerated.
  QA scenarios: happy = fakes → process reaches "listening" then stops cleanly; failure = missing `config.toml` → exit code 1 and `data/collector.log` contains the path; evidence `.omo/evidence/task-12-vocab-collector.txt`.
  Commit: Y | feat(app): daemon entry point with fail-fast config logging

- [ ] 13. `README.md`: usage, install location, limitations, first-run
  What to do / Must NOT do: Document: what it does; first-run steps (copy `config.example.toml` → `config/config.toml`, paste key); where to open the vocabulary page (`data/vocabulary.html`); where the log is; how to quit (Task Manager / console Ctrl+C); and the known limitations (elevated apps invisible due to UIPI; terminals where Ctrl+C isn't copy; protected scanned PDFs; garbage-in captures like a whole code line; no retry; restart if captures stop after sleep; install in a user-writable, non-OneDrive folder). MUST NOT document features that don't exist.
  Parallelization: Wave 3 | Blocked by: T12 | Blocks: -
  References: Metis limitations list; Findings F9.
  Acceptance criteria (agent-executable): file exists and contains the exact section headings `First run`, `Where is my vocabulary?`, `Where is the log?`, `Known limitations` (grep).
  QA scenarios: happy = grep finds all four headings; failure = no mention of an unimplemented feature (grep for `Anki|FSRS|tray|popup` only appears in "not included"); evidence `.omo/evidence/task-13-vocab-collector.txt`.
  Commit: Y | docs(readme): usage, first run, and known limitations

- [ ] 14. `packaging/vocab-collector.spec` + `scripts/build.ps1`
  What to do / Must NOT do: PyInstaller spec: `onedir`, `console=False` (noconsole), `upx=False`, `name="VocabularyCollector"`, `hiddenimports=["pynput.keyboard._win32","pynput.mouse._win32","pynput._util.win32"]`, no icon. Build script (PowerShell, run on Windows): `uv sync`; `uv run pyinstaller packaging/vocab-collector.spec`; create `dist/config/` and `dist/data/`; copy `config/config.example.toml` → `dist/config/config.example.toml`. MUST NOT copy or embed the real `config/config.toml`. Do NOT enable UPX. Do NOT use `--contents-directory .` (keep the default `_internal/` so config/ and data/ stay visible).
  Parallelization: Wave 4 | Blocked by: T12 | Blocks: T15,T16,T17,T18
  References: Findings F8; Metis (no UPX, use default _internal, config beside exe).
  Acceptance criteria (agent-executable): on Windows `scripts/build.ps1` exits 0; `dist/VocabularyCollector/VocabularyCollector.exe` exists; `dist/VocabularyCollector/config/config.example.toml` exists; no `config/config.toml` anywhere under `dist/`.
  QA scenarios: happy = build + expected files; failure = exe folder contains no real key (checked in T15); evidence `.omo/evidence/task-14-vocab-collector.txt`.
  Commit: Y | build(packaging): PyInstaller onedir spec and Windows build script

- [ ] 15. Build hygiene: prove no secret and no real config in `dist/`
  What to do / Must NOT do: A check (script or pytest marked windows_e2e) that greps the entire `dist/` tree for the real api key value and for a file named `config/config.toml`; both must be absent. Also assert `.gitignore` covers `config/config.toml` and `data/` using `git check-ignore`.
  Parallelization: Wave 4 | Blocked by: T14 | Blocks: T17,T18
  References: Scope Config/Packaging; Metis MUST-FIX build hygiene.
  Acceptance criteria (agent-executable): grep for the key pattern returns nothing; `git check-ignore -q config/config.toml` and `git check-ignore -q data/` both exit 0.
  QA scenarios: happy = clean dist; failure = intentionally copying the real config then re-running the check FAILS (proves the check works), then remove it; evidence `.omo/evidence/task-15-vocab-collector.txt`.
  Commit: Y | test(build): assert no secret or real config in dist

- [ ] 16. Windows smoke: listener + pipeline start and stop cleanly (no network)
  What to do / Must NOT do: A Windows-only pytest (marker `windows_e2e`) that starts the real `pynput` listener with a fake `on_trigger`, asserts it captures a synthetic `Ctrl+C+C` (sent via `pynput.keyboard.Controller`) into the callback, then stops the listener and asserts it terminated. Do NOT require the real LLM or network. Do NOT run on Linux (skip when `sys.platform != "win32"`).
  Parallelization: Wave 4 | Blocked by: T12,T14 | Blocks: T17
  References: Findings F2/F3; pynput Controller.
  Acceptance criteria (agent-executable): on Windows `uv run pytest -m windows_e2e tests/test_listener_smoke.py` passes; on Linux it is skipped.
  QA scenarios: happy = synthetic double-tap fires exactly one callback; failure = a single synthetic Ctrl+C fires zero callbacks; evidence `.omo/evidence/task-16-vocab-collector.txt`.
  Commit: Y | test(hotkey): Windows listener smoke test

- [ ] 17. Windows hermetic E2E: stub LLM + Notepad + real capture → DB + HTML
  What to do / Must NOT do: A Windows-only E2E script/test that: (1) starts a local `http.server` stub on `127.0.0.1:<port>` replying to `POST /v1/chat/completions` with canned content `{"english":"heterogeneous","chinese":"异质的","domain":"AI"}`; (2) writes `config/config.toml` pointing `base_url` at the stub; (3) runs the app (source or built exe) in a subprocess; (4) launches `notepad.exe`, types `heterogeneous`, selects all, sends `Ctrl+C+C` via the Controller; (5) polls the DB until 1 row appears (timeout) and asserts `english=="heterogeneous"`, `chinese=="异质的"`, and that `data/vocabulary.html` contains the word; (6) sends the gesture again and asserts the row count stays 1 (dedup). Do NOT use the real key/network.
  Parallelization: Wave 4 | Blocked by: T10,T14,T15,T16 | Blocks: T18
  References: Scope Storage/HTML; Findings F7; Metis hermetic-E2E directive.
  Acceptance criteria (agent-executable): `uv run pytest -m windows_e2e tests/test_e2e_capture.py` passes on Windows; evidence includes the DB dump and the HTML.
  QA scenarios: happy = one row + HTML contains the word; failure = second identical capture leaves count==1; evidence `.omo/evidence/task-17-vocab-collector.txt`.
  Commit: Y | test(e2e): hermetic Windows capture-to-DB-to-HTML flow

- [ ] 18. Windows failure-path E2E: API error, timeout, missing config, resilience
  What to do / Must NOT do: Windows-only E2E: (a) stub returns HTTP 500 → capture a word → assert DB unchanged and `data/collector.log` contains an ERROR with the word, and the app process is still alive; (b) point config at a dead port → capture → same no-write + logged timeout + alive; (c) start with no `config/config.toml` → process exits 1 and the log names the path; (d) simulate a stale clipboard (no sequence change) → assert `rejected timeout` and no row. Do NOT require network or the real key.
  Parallelization: Wave 4 | Blocked by: T17 | Blocks: -
  References: Metis MUST-FIX (at-most-once logging, first-run, abort-on-stale, resilience).
  Acceptance criteria (agent-executable): `uv run pytest -m windows_e2e tests/test_e2e_failures.py` passes; the app subprocess is alive after (a) and (b).
  QA scenarios: happy = all four failure behaviours observed; failure = if the DB gains a row on any failure path the test FAILS; evidence `.omo/evidence/task-18-vocab-collector.txt` including the tail of the log.
  Commit: Y | test(e2e): failure paths never write partial rows

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [ ] F1. Plan compliance audit
- [ ] F2. Code quality review
- [ ] F3. Real manual QA
- [ ] F4. Scope fidelity

## Commit strategy
One atomic conventional commit per todo (messages in the `Commit:` lines), on a feature branch `feat/vocab-collector`. Never commit `config/config.toml`, `data/`, `dist/`, or any key. Before the first commit, confirm `git status` shows `config/config.example.toml` tracked and `config/config.toml` ignored. The commit for T15 must demonstrably fail if a real config leaks.

## Success criteria
1. `uv run pytest` is green for all non-Windows tests; `uv run pytest -m windows_e2e` is green on the Windows host (T16-T18).
2. On Windows, selecting an English word in a browser/PDF/VS Code/Obsidian and pressing `Ctrl+C+C` inserts exactly one row into `data/vocabulary.db` and updates `data/vocabulary.html`.
3. Re-capturing the same word (any casing) does not add a row.
4. With the real SJTU endpoint and a valid key, `domain` is the academic discipline (e.g. AI, Maths) and `chinese` is populated; with an invalid key/network failure, **no** row is written and the word + reason appear in `data/collector.log`.
5. The built `VocabularyCollector/` folder runs by double-click on a machine without Python; it creates `data/` and the log; it contains no API key.
6. No feature outside Scope "Must have" exists anywhere in the code.