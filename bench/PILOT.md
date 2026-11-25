# 三题真实试跑

题号、base commit、官方镜像 manifest 和臂顺序固定在 `pilot3.json`。三道 Django 题涵盖两道 ORM 查询和一道时间解析；选择纯 Python 项目，以便在当前 amd64 仿真环境验证 editable 安装。三道均从正式样本中剔除。每臂一次，T=128，Pi 1.6.0，gpt-4.1-mini-2025-04-14，每次至多 32 个模型请求、900 秒。同题按表内顺序运行，三题各有不同首臂。

每题预检在一次性官方镜像中 checkout base，执行官方采用的 `python -m pip install -e .`，确认 Django 从 /testbed 导入，并运行相应未加评分补丁的测试模块。预检通过后才启动付费 agent。模型只见公开题面。判分保留官方 resolved、构建证据及 runner 判定。空补丁、达到上限、回读为零和未触发题均保留。整题输入计未缓存输入加缓存读取，费用按 provider usage 和标准单价估算。

复现一臂使用 `bench/m0.py ROWS PI_LINUX NEW_OUTPUT --instance INSTANCE --arm ARM --preview-tokens 128`。ROWS 沿用 M0 的 JSON 格式，将官方 Verified parquet 中选定的完整行包装为 `{"rows":[{"row":记录,"truncated_cells":[]}]}`。镜像需使用清单中固定的 linux/amd64 manifest，并打上该题的官方 image 标签。完整运行产物在共享工作区 `runs/real-pilot-01/`。
