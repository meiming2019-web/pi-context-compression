# Pi 长日志预览实验

这是 Codex 和 DeepSeek 共用的本地项目。研究问题是：给 Pi 同等 token 预算的 bash 日志预览，保留头尾能否减少回读和整题成本，同时维持修复表现？

## 实验约定

| 组别 | bash 输出预览 |
| --- | --- |
| A | 使用固定版本 Pi 的默认策略 |
| B | 预算 T 内保留尾部，计入状态、提示和全文路径 |
| C | 同样预算 T，扣除状态、提示和全文路径后，头尾各用一半 |

主比较为同题 C 对 B。SWE-bench Verified 提供任务，官方评分器检查最终补丁。三组固定模型、Pi 版本和运行限制。记录每题的通过情况、token 用量、费用和日志回读。

## 当前进度

M0 已完成。原版 Pi 1.6.0 使用 `gpt-4.1-mini-2025-04-14` 运行了试跑题 `astropy__astropy-12907`。Pi 自验 11 项通过，SWE-bench 5.0.2 独立容器评分为 `resolved: true`。2 项 FAIL_TO_PASS 与 13 项 PASS_TO_PASS 均通过。本题从正式样本中剔除。

这次基线用了 24 次模型响应。Pi 记录的非缓存输入为 15,722 tokens，缓存读取为 144,128 tokens，输出为 1,469 tokens。B/C 尚待实现和评测。

复现命令见 [M0 单题复现](bench/README.md)。本地共享产物位于 `runs/m0-a-01/`，run ID 为 `m0-213d1c64bf5c`。提交的补丁、prediction 里的补丁和评分器实际使用的补丁三者字节一致，SHA-256 为 `62a53d8d1b2f2e539f8c672424aff0956e3f3c2648e8fe020584199477af279d`。

本机使用 arm64 上的 amd64 仿真。官方评分脚本尝试重新安装 Astropy 时 GCC 段错误，随后在预装环境中运行 pytest，15 项通过。额外用新的同镜像容器应用同一补丁，确认预装 Python 导入 `/testbed/astropy/modeling/separable.py`，Git blob 为 `3252330e`，与模型补丁目标一致。详见本地 `test_output.txt` 和 `runs/m0-a-01/import-check.txt`。

## 当前分工和接口

- **Codex 主责代码、测试和运行。** 先在 `bench/` 跑通一题原版 Pi 的 runner、补丁收集和官方评分，再在 `extension/` 实现 B/C 预览、归档回读和 token 预算测试。评测产物写入 `runs/`，由 Codex 修复审查发现的问题。
- **DeepSeek 主责审查。** M0 核对题目隔离、补丁是否相对原始提交完整收集，以及官方评分报告能否追溯到该补丁。B/C 阶段核对两臂的预算、退出状态、回读与计费口径，检查结论能否由逐题数据支持。
- **Runner 接口。** 三组使用 Pi 1.6.0 和相同的模型、工具、隔离配置与运行上限。A 组用 `pi --no-extensions` 禁用扩展发现，保留标准工具。B/C 使用相同参数，另加 `-e /path/to/extension/index.ts`；该路径为约定入口，待 Codex 实现。用环境变量 `PI_PREVIEW_ARM=B|C` 选择策略，`PI_PREVIEW_TOKENS` 设置共用预算。路径应在 Pi 进程所在环境中可访问。正式评测前一起锁定模型、tokenizer 和 T。

## 两边怎么协作

每个里程碑由 Codex 提交代码并给出提交号、验证命令和结果路径。M0 另附题号、base commit、Pi 版本、模型、补丁与评分报告。DeepSeek 按提交审查，用文件位置、复现步骤或运行证据反馈问题。Codex 完成修复后提供对应提交，供 DeepSeek 复核。
