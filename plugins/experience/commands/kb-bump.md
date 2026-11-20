# /kb-bump

【经验库】把个人技巧升档或标否定；改 methods-personal 索引与卡面 strength，不打 PR。

## 怎么做

1. 解析引擎路径（同 `/kb-note`）。
2. 执行：`python3 <kb> technique bump <id|path|文件名> [--to used|repeated|contradicted|hypothesis]`
3. 省略 `--to` 时按 hypothesis→used→repeated 递进。
4. 以 CLI 打印的 JSON 为准。