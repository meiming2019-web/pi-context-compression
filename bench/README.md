# M0 单题复现

在项目根目录运行以下命令。需要可运行 linux/amd64 容器的 Docker、Python 3.12、npm 和宿主环境中的 `OPENAI_API_KEY`。Apple Silicon 可使用启用了 amd64 仿真的 Colima。Python Docker SDK 需要连接同一个 daemon，Colima 默认实例通常使用 `export DOCKER_HOST="unix://$HOME/.colima/default/docker.sock"`。

```sh
mkdir -p runs/setup/pi/bin
python3.12 -m venv runs/setup/venv
runs/setup/venv/bin/pip install swebench==5.0.2
curl -fLsS 'https://datasets-server.huggingface.co/first-rows?dataset=SWE-bench%2FSWE-bench_Verified&config=default&split=test' -o runs/setup/first-rows.json
npm install --prefix runs/setup/pi --ignore-scripts --no-audit --no-fund @earendil-works/pi-coding-agent@1.6.0
npm pack node-linux-x64@24.11.1 --pack-destination runs/setup
tar -xzf runs/setup/node-linux-x64-24.11.1.tgz -C runs/setup/pi/bin --strip-components 2 package/bin/node
image=swebench/sweb.eval.x86_64.astropy_1776_astropy-12907
digest=sha256:7485c1e3c8861efd0c6a4a78b952857592e541031039000d25e9481f045dc4a3
docker pull --platform linux/amd64 "$image@$digest"
docker tag "$image@$digest" "$image:latest"
runs/setup/venv/bin/python bench/m0.py runs/setup/first-rows.json runs/setup/pi runs/my-m0-a
```

每次运行使用新的结果目录。加载原版 Pi 之前，runner 在题目容器内恢复官方 base commit，并检查工作树干净且只有一个可达提交。模型进程使用普通用户，通过回环地址调用固定模型。宿主转发模型请求，密钥和评分输入均留在宿主。Pi 有 900 秒和 32 次模型请求的上限。

`events.jsonl` 是原始工具轨迹。`model.patch` 包含相对 base 的修改和新增文件。`predictions.jsonl` 是交给评分器的输入。官方评分器另起容器，在 `logs/run_evaluation/` 下保存实际应用的补丁、测试输出和逐题报告。可比较两份补丁的 SHA-256，再核对报告的 `resolved` 字段。若只有 `grader.log` 而无测试结果，请在日志中定位基础设施故障。

只复核评分时可复用已有补丁，无需再次调用模型。在结果目录执行，使用上述虚拟环境的 Python 和新的唯一 run ID。

```sh
python -m swebench.harness.run_evaluation --dataset_name "$PWD/grader-input.json" \
  --predictions_path "$PWD/predictions.jsonl" --instance_ids astropy__astropy-12907 \
  --run_id "review-$(uuidgen)" --max_workers 1
```

## 审查后的记账和判分

每个尝试保留两项状态。`status` 记录 Pi 如何结束，例如 `completed`、`timeout`、`limit_hit` 或 `agent_error`。`grade_status` 记录补丁的处置。超时或撞上限后，runner 停住遗留的工具进程，用独立 Git index 收集当时的工作树。有效的非空补丁照常送评，空补丁记为未解决。三臂沿用 M0 的 32 次转发、900 秒和 128,000 token 上下文窗口，以便比较。提示词为本实验自定义文本。

- `requests.jsonl` 按请求记下开始与返回，保留超时前已发出请求的记录。取服务端 usage，将 prompt tokens 拆成未缓存输入与缓存读取。以每百万 token 的 USD 0.40、0.10、1.60 分别折算未缓存输入、缓存读取与输出。`cost_usd` 是标准价估算；若有请求缺少 usage，完整费用填 null，已知部分另存 `known_cost_usd`，缺失数记在 `calls_without_usage`。Pi 事件的用量独立保留，避免重复计费。模拟响应中的估算不产生真实账单。[模型定价](https://developers.openai.com/api/docs/models/gpt-4.1-mini)
- 扩展应将全文与索引写入 `PI_PREVIEW_ARCHIVE_DIR`，当前为 `/home/nonroot/pi-preview-archive`。收集器按 Git 规则收集相对题目 base 的修改、删除和新增文件，`added_paths` 列出新增路径。任意层级的 `.pytest_cache` 和 `__pycache__` 从最终补丁中排除，`excluded_cache_paths` 记录收集时发现的未跟踪缓存（含被忽略的文件）及相对 base 有变化的缓存。已暂存或已提交的缓存同样排除。若剩余补丁含 `.pi`、`.pi-preview` 或 `pi-preview-archive` 路径组件，整份补丁保存供复核，并标为 `patch_contaminated`。测试文件按路径命名约定标记。不能被官方 JSON 接口无损表示的非 UTF-8 补丁也留档。
- `official_resolved` 保存官方结论。对本题只解析官方日志里实际执行的 editable pip 安装步骤。`env_build_ok` 为 false 表示有失败证据，null 表示无法验证。两者均标为 `grade_status=infra`、`resolved=null`，整次尝试及用量保留。推广到其他构建方式前应增加对应校验。正式配对分析时单列基础设施故障及缺失配对。

在项目根目录运行 `PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest discover -s bench -v` 可复核日志、计费与补丁检查。另有四份断网容器验证产物位于本地 `runs/review-fixture-*-02/`。这些用真实 Pi、模拟模型响应；对有补丁的场景，测试截获评分命令并检查 prediction。它们用于验证控制流程，正式评测应剔除。
