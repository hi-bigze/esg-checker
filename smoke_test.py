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
    messages=[{"role": "user", "content": "回复两个字：联通"}], max_tokens=10)
print("[3] DeepSeek:", r.choices[0].message.content)
