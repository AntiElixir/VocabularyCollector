# vocab-collector

一个常驻后台的小工具：在任意程序里选中英文单词，按 `Ctrl+C+C`，它会调用你的
SJTU LLM 取回中文释义和学科，写进本地数据库，并刷新一个可以浏览的网页。

程序本身不做任何提示音、弹窗或托盘图标，也不注册开机启动。

## First run

1. 把 `config/config.example.toml` 复制成 `config/config.toml`。
2. 打开 `config/config.toml`，把 `api_key` 换成你自己的真实 key。
3. 双击 `VocabularyCollector.exe` 启动（源码方式则是 `uv run python -m vocab_collector`）。
4. 第一次启动时它会自动建好 `data/` 目录和日志文件。

配置含义：`base_url`/`model` 指向模型服务，`timeout_seconds`/`max_retries` 控制请求，
`max_selection_chars` 限制单词长度，`double_tap_window_ms` 是两次 C 之间允许的间隔，
`clipboard_wait_ms` 是等待剪贴板更新的最长时间，`log_level` 控制日志级别。

## 用法

选中一个英文单词，在按住 Ctrl 的同时连按两次 C。只会读取你自己 `Ctrl+C` 已经放进剪贴板的
内容，不会替换或拦截正常复制。同一个单词（不区分大小写）只记录一次。

## Where is my vocabulary?

`data/vocabulary.html`。用浏览器直接打开即可，每次成功记录后都会自动刷新。表格按时间倒序，
只有 english / chinese / domain / created_at 四列。

## Where is the log?

`data/collector.log`，1 MB 轮转、保留 3 份。识别到超时、无效选区或接口失败时都会写在这里，
失败时会把单词和原因一起记下来，方便你事后手工补录。

## Known limitations

- 以管理员权限运行的程序（UIPI）看不到你的手势。
- 终端里 `Ctrl+C` 不是复制，所以终端中可能无法触发。
- 受保护的扫描版 PDF 里选不中文字，自然也无法复制。
- 没有重试队列：接口失败只写日志，不会自动补录。
- 选中的是一整行代码这类“垃圾输入”也会被当成单词送出去，最多记录失败。
- 电脑休眠唤醒后如果手势失灵，重启程序即可。
- 请安装在用户可写、且不在 OneDrive 同步目录里的位置，否则 `data/` 可能写不进去。

## 明确不做的事

没有 GUI、托盘、弹窗、通知、发音、例句、复习算法（Anki/FSRS）、统计、云同步或服务器。
数据库里为 FSRS 预留了几个空列，但没有任何复习逻辑。