# Vocab Collector

在任意程序里选中一个英文单词，按住 `Ctrl` 连按两次 `C`，它就会调用大模型取回**中文释义**和**学科**，写入本地数据库，并刷新一个可直接用浏览器打开的单词表。

它常驻后台：没有窗口、不弹提示、不托盘、不注册开机启动、不做云同步。整个文件夹是便携的——双击一个 `exe` 即可运行，不需要 Python、Node 或安装器。推荐通过 win+r 输入`shell:startup` 将 `exe` 放入，即可开机自启。

- 平台：Windows
- 语言：Python >= 3.11
- 运行依赖：`pynput`、`pyperclip`、`openai`、`pydantic`
- 当前版本：`0.1.0`（源码 `src/vocab_collector`）

---

## 一、功能与实现文件对照

| 功能                                                | 实现文件                                                                      | 对应测试                                                  | 状态       |
| ------------------------------------------------- | ------------------------------------------------------------------------- | ----------------------------------------------------- | -------- |
| 配置加载与校验（TOML、占位 key 拦截、密钥脱敏）                      | `src/vocab_collector/config.py`                                           | `tests/test_config.py`                                | 完成       |
| 可移植路径解析（源码与冻结 exe 都指向同级 `config/`、`data/`）        | `src/vocab_collector/paths.py`                                            | `tests/test_paths.py`                                 | 完成       |
| 轮转日志、`--noconsole` 安全、未捕获异常写入日志                   | `src/vocab_collector/logging_setup.py`                                    | `tests/test_logging_setup.py`                         | 完成       |
| LLM 结构化调用（`json_schema` 严格模式，被拒时回退 `json_object`） | `src/vocab_collector/llm.py`                                              | `tests/test_llm.py`                                   | 完成       |
| 模型响应校验（Pydantic v2，三字段非空、禁止多余字段）                  | `src/vocab_collector/models.py`                                           | `tests/test_models.py`                                | 完成       |
| 剪贴板新鲜度门控、重试读取、选区清洗                                | `src/vocab_collector/clipboard.py`                                        | `tests/test_clipboard.py`                             | 完成       |
| 全局手势 `Ctrl+C+C`（虚拟键状态机 + pynput 监听）               | `src/vocab_collector/hotkey.py`                                           | `tests/test_hotkey.py`、`tests/test_listener_smoke.py` | 完成       |
| 单工作线程队列编排、阶段隔离、成功后刷新 HTML                         | `src/vocab_collector/pipeline.py`                                         | `tests/test_pipeline.py`                              | 完成       |
| SQLite 存储（大小写不敏感去重、倒序查询、FSRS 预留列）                 | `src/vocab_collector/db.py`                                               | `tests/test_db.py`                                    | 完成       |
| 自包含 HTML 导出（HTML 转义 + 原子写入）                       | `src/vocab_collector/html_export.py`                                      | `tests/test_html_export.py`                           | 完成       |
| 守护进程入口（无参数、启动即监听）                                 | `src/vocab_collector/__main__.py`                                         | `tests/test_main.py`                                  | 完成       |
| Web 词库页面（Flask、搜索、分页、删除、编辑、亮/暗主题）             | `src/vocab_collector/web.py`、`src/vocab_collector/templates/index.html`   | 待补充                                                | 完成       |
| 打包（PyInstaller onedir、无控制台、无 UPX、附带示例配置）          | `packaging/vocab-collector.spec`、`scripts/build.ps1`、`scripts/run_app.py` | `tests/test_build_hygiene.py`                         | 完成       |
| 构建产物卫生检查（dist 内无真实 key、无真实 config）                | `tests/test_build_hygiene.py`                                             | 自身                                                    | 完成       |

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
6. 打开浏览器访问 `http://127.0.0.1:8765/` 查看词库（支持搜索、分页、删除）。

> 建议放在**用户可写、且不在 OneDrive 同步目录**的位置，否则 `data/` 可能写不进去。

### 方式 B：从源码运行（开发）

```powershell
uv sync
Copy-Item config/config.example.toml config/config.toml   # 然后填入你的 key
uv run python -m vocab_collector
```

## 四、配置说明（`config/config.toml`）

| 键                          | 默认值                                 | 含义                 |
| -------------------------- | ----------------------------------- | ------------------ |
| `llm.base_url`             | `https://models.sjtu.edu.cn/api/v1` | OpenAI 兼容接口地址      |
| `llm.api_key`              | `sk-REPLACE_ME`                     | 你的密钥（必须替换，否则启动即报错） |
| `llm.model`                | `deepseek-chat`                     | 模型名                |
| `llm.timeout_seconds`      | `30`                                | 单次请求超时             |
| `llm.max_retries`          | `0`                                 | SDK 级别重试次数（禁用以避免快速消耗配额） |
| `llm.rate_limit_retry_wait`| `60`                                | 收到 429 限流后等待多少秒再重试一次 |
| `app.max_selection_chars`  | `64`                                | 允许的最大选区长度          |
| `app.double_tap_window_ms` | `400`                               | 两次 C 之间允许的最大间隔     |
| `app.clipboard_wait_ms`    | `800`                               | 等待剪贴板更新的最长时间       |
| `app.log_level`            | `INFO`                              | 日志级别               |
| `web.host`                 | `127.0.0.1`                         | Web 服务监听地址          |
| `web.port`                 | `8765`                              | Web 服务端口             |

`config/config.toml` 被 `.gitignore` 忽略，且**绝不会**被打包进 `dist/`。

