#!/bin/bash
# Day 1 环境安装脚本 —— 在腾讯云 Linux 服务器上执行
# 用法：整段粘贴到 SSH 终端，或保存为 day1_setup.sh 后 bash day1_setup.sh
# 每一步都有验证方式，任何一步报错立即停下，把报错原文贴回对话

set -e
echo "=== 0. 前置确认 ==="
python3 --version || { echo "无 python3，先: apt install -y python3 python3-venv python3-pip (Ubuntu) / yum install -y python3 (CentOS)"; exit 1; }
free -h | head -2
df -h / | tail -1
# 验收：python3 >= 3.10，内存 >= 4G（不够用 swap，见 checklist），磁盘剩余 >= 10G

echo "=== 1. 项目目录 ==="
mkdir -p ~/esg-checker && cd ~/esg-checker
mkdir -p data/reports rules src docs

echo "=== 2. 虚拟环境 + 国内镜像 ==="
python3 -m venv venv
source venv/bin/activate
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
# 验收：pip config list 显示 tuna 镜像

echo "=== 3. 核心依赖 ==="
pip install --upgrade pip
pip install pymupdf rapidocr-onnxruntime openai pyyaml gradio pandas
# 说明：
#   pymupdf              PDF 解析（本机已验证比 pypdf 快且稳）
#   rapidocr-onnxruntime 表格数字 OCR（长安绩效表字体编码问题，CPU 可跑）
#   openai               DeepSeek 兼容 openai 协议，用 base_url 指向 deepseek
#   gradio               Day 5 人工复核界面
# 验收：python -c "import fitz, rapidocr_onnxruntime, openai, gradio; print('imports ok')"

echo "=== 4. BGE embedding 模型（本地，不走 API） ==="
pip install sentence-transformers
export HF_ENDPOINT=https://hf-mirror.com   # 国内拉 HuggingFace 模型用镜像
python - <<'EOF'
from sentence_transformers import SentenceTransformer
m = SentenceTransformer('BAAI/bge-small-zh-v1.5')
v = m.encode(['范围一温室气体排放量为吨二氧化碳当量'])
print('embedding dim =', len(v[0]))
EOF
# 验收：输出 embedding dim = 512。模型约 100MB，已缓存到 ~/.cache
# 注意：以后每次新终端都要先 export HF_ENDPOINT=https://hf-mirror.com，或写进 ~/.bashrc

echo "=== 5. DeepSeek key 写入环境变量 ==="
echo 'export DEEPSEEK_API_KEY="你的key粘在这里"' >> ~/.bashrc
echo 'export HF_ENDPOINT=https://hf-mirror.com' >> ~/.bashrc
source ~/.bashrc
# 验收：echo $DEEPSEEK_API_KEY 非空。key 不进任何代码文件

echo "=== 6. 冒烟测试：DeepSeek 联通 ==="
python - <<'EOF'
import os
from openai import OpenAI
c = OpenAI(api_key=os.environ['DEEPSEEK_API_KEY'], base_url='https://api.deepseek.com')
r = c.chat.completions.create(model='deepseek-chat',
    messages=[{'role':'user','content':'回复两个字：联通'}], max_tokens=10)
print('DeepSeek 回复:', r.choices[0].message.content)
EOF
# 验收：打印「联通」

echo "=== 全部通过 = Day 1 环境完成 ==="
