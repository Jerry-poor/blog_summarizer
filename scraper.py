import os
import json
import datetime
import hashlib
import argparse
import requests
import feedparser
from bs4 import BeautifulSoup
from config import DATA_DIR, API_DEF_FILE, BLOG_RSS_URL
from logger import logger

# 加载本地 api.json 定义
def load_api_defs():
    # 从 API_DEF_FILE 读取 JSON
    with open(API_DEF_FILE, encoding='utf-8') as f:
        return json.load(f)

# 抓取博客 RSS 条目
def fetch_blog_entries(api_defs):
    # 如果 api.json 中定义了 getBlogRSS，则使用该接口
    if "getBlogRSS" in api_defs:
        ep = api_defs["getBlogRSS"]
        resp = requests.request(ep["method"], ep["url"], headers=ep.get("headers"))
    else:
        # 否则使用 config 中的 RSS URL
        resp = requests.get(BLOG_RSS_URL)
    resp.raise_for_status()
    return feedparser.parse(resp.text).entries

# 按指定日期过滤条目
def filter_by_date(entries, target_date):
    result = []
    for e in entries:
        if hasattr(e, "published_parsed"):
            pub = datetime.date(*e.published_parsed[:3])
            if pub == target_date:
                result.append(e)
    return result

# 将条目保存为本地 JSON 文件
def save_entries(entries, date_str):
    # 按日期在 data 目录下创建子目录
    dir_path = os.path.join(DATA_DIR, date_str)
    os.makedirs(dir_path, exist_ok=True)

    for e in entries:
        link = e.link
        # 用链接 MD5 生成唯一文件名
        entry_id = hashlib.md5(link.encode('utf-8')).hexdigest()
        file_path = os.path.join(dir_path, f"{entry_id}.json")

        # 抓取页面并解析正文
        content = ""
        try:
            page = requests.get(link, timeout=10)
            page.raise_for_status()
            soup = BeautifulSoup(page.text, 'html.parser')
            # 尝试找到最可能的文章节点
            container = (
                soup.find("article") or
                soup.find("div", class_="markdown") or
                soup.find("div", class_="markdown-body") or
                soup.find("main")
            )
            if container:
                content = container.get_text(separator="\n", strip=True)
            else:
                # 回退到整页文本
                content = soup.get_text(separator="\n", strip=True)
        except Exception as ex:
            logger.warning(f"抓取全文失败：{link}，错误：{ex}")

        # 如果抓取失败，降级到 RSS summary/description
        summary = ""
        if hasattr(e, 'summary'):
            summary = e.summary
        elif hasattr(e, 'description'):
            summary = e.description
        if not content:
            content = summary

        data = {
            "title":     e.title,
            "link":      link,
            "published": datetime.date(*e.published_parsed[:3]).isoformat(),
            "summary":   summary,
            "content":   content
        }

        try:
            # 写入 JSON 并格式化
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved entry: {file_path}")
        except Exception as ex:
            logger.error(f"Failed saving entry {entry_id}: {ex}")

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', type=str,
                        help='指定抓取日期，格式 YYYY-MM-DD')
    parser.add_argument('--all', action='store_true',
                        help='不按日期过滤，保存所有抓取到的条目')
    args = parser.parse_args()

    # 确定目标日期
    if args.date:
        try:
            target_date = datetime.date.fromisoformat(args.date)
        except ValueError:
            logger.error(f"非法的日期格式: {args.date}, 应为 YYYY-MM-DD")
            return
    else:
        target_date = datetime.date.today()

    logger.info(f"Scraper started for date: {target_date.isoformat()}")
    api_defs = load_api_defs()
    try:
        entries = fetch_blog_entries(api_defs)
    except Exception as ex:
        logger.error(f"Failed fetching blog entries: {ex}")
        return

    # 根据参数决定保存哪些条目
    to_save = entries if args.all else filter_by_date(entries, target_date)
    if not to_save:
        logger.info(f"No blog entries to save for date: {target_date.isoformat()}")
    else:
        save_entries(to_save, target_date.isoformat())

    logger.info("Scraper finished")

if __name__ == "__main__":
    main()
