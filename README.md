# Vocab Collector

在任意程序里选中一个英文单词，按住 `Ctrl` 连按两次 `C`，它就会调用大模型取回**中文释义**和**学科**，写入本地数据库，并刷新一个可直接用浏览器打开的单词表。

它常驻后台：没有窗口、不弹提示、不托盘、不注册开机启动、不做云同步。整个文件夹是便携的——双击一个 `exe` 即可运行，不需要 Python、Node 或安装器。

- 平台：Windows
- 语言：Python >= 3.11
- 运行依赖：`pynput`、`pyperclip`、`openai`、`pydantic`
- 当前版本：`0.1.0`（源码 `src/vocab_collector`）

---

## 一、功能与实现文件对照

| 功能 | 实现文件 | 对应测试 | 状态 |
| --- | --- | --- | --- |
| 配置加载与校验（TOML、占位 key 拦截、密钥脱敏） | `src/vocab_collector/config.py` | `tests/test_config.py` | 完成 |
| 可移植路径解析（源码与冻结 exe 都指向同级 `config/`、`data/`） | `src/vocab_collector/paths.py` | `tests/test_paths.py` | 完成 |
| 轮转日志、`--noconsole` 安全、未捕获异常写入日志 | `src/vocab_collector/logging_setup.py` | `tests/test_logging_setup.py` | 完成 |
| LLM 结构化调用（`json_schema` 严格模式，被拒时回退 `json_object`） | `src/vocab_collector/llm.py` | `tests/test_llm.py` | 完成 |
| 模型响应校验（Pydantic v2，三字段非空、禁止多余字段） | `src/vocab_collector/models.py` | `tests/test_models.py` | 完成 |
| 剪贴板新鲜度门控、重试读取、选区清洗 | `src/vocab_collector/clipboard.py` | `tests/test_clipboard.py` | 完成 |
| 全局手势 `Ctrl+C+C`（虚拟键状态机 + pynput 监听） | `src/vocab_collector/hotkey.py` | `tests/test_hotkey.py`、`tests/test_listener_smoke.py` | 完成 |
| 单工作线程队列编排、阶段隔离、成功后刷新 HTML | `src/vocab_collector/pipeline.py` | `tests/test_pipeline.py` | 完成 |
| SQLite 存储（大小写不敏感去重、倒序查询、FSRS 预留列） | `src/vocab_collector/db.py` | `tests/test_db.py` | 完成 |
| 自包含 HTML 导出（HTML 转义 + 原子写入） | `src/vocab_collector/html_export.py` | `tests/test_html_export.py` | 完成 |
| 守护进程入口（无参数、启动即监听） | `src/vocab_collector/__main__.py` | `tests/test_main.py` | 完成 |
| 打包（PyInstaller onedir、无控制台、无 UPX、附带示例配置） | `packaging/vocab-collector.spec`、`scripts/build.ps1`、`scripts/run_app.py` | `tests/test_build_hygiene.py` | 完成 |
| 构建产物卫生检查（dist 内无真实 key、无真实 config） | `tests/test_build_hygiene.py` | 自身 | 完成 |
| 端到端：真实捕获 -> 建库 -> 刷新页面 | `tests/test_e2e_capture.py`、`tests/e2e_support.py` | 自身（`windows_e2e`） | 不稳定，见第八节 |
| 端到端：失败路径（接口错误、超时、缺配置、陈旧剪贴板） | `tests/test_e2e_failures.py`、`tests/e2e_support.py` | 自身（`windows_e2e`） | 不稳定，见第八节 |

## 二、工作原理（一次捕获的完整链路）

1. `hotkey.Listener` 用 pynput 被动监听键盘，`TapStateMachine` 按**虚拟键码**判断「Ctrl 按住 + C 连按两次」。它只把工作塞进队列，绝不在回调里做慢操作。
2. 第一次按下 C 时记录 `GetClipboardSequenceNumber()`；触发时交给 `pipeline.Collector`。
3. `clipboard.wait_for_change()` 等待剪贴板序号变化（有超时）。序号不变就中止，绝不读取可能过期的剪贴板。
4. `clipboard.read_text()`（对忙锁重试）读出你自己 `Ctrl+C` 已经复制的内容；`clipboard.sanitize()` 去掉首尾/多余空白，拒绝空、多行、超长、无 ASCII 字母的输入。
5. `llm.LLMClient.collect()` 调 OpenAI 兼容接口，主用 `json_schema` 严格模式，被拒则回退 `json_object`；结果用 `models.VocabResult` 校验。**任何时候失败都只写日志，绝不写库。**
6. `db.insert_word()` 以大小写不敏感方式去重（`COLLATE NOCASE` + `UNIQUE`），重复词不新增。
7. 新词入库后，`html_export.write_atomic()` 重新生成 `data/vocabulary.html`（原子替换）。

## 三、快速开始

### 方式 A：使用打包好的程序（推荐给最终用户）

1. 准备 `VocabularyCollector/` 文件夹（含 `VocabularyCollector.exe`）。
2. 把 `config/config.example.toml` 复制为 `config/config.toml`。
3. 打开 `config/config.toml`，把 `api_key` 换成你自己的真实 key。
4. 双击 `VocabularyCollector.exe`。首次启动会自动创建 `data/` 和日志文件。
5. 在浏览器 / PDF / VS Code / Obsidian 里选中一个英文单词，按住 Ctrl 连按两次 C。
6. 用浏览器打开 `data/vocabulary.html` 查看结果。

> 建议放在**用户可写、且不在 OneDrive 同步目录**的位置，否则 `data/` 可能写不进去。

