# Day 1 任务清单（Windows 本机版）

> 架构已改：开发全部在本机完成，0 元。演示期（Day 5 后）再开按量付费云服务器。
> 用户机器：HUAWEI MCLG-XX，i5-13420H / 16GB RAM / Win11 家庭版 x64 —— 已验证够用。

## 前置：确认 Python

打开 **PowerShell**（Win 键搜「PowerShell」），输入：
```powershell
python --version
```
- 显示 `Python 3.10` 以上 → 跳过安装
- 报错或显示「不是内部或外部命令」→ 去 python.org 下 3.11/3.12 安装包，**安装时务必勾选 `Add Python to PATH`**
- 若自动跳到 Microsoft Store，直接关掉，用 python.org 的安装包

## 第 1 步：建项目虚拟环境（隔离依赖，不污染系统）

```powershell
cd D:\workbuddy\esg-checker
python -m venv venv
.\venv\Scripts\Activate.ps1
```
**验收**：命令行前面出现 `(venv)`。

若报「无法加载文件，因为在此系统上禁止运行脚本」，执行一次：
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
再重试激活。

## 第 2 步：装依赖（国内镜像，5–10 分钟）

```powershell
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
pip install --upgrade pip
pip install pymupdf rapidocr-onnxruntime openai pyyaml gradio sentence-transformers pandas
```

**验收**：
```powershell
python -c "import fitz, rapidocr_onnxruntime, openai, gradio, sentence_transformers; print('imports ok')"
```
打印 `imports ok` = 通过。

**已知坑**：`sentence-transformers` 会拉 torch，Windows 上约 2–3 GB，网速慢时要等。若卡住在下载 torch，中断后单独装 CPU 版：
```powershell
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

## 第 3 步：拉 BGE 模型（约 100MB，国内走镜像）

```powershell
$env:HF_ENDPOINT="https://hf-mirror.com"
python -c "from sentence_transformers import SentenceTransformer; m=SentenceTransformer('BAAI/bge-small-zh-v1.5'); print('dim =', len(m.encode(['测试'])[0]))"
```
**验收**：打印 `dim = 512`。

## 第 4 步：DeepSeek key 写入环境变量（不进代码）

```powershell
[Environment]::SetEnvironmentVariable("DEEPSEEK_API_KEY","你的key","User")
```
设完**关掉 PowerShell 重开**，验证：
```powershell
echo $env:DEEPSEEK_API_KEY
```
**验收**：打印出 key（非空）。

**注意**：key 只放环境变量，任何 .py 文件、README、截图里都不许出现。

## 第 5 步：冒烟测试（三绿灯最后一盏）

新建 `D:\workbuddy\esg-checker\smoke_test.py`：
```python
import os, fitz
from openai import OpenAI
from sentence_transformers import SentenceTransformer

# 1. PDF 解析
doc = fitz.open(r"D:\workbuddy\esg-checker\data\reports\changan_2025_esg.pdf")
print("[1] PDF 页数:", doc.page_count)

# 2. 本地 embedding
m = SentenceTransformer("BAAI/bge-small-zh-v1.5")
print("[2] embedding dim:", len(m.encode(["范围一温室气体排放量"])[0]))

# 3. DeepSeek 联通
c = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
r = c.chat.completions.create(model="deepseek-chat",
    messages=[{"role":"user","content":"回复两个字：联通"}], max_tokens=10)
print("[3] DeepSeek:", r.choices[0].message.content)
```
运行：
```powershell
python smoke_test.py
```

**验收（三绿灯）**：
```
[1] PDF 页数: 139
[2] embedding dim: 512
[3] DeepSeek: 联通
```

## Day 1 完成标准

三行输出全对 = 环境就绪，进 Day 2（人工标注 20–30 条，禁 AI 代填）。

## 翻车记录（从今天开始）

新建 `D:\workbuddy\esg-checker\docs\翻车记录.md`：
```
日期 | 现象（报错原文） | 我怎么定位的 | 怎么修的 | 花了多久
```
不要求今天有翻车。**但每个报错都必须原样抄进去，包括我帮你修的那次**——这是面试最能讲的部分。
