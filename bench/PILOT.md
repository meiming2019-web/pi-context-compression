# 三题真实试跑

题号、base commit、官方镜像 manifest 和臂顺序固定在 `pilot3.json`。三道 Django 题涵盖两道 ORM 查询和一道时间解析；选择纯 Python 项目，以便在当前 amd64 仿真环境验证 editable 安装。三道均从正式样本中剔除。每臂一次，T=128，Pi 1.6.0，gpt-4.1-mini-2025-04-14，每次至多 32 个模型请求、900 秒。同题按表内顺序运行，三题各有不同首臂。

每题预检在一次性官方镜像中 checkout base，执行官方采用的 `python -m pip install -e .`，确认 Django 从 /testbed 导入，并运行相应未加评分补丁的测试模块。预检通过后才启动付费 agent。模型只见公开题面。判分保留官方 resolved、构建证据及 runner 判定。空补丁、达到上限、回读为零和未触发题均保留。整题输入计未缓存输入加缓存读取，费用按 provider usage 和标准单价估算。

复现一臂使用 `bench/m0.py ROWS PI_LINUX NEW_OUTPUT --instance INSTANCE --arm ARM --preview-tokens 128`。ROWS 沿用 M0 的 JSON 格式，将官方 Verified parquet 中选定的完整行包装为 `{"rows":[{"row":记录,"truncated_cells":[]}]}`。镜像需使用清单中固定的 linux/amd64 manifest，并打上该题的官方 image 标签。完整运行产物在共享工作区 `runs/real-pilot-01/`。

## 原版 Pi 校准与后续配对协议

校准固定 10 道新题，详见 `calibration10.json` 的顺序、base、镜像 manifest 与预检测试模块。候选取自 Verified 的 Django 3.0，聚焦可用 SQLite 验证的 Python 行为，包括 HTTP 响应、表单、ORM 和管理命令。这是定向校准集。每题 A 一次，模型沿用 gpt-4.1-mini-2025-04-14，64 次请求、900 秒。保留所有尝试，预检失败和评分缺失单列。只纳入自行完成且通过官方评分和环境检查的题。校准十题全部完成后，按锁定顺序取前五道；不足五道就结束本阶段，另立换题或换模型的校准批次。

锁题后每题重新运行 A **两次**。这两个独立重复对应本批 T=128 的两轮 B/C。校准的成功运行仅用于选题，保留率分母只来自独立 A 重跑，逐次报告 A 的翻转和缺失。所有配置共享调用上限 64；若选中题的成功校准运行恰用满 64，则统一改为 128。入选题的结果仅解释原版曾解出的条件子集。

本批范围在十题校准后收窄为五道锁题、同题 A/B/C、各两次，仅用 T=128，共 30 次。C 对 B 比较相同预览预算下的保留位置，C 对 A 比较换用扩展的整题效果。每题先平均两轮，再取五道题的配对差中位数；逐题列出通过次数、整题输入及费用。预算内通过、自然完成可判定通过、触顶和判分缺失分别计数。未触发预览的运行照常纳入。原版校准日志中的长输出包括目录列表、搜索结果、缺失工具和 Django 设置错误，缺乏因果证据的诊断位置留作未知。T=512 和固定尾长策略留待另行立项。

运行前锁定的题号和完整顺序见 [五题配对清单](paired5.json)。第一轮从六种 A/B/C 排列中用种子 20261125 不放回抽取五种，第二轮逐题逆序。每次使用全新容器。记录首个 provider 响应的缓存读取 tokens，零标 cold、正数标 warm、缺失标 unknown。

更换模型需另立实验版本，核对该版本对应的 tokenizer、编码与定价，并校验预览 token 预算；同步更新未缓存输入、缓存读取和输出的 USD 单价，再做离线探针及 A 校准。当前 o200k_base 与标准价绑定本次 gpt-4.1-mini 快照。

单独复现中继上限可在项目根目录运行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=bench python3.12 -m unittest -v test_relay`。不需要 Docker、网络或真实密钥。
