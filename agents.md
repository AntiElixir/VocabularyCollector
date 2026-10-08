# 项目背景

VocabularyCollector 是一个 Windows 便携式后台工具。用户在任意程序中选中英文单词，按住 `Ctrl` 连按两次 `C` 后，程序读取刚复制到剪贴板的文本，调用 OpenAI 兼容接口获取中文释义和学科分类，写入本地 SQLite 数据库。

项目刻意保持轻量：没有 GUI、托盘、弹窗、通知、云同步或开机启动注册。最终用户拿到 `dist/VocabularyCollector/` 后，双击 `VocabularyCollector.exe` 即可运行；首次使用前需要把 `config/config.example.toml` 复制为 `config/config.toml` 并填入自己的 key。程序启动后会在 `http://127.0.0.1:8765/` 提供 Web 词库页面（端口可配置）。

# Windows 环境与命令

- 本项目的开发、运行、打包环境是 Windows。终端命令、脚本和文档示例优先使用 PowerShell 与 `.ps1`。
- 不要使用或建议 `.sh` 脚本作为 Windows 上的执行方案；需要临时自动化时，使用 PowerShell 或 Python。
- 源码开发使用 Python >= 3.11 和 `uv`：`uv sync` 后以 `uv run python -m vocab_collector` 启动。
- 产物面向没有 Python、Node 或安装器的最终用户；打包后的 `VocabularyCollector.exe` 可直接运行。

# 运行行为与数据

- 捕获流程是：`Ctrl+C+C` -> 等待新剪贴板内容 -> 清洗选区 -> 调用 LLM -> 校验结果 -> SQLite 去重写入 -> 刷新词库页面。
- SQLite 数据库位于 `data/vocabulary.db`，运行日志位于 `data/collector.log`；这些都是运行时数据，不应进入发布包。
- Web 词库页面通过 Flask 服务提供，监听 `127.0.0.1:8765`（端口可在配置文件中修改）。
- 失败路径只记录日志，不写入数据库，也没有自动补录队列。这是当前有意保持的行为。
- 数据库使用大小写不敏感去重；`fsrs_*` 列只是预留字段，当前没有复习算法。
- 在用户可写且不受 OneDrive 同步影响的目录运行，避免 `data/` 无法写入。

# 安全、构建与测试

- README 是项目进度参照。开发项目前、开发过程中和开发完成后，都要及时更新 README：先将计划工作记录为待办项，实施时同步状态，完成后更新进度记录、使用方式和验证结果。
- 真实密钥只可存在于 `config/config.toml` 或用户明确指定的安全位置。该文件必须保持被忽略，不能记录、提交或复制到发布包。
- 构建命令是 `pwsh scripts/build.ps1`。`dist/VocabularyCollector/` 只包含 exe、依赖、资源、`config/config.example.toml`、`README.md` 和 `LICENSE`；不包含真实配置、`data/`、日志、数据库、缓存或本地测试产物。
- 默认验证命令是 `uv run pytest`。
- 修改打包、配置或路径逻辑后，至少运行 `uv run pytest tests/test_build_hygiene.py`。

# 当前进度

- 核心模块已完成：配置、路径解析、日志、LLM 调用、响应模型、剪贴板读取、全局热键、队列编排、SQLite 存储、HTML 导出和守护进程入口。
- 测试此前已在本机跑到 `77 passed`。
- PyInstaller onedir 打包流程已完成，产物位于 `dist/VocabularyCollector/`。
- 构建脚本只复制 `config/config.example.toml`，不会把真实的 `config/config.toml` 打进发布目录。
- `tests/test_build_hygiene.py` 会检查 `dist/` 中没有真实 key、没有真实 `config.toml`，并确认 `.gitignore` 覆盖敏感配置和运行数据。
- Web 词库页面已完成：Flask 服务监听 `127.0.0.1:8765`，支持搜索、分页、删除、亮/暗主题。

# 仍需注意

- 接口失败只写日志，不自动补录；这是当前的有意取舍。
- 数据库已预留 `fsrs_*` 列，但还没有复习算法。

# 开发约定

- 真实密钥只能放在 `config/config.toml` 或用户明确指定的安全位置；不要提交真实配置，也不要把真实配置复制进 release 包。
- 发布 zip 应以干净构建产物为准：包含 exe、依赖、资源、`config/config.example.toml`、`README.md` 和 `LICENSE`；排除真实配置、`data/`、日志、数据库、缓存和本地测试产物。
- 修改打包、配置或路径逻辑后，至少运行 `uv run pytest tests/test_build_hygiene.py`；改动核心逻辑后运行默认测试集。
- 每一小段任务完成后，例行收尾：1) 更新 README（进度、功能描述等）；2) `git add` + `git commit` + `git push` 推送到 GitHub。