## 五、运行时生成的文件（都在 exe 同级目录）

| 路径                     | 说明                          |
| ---------------------- | --------------------------- |
| `data/vocabulary.db`   | SQLite 数据库，唯一表 `vocabulary` |
| `data/vocabulary.html` | 静态单词表页面（备用，Web 服务不可用时可用）   |
| `data/collector.log`   | 轮转日志（1 MB × 3，UTF-8）        |

## 五.一、Web 词库页面

程序启动后，会在 `http://127.0.0.1:8765/` 提供 Web 词库服务（端口可在配置文件中修改）。

功能：
- **搜索**：支持按英文、中文释义、领域模糊搜索
- **分页**：每页 20 条，支持翻页
- **统计**：显示全部词汇数、本周新增、涉及领域数
- **删除**：单条永久删除（有确认对话框）
- **编辑**：点击铅笔图标就地修改中文释义，Enter 保存 / Shift+Enter 换行
- **主题**：支持亮色/暗色主题切换（自动记住偏好）
- **释义隐藏**：可隐藏/显示单条或全部释义

## 六、测试

```powershell
uv run pytest
```

## 七、打包构建

```powershell
pwsh scripts/build.ps1
```

产物在 `dist/VocabularyCollector/`。构建脚本只会把 `config/config.example.toml` 复制进 `dist/config/`，不会打包真实密钥。

### 自动化构建（GitHub Actions）

项目配置了两个 GitHub Actions workflow：

**CI（持续集成）**
- 每次 push 到 `main` 或提交 PR 时自动运行测试
- 确保代码改动不会破坏现有功能

**Release（自动发布）**
- 推送 `v*` 格式的 tag 时自动触发（例如 `v0.1.1`）
- 在 GitHub 的 Windows 服务器上构建 exe
- 自动打包并上传到 GitHub Release
- 用户可以直接从 Release 页面下载最新版本

发布新版本的流程：
```powershell
# 1. 更新 pyproject.toml 中的 version
# 2. 提交并推送
git add pyproject.toml
git commit -m "bump version to 0.1.1"
git push

# 3. 打 tag 并推送
git tag v0.1.1
git push origin v0.1.1
```

推送 tag 后，GitHub Actions 会自动构建并创建 Release，无需手动操作。

## 八、开发进度记录

用此清单维护项目状态。开始工作前登记待办，实施中标记进行中，完成后补充验证结果。

### 已完成

- [x] 核心模块：配置、路径、日志、LLM、模型、剪贴板、手势、队列、SQLite 存储、HTML 导出和守护进程入口。
- [x] 默认测试集曾在本机通过：`77 passed`。
- [x] PyInstaller onedir 打包：可生成无控制台的 `dist/VocabularyCollector/`。
- [x] 手动验证：已确认 `Ctrl+C+C` 手势可用。
- [x] 修复热键虚拟键码识别：`pynput.Key` 的键码来自 `key.value.vk`，并将 `VK_CONTROL = 0x11` 纳入 Ctrl 判定。
- [x] 本机词库网页：以固定地址 `http://127.0.0.1:8765/` 提供服务（端口可配置），主程序启动时自动启动服务。
- [x] 本机词库网页：SQLite 数据源；支持搜索、分页、刷新和单条永久删除。
- [x] 本机词库网页：紧凑词卡布局；支持亮/暗主题、单卡片释义隐藏/显示、全部释义隐藏/显示。
- [x] 限流保护：禁用 SDK 自动重试，429 错误等待 60 秒后重试一次，避免快速消耗 API 配额。
- [x] 构建保护：重新构建时自动备份并恢复 `data/`（数据库）和 `config/config.toml`（API key），避免数据丢失。
- [x] 词卡编辑：卡片 footer 增加 ✏️ 按钮，点击后就地编辑中文释义，保存后即时更新。
- [x] 剪贴板等待超时默认值从 400ms 调整为 800ms，减少慢响应程序的 `rejected timeout`。
- [x] 词卡图标统一彩色：三个操作按钮（👁️ ✏️ 🗑️）均添加 U+FE0F 变体选择符，确保在所有系统上渲染为彩色 emoji。
- [x] 编辑快捷键：修改释义时按 Enter 直接保存（Shift+Enter 换行），无需点击保存按钮。
- [x] 删除端到端测试：移除不稳定的 `windows_e2e` 测试（`test_e2e_capture`、`test_e2e_failures`、`test_listener_smoke`）。
- [x] GitHub Actions CI：每次 push 或 PR 自动运行测试。
- [x] GitHub Actions Release：推送 `v*` tag 时自动构建 exe 并上传到 GitHub Release。

### 进行中

### 待办

- [ ] FSRS 复习逻辑：数据库已有 `fsrs_*` 预留列，但尚无算法。

## 九、已知限制

- 以管理员权限运行的程序（UIPI）看不到你的手势。
- 终端里 `Ctrl+C` 不是复制，因此终端中通常无法触发。
- 受保护的扫描版 PDF 选不中文字，自然也无法复制。
- 限流保护：收到 429 后会等待 60 秒再重试一次，若仍失败则仅记日志，不会自动补录。
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
│  ├─ web.py                   # Flask Web 服务
│  ├─ templates/
│  │  └─ index.html            # 词库网页模板
│  └─ __init__.py
├─ tests/                      # pytest 测试
├─ pyproject.toml
├─ uv.lock
└─ README.md
```
