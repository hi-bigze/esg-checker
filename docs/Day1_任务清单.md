# Day 1 任务清单（腾讯云服务器）

## 前置（本机，10 分钟）

1. **开通/确认服务器**：腾讯云控制台 → 轻量应用服务器（或 CVM）→ 记下公网 IP
2. **SSH 连通**：
   ```bash
   ssh root@你的公网IP
   ```
   连不上最常见两个原因：控制台防火墙没放行 22 端口、密码/密钥错。报错贴回来。
3. **上传两份年报**（本机 Git Bash 执行）：
   ```bash
   scp D:/workbuddy/esg-checker/data/reports/*.pdf root@你的公网IP:~/esg-checker/data/reports/
   ```
   注意：先在服务器上 `mkdir -p ~/esg-checker/data/reports`，或先跑安装脚本第 1 步再传。
4. **上传安装脚本**：
   ```bash
   scp D:/workbuddy/esg-checker/day1_setup.sh root@你的公网IP:~/
   ```

## 服务器上（20–40 分钟，取决于网速）

5. `bash ~/day1_setup.sh` —— **任何一步报错立即停**，把报错原文原样贴回对话，不要自己改脚本
6. 脚本内每步都有「验收」注释，六步全过 = 环境完成

## 已知风险与对策

| 风险 | 信号 | 对策 |
|---|---|---|
| 内存不足（2G 小机器装不动 sentence-transformers） | pip install 或模型加载被 OOM kill | `fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile` |
| HuggingFace 拉模型超时 | 卡在下载不动 | 确认 `echo $HF_ENDPOINT` 是 hf-mirror.com，重跑第 4 步 |
| DeepSeek 余额不足 | 402 错误 | 控制台充值（本周期 10 元足够） |
| 端口 7860 没开（Day 5 才用） | 届时 Gradio 打不开 | 腾讯云控制台防火墙放行 7860，先不用管 |

## Day 1 完成的验收标准（三绿灯）

- [ ] 服务器上 `python -c "import fitz, rapidocr_onnxruntime, openai, gradio"` 无报错
- [ ] BGE 输出 `embedding dim = 512`
- [ ] DeepSeek 冒烟测试打印「联通」

三个绿灯全亮，截图或复制终端输出发我，进 Day 2（人工标注 20–30 条，这是全项目最重要的一天，规则见 `esg-checker/docs/D1_任务清单.md` 的手工核查纪律——ground truth 禁止 AI 代填）。

## 翻车记录（从今天开始记）

新建 `~/esg-checker/docs/翻车记录.md`，格式：
```
日期 | 现象（报错原文） | 我怎么定位的 | 怎么修的 | 花了多久
```
Day 1 如果一次跑顺，也记一行「无翻车」——面试时「我预判了 OCR 坑并提前验证」本身就是素材。