### 方式 B：从源码运行（开发）

```powershell
uv sync
Copy-Item config/config.example.toml config/config.toml   # 然后填入你的 key
uv run python -m vocab_collector
```

## 四、配置说明（`config/config.toml`）

| 键 | 默认值 | 含义 |
| --- | --- | --- |
| `llm.base_url` | `https://models.sjtu.edu.cn/api/v1` | OpenAI 兼容接口地址 |
| `llm.api_key` | `sk-REPLACE_ME` | 你的密钥（必须替换，否则启动即报错） |
| `llm.model` | `deepseek-chat` | 模型名 |
| `llm.timeout_seconds` | `30` | 单次请求超时 |
| `llm.max_retries` | `2` | 请求重试次数 |
| `app.max_selection_chars` | `64` | 允许的最大选区长度 |
| `app.double_tap_window_ms` | `400` | 两次 C 之间允许的最大间隔 |
| `app.clipboard_wait_ms` | `400` | 等待剪贴板更新的最长时间 |
| `app.log_level` | `INFO` | 日志级别 |

`config/config.toml` 被 `.gitignore` 忽略，且**绝不会**被打包进 `dist/`。

## 五、运行时生成的文件（都在 exe 同级目录）

| 路径 | 说明 |
| --- | --- |
| `data/vocabulary.db` | SQLite 数据库，唯一表 `vocabulary` |
| `data/vocabulary.html` | 单词表页面，每次成功记录后自动刷新 |
| `data/collector.log` | 轮转日志（1 MB × 3，UTF-8） |

## 六、测试

```powershell
uv run pytest                 # 单元 + 集成测试（默认排除 windows_e2e）
uv run pytest -m windows_e2e  # 需要真实桌面会话的端到端测试
```

## 七、打包构建

```powershell
pwsh scripts/build.ps1
```

产物在 `dist/VocabularyCollector/`。构建脚本只会把 `config/config.example.toml` 复制进 `dist/config/`，不会打包真实密钥。

## 八、开发进度记录

### 已完成

- 全部核心模块（配置、路径、日志、LLM、模型、剪贴板、手势、队列、存储、HTML、入口）均已实现并有对应测试。
- 非 `windows_e2e` 测试在本机为 `77 passed`。
- 已用 PyInstaller 构建出可双击运行的无控制台程序（`dist/VocabularyCollector/`）。
- 已录入真实 key、手动验证 `Ctrl+C+C` 手势可用，功能正常。

### 修复记录

- **手势完全失效的根因**（`src/vocab_collector/hotkey.py`）：pynput 对特殊键传入的是 `Key` 枚举，`key.vk` 恒为 `None`，真实值在 `key.value.vk`；并且合成 `Key.ctrl` 使用的是 `VK_CONTROL = 0x11`。原实现用 `getattr(key, "vk", None)` 取不到键码，导致所有按键被直接丢弃、手势无法触发。修复方式是新增 `_vk_of(key)` 统一提取虚拟键码，并把 `VK_CONTROL` 纳入 Ctrl 判定。

### 待完成 / 后续可改进

- **稳定 `windows_e2e`**：`test_e2e_capture` / `test_e2e_failures` 依赖 `notepad.exe` 获取前台焦点，已存在记事本实例时容易抢不到焦点而超时，导致偶发失败。可改用 `SetForegroundWindow` + `AttachThreadInput` 强制焦点，或每次用例启动独立记事本并等待窗口就绪。
- **失败重试 / 补录队列**：目前接口失败只记日志，不自动补录（有意保持简单）。
- **发布相关**：仓库尚无 `LICENSE`，可按需添加；可加入 GitHub Actions 做 CI 与 Release。
- **FSRS 复习逻辑**：数据库已预留 6 个 `fsrs_*` 列，但没有任何复习算法。
- **更丰富的单词表页面**：当前刻意保持极简（无搜索/过滤/分页）。

## 九、已知限制

- 以管理员权限运行的程序（UIPI）看不到你的手势。
- 终端里 `Ctrl+C` 不是复制，因此终端中通常无法触发。
- 受保护的扫描版 PDF 选不中文字，自然也无法复制。
- 没有重试队列：接口失败只写日志，不会自动补录。
- 选中一整行代码这类「垃圾输入」也会被当成单词送出去，最多记录一次失败。
- 电脑休眠唤醒后若手势失灵，重启程序即可。
- 若在 `dist/` 里手动放了真实 `config.toml`，`tests/test_build_hygiene.py` 的 dist 检查会失败——这是预期行为，该检查针对的是「刚构建出来、尚未填入密钥」的发布产物。

## 十、明确不做的事

没有 GUI、托盘、弹窗、通知、发音、例句、复习算法（Anki/FSRS）、统计、云同步或服务器。数据库里为 FSRS 预留了空列，但没有任何复习逻辑。

## 十一、目录结构

```
VocabularyCollector/
├─ config/
│  └─ config.example.toml      # 示例配置（提交进仓库）
├─ packaging/
│  └─ vocab-collector.spec     # PyInstaller 规格
├─ scripts/
│  ├─ build.ps1                # 构建脚本
│  └─ run_app.py               # PyInstaller 入口
├─ src/vocab_collector/        # 应用源码
│  ├─ __main__.py              # 守护进程入口
│  ├─ paths.py  config.py  logging_setup.py
│  ├─ clipboard.py  hotkey.py  pipeline.py
│  ├─ llm.py  models.py  db.py  html_export.py
│  └─ __init__.py
├─ tests/                      # pytest 测试（含 windows_e2e）
├─ pyproject.toml
├─ uv.lock
└─ README.md
```
