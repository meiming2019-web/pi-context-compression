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
