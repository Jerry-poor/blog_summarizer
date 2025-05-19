import os
import json
import re
import faiss
import requests
from sentence_transformers import SentenceTransformer
from config import INDEX_DIR, API_DEF_FILE, EMBEDDING_MODEL, REPORTS_DIR
from logger import logger
from refresh_today import refresh_pipeline

CLI_HISTORY_FILE = 'cli_history.json'
# 日期格式匹配 YYYY-MM-DD
date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')

def load_api_defs():
    with open(API_DEF_FILE, encoding='utf-8') as f:
        return json.load(f)

def load_index_and_meta(date_str):
    """根据日期加载对应的 FAISS 索引和 meta 文件"""
    idx_path = os.path.join(INDEX_DIR, f"{date_str}_faiss.index")
    meta_path = os.path.join(INDEX_DIR, f"{date_str}_meta.json")
    if not os.path.exists(idx_path) or not os.path.exists(meta_path):
        logger.error(f"索引或元数据不存在：{idx_path}, {meta_path}")
        return None, None

    index = faiss.read_index(idx_path)
    with open(meta_path, encoding='utf-8') as f:
        meta = json.load(f)
    return index, meta

def retrieve_context(query, index, meta, top_k=4):
    """
    从索引中检索出 top_k 个最相关的文本片段，默认 4 段
    """
    embedder = SentenceTransformer(EMBEDDING_MODEL)
    qvec = embedder.encode([query], convert_to_numpy=True)
    D, I = index.search(qvec, top_k)
    return [meta[i]['text'] for i in I[0]]

def answer_query(query, contexts, api_defs):
    """
    构造增强型 prompt，要求回答专业、详尽，分点阐述并举例
    """
    ep = api_defs.get("summarize")
    url = f"{ep['url']}?key={ep['api_key']}"

    # 拼接上下文段落
    context_str = "\n\n".join(contexts)
    # 构造强指令 prompt
    prompt = (
        "你是资深技术专家，回答要既专业又详尽。"
        "请基于以下文章片段，分点阐述，给出背景原理，并举例说明：\n\n"
        + context_str +
        f"\n\n用户提问：{query}\n\n"
        "请输出结构清晰、逻辑严谨的完整回答。"
    )

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    j = resp.json()
    # 返回模型生成的文本
    return j["candidates"][0]["content"]["parts"][0]["text"].strip()

# CLI 部分保留原有逻辑

def load_cli_history():
    if os.path.exists(CLI_HISTORY_FILE):
        return json.load(open(CLI_HISTORY_FILE, encoding='utf-8'))
    return []

def save_cli_history(history):
    with open(CLI_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def print_report(date_str):
    path = os.path.join(REPORTS_DIR, f"{date_str}-summary.md")
    if os.path.exists(path):
        print(f"\n===== {date_str} 博客日报 =====\n")
        print(open(path, encoding='utf-8').read())
        print("\n" + "="*30 + "\n")
        return True
    else:
        print(f" 未找到 {date_str} 的报告")
        return False

def main():
    logger.info("启动 CLI 聊天/报告工具")
    history = load_cli_history()
    print(" 历史报告：" + (", ".join(history) if history else "（空）"))
    current_date = None

    while True:
        inp = input("> ").strip()
        if inp.lower() in ("exit", "quit"):
            print(" 退出")
            break
        if inp.lower() == "history":
            print(" 报告历史：" + (", ".join(history) or "（空）"))
            continue

        if date_pattern.match(inp):
            date_str = inp
            print(f" 刷新 {date_str} 全流程…")
            refresh_pipeline(date_str)
            if print_report(date_str):
                if date_str not in history:
                    history.insert(0, date_str)
                    if len(history) > 20:
                        history.pop()
                    save_cli_history(history)
                current_date = date_str
            continue

        if not current_date:
            print(" 请先输入一个日期 (YYYY-MM-DD) 来加载报告")
            continue

        query = inp
        print(" 检索并生成回答…")
        api_defs = load_api_defs()
        index, meta = load_index_and_meta(current_date)
        if index is None:
            print(" 索引不存在，正在重建…")
            refresh_pipeline(current_date)
            index, meta = load_index_and_meta(current_date)
            if index is None:
                print(" 索引重建失败，请稍后重试")
                continue

        try:
            contexts = retrieve_context(query, index, meta)
            answer = answer_query(query, contexts, api_defs)
            print(f"\n 回答：\n{answer}\n")
        except Exception as e:
            logger.error(f"问答出错：{e}")
            print(f" 回答失败：{e}")

if __name__ == "__main__":
    main()
