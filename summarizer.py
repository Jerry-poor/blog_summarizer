import os
import json
import glob
import argparse
import datetime
import requests
from config import DATA_DIR, SUMMARY_CHUNK_SIZE, API_DEF_FILE, SUMMARIZER_KEY
from logger import logger

# 从 api.json 读取接口定义
def load_api_defs():
    with open(API_DEF_FILE, encoding='utf-8') as f:
        return json.load(f)

# 增加 --date 支持
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--date', type=str,
        help='指定生成摘要的日期，格式 YYYY-MM-DD，默认今天'
    )
    return parser.parse_args()

# 按 SUMMARY_CHUNK_SIZE 切分文本
def chunk_text(text, size=SUMMARY_CHUNK_SIZE):
    if len(text) <= size:
        return [text]
    return [text[i:i+size] for i in range(0, len(text), size)]

# 调用 Gemini generateContent 生成中英对照学术风格 Abstract
def summarize_text(text, api_defs):
    ep = api_defs["summarize"]
    # 拼接带 key 的 URL
    url = f"{ep['url']}?key={ep['api_key']}"
    # 构造请求体，要求中英对照、学术 Abstract 风格、不超过200字
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "请以学术摘要（Abstract）的形式，对以下内容做中英对照："
                            "每一句中文紧跟英文一句，整体不超过200字，保留关键公式和术语。\n\n"
                            f"{text}"
                        )
                    }
                ]
            }
        ]
    }
    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    j = resp.json()
    # 从响应中提取文本
    try:
        return j["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        # 防护：若格式不符则返回原 text
        return text[:SUMMARY_CHUNK_SIZE]

# 处理单篇文章并保存摘要
def process_article(file_path, api_defs):
    # 读取文章 JSON，优先用 content，再 fallback summary
    with open(file_path, encoding='utf-8') as f:
        data = json.load(f)
    content = data.get("content", "").strip()
    if len(content) < 50:
        content = data.get("summary", "").strip()
    text = content or "（正文获取失败，请查看原文）"

    # 切分并摘要，合并为一个 Abstract
    chunks = chunk_text(text)
    abstracts = []
    for chunk in chunks:
        try:
            ab = summarize_text(chunk, api_defs)
            abstracts.append(ab)
        except Exception as ex:
            logger.error(f"摘要失败：{file_path}，错误：{ex}")
    full_summary = "\n\n".join(abstracts)

    # 保存到 *_summary.json
    base = os.path.splitext(file_path)[0]
    summary_path = f"{base}_summary.json"
    out = {
        "title":     data.get("title", ""),
        "link":      data.get("link", ""),
        "published": data.get("published", ""),
        "summary":   full_summary
    }
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved summary: {summary_path}")
    return summary_path

def main():
    args = parse_args()
    # 确定日期目录
    if args.date:
        try:
            dt = datetime.date.fromisoformat(args.date)
            date_str = dt.isoformat()
        except ValueError:
            logger.error(f"非法日期格式: {args.date}")
            return
    else:
        date_str = datetime.date.today().isoformat()

    logger.info(f"Summarizer started for date: {date_str}")
    api_defs = load_api_defs()

    # 找到该日期下的原始条目文件
    dir_path = os.path.join(DATA_DIR, date_str)
    if not os.path.isdir(dir_path):
        logger.info(f"未找到目录：{dir_path}")
        return

    # 仅处理原始 JSON，不包含已有摘要文件
    files = [f for f in glob.glob(os.path.join(dir_path, "*.json"))
             if not f.endswith("_summary.json")]
    if not files:
        logger.info(f"{date_str} 无待摘要文件")
        return

    # 为每篇文章生成 Abstract 样式中英对照摘要
    for fp in files:
        process_article(fp, api_defs)

    logger.info("Summarizer finished")

if __name__ == "__main__":
    main()
