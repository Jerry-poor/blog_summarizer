import os
import json
import faiss
import requests
from sentence_transformers import SentenceTransformer
from config import INDEX_DIR, FAISS_INDEX_FILE, META_FILE, API_DEF_FILE, EMBEDDING_MODEL
from logger import logger

# 加载本地 api.json 定义
def load_api_defs():
    with open(API_DEF_FILE, encoding='utf-8') as f:
        return json.load(f)

# 加载 FAISS 索引和元数据
def load_index_and_meta():
    index_path = FAISS_INDEX_FILE
    meta_path  = META_FILE
    if not os.path.exists(index_path) or not os.path.exists(meta_path):
        logger.error("FAISS 索引或元数据文件不存在，请先运行 chunker_indexer.py")
        return None, None
    # 读取索引
    index = faiss.read_index(index_path)
    # 加载 meta 列表
    with open(meta_path, encoding='utf-8') as f:
        meta = json.load(f)
    return index, meta

# 基于查询检索 top_k 个相关 chunk 文本
def retrieve_context(query, index, meta, top_k=3):
    # 初始化多语种编码器
    embedder = SentenceTransformer(EMBEDDING_MODEL)
    # 对查询做向量化
    qvec = embedder.encode([query], convert_to_numpy=True)
    # 索引搜索（内积近似余弦相似度）
    D, I = index.search(qvec, top_k)
    contexts = []
    for idx in I[0]:
        # 从 meta 中获取对应文本
        entry = meta[idx]
        contexts.append(entry['text'])
    return contexts

# 调用 LLM 接口生成回答，基于检索到的上下文
def answer_query(query, contexts, api_defs):
    ep = api_defs["summarize"]
    url = f"{ep['url']}?key={ep['api_key']}"
    # 把上下文和问题拼进一个文本里
    context_str = "\n".join(contexts)
    prompt = (
        "你是一个严谨的 AI 助手，基于以下文章段落回答，不要编造：\n\n"
        f"{context_str}\n\n提问：{query}"
    )
    payload = {
        "contents": [
            {
                "parts": [
                    { "text": prompt }
                ]
            }
        ]
    }
    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    j = resp.json()
    return j["candidates"][0]["content"]["parts"][0]["text"].strip()


def main():
    logger.info("Chat 模块启动")
    api_defs = load_api_defs()
    index, meta = load_index_and_meta()
    if index is None or meta is None:
        return

    # CLI 循环
    print("输入问题并回车 (输入 'exit' 或 'quit' 退出)：")
    while True:
        query = input("> ").strip()
        if query.lower() in ("exit", "quit"):
            print("退出 Chat。")
            break
        if not query:
            continue
        try:
            # 检索相关上下文
            contexts = retrieve_context(query, index, meta, top_k=3)
            # 生成并打印回答
            answer = answer_query(query, contexts, api_defs)
            print(f"\n📝 回答：\n{answer}\n")
        except Exception as ex:
            logger.error(f"回答过程出错：{ex}")
            print(f"⚠️ 回答失败：{ex}")

    logger.info("Chat 模块结束")

if __name__ == "__main__":
    main()
