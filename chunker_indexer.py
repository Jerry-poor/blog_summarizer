import os
import json
import glob
import argparse
import datetime
from sentence_transformers import SentenceTransformer
import faiss
from config import DATA_DIR, INDEX_DIR, FAISS_INDEX_FILE, META_FILE, EMBEDDING_MODEL
from logger import logger

# 设置检索切块大小
CHUNK_SIZE = 128

def chunk_text(text, size=CHUNK_SIZE):
    chunks = [text[i:i+size] for i in range(0, len(text), size)]
    return chunks

def collect_chunks_for_date(date_str):
    all_chunks = []
    dir_path = os.path.join(DATA_DIR, date_str)
    if not os.path.isdir(dir_path):
        logger.info(f"没有找到数据目录：{dir_path}")
        return all_chunks
    # 先加载 *_summary.json，再加载原始 JSON
    files = sorted(glob.glob(os.path.join(dir_path, '*_summary.json'))) + \
            sorted([f for f in glob.glob(os.path.join(dir_path, '*.json'))
                    if not f.endswith('_summary.json')])
    for file_path in files:
        with open(file_path, encoding='utf-8') as f:
            data = json.load(f)
        text = data.get('summary') or data.get('content', '')
        if text:
            for chunk in chunk_text(text):
                all_chunks.append((os.path.splitext(os.path.basename(file_path))[0], chunk))
    logger.info(f"共收集到 {len(all_chunks)} 切块")
    return all_chunks

def build_faiss_index(chunks):
    # 1. 计算 embeddings
    embedder = SentenceTransformer(EMBEDDING_MODEL)
    texts = [c for _, c in chunks]
    embeddings = embedder.encode(texts, convert_to_numpy=True)

    dim = embeddings.shape[1]
    logger.info(f"Embedding 完成，维度={dim}")

    # 2. 在 GPU 上构建 IndexFlatIP
    res = faiss.StandardGpuResources()            # 分配 GPU 资源
    cpu_index = faiss.IndexFlatIP(dim)            # 在 CPU 上先创建索引结构
    gpu_index = faiss.index_cpu_to_gpu(res, 0, cpu_index)  # 把它搬到 GPU: device 0
    gpu_index.add(embeddings)                     # 在 GPU 上添加向量
    logger.info(f"GPU 上已添加 {gpu_index.ntotal} 个向量")

    # 3. 可选：把 GPU 索引搬回 CPU 以便持久化
    cpu_index = faiss.index_gpu_to_cpu(gpu_index)
    os.makedirs(INDEX_DIR, exist_ok=True)
    faiss.write_index(cpu_index, FAISS_INDEX_FILE)
    logger.info(f"已将 GPU 索引保存到 {FAISS_INDEX_FILE}")

    # 4. 保存元数据
    meta = []
    for idx, (entry_id, txt) in enumerate(chunks):
        meta.append({'chunk_id': idx, 'entry_id': entry_id, 'text': txt})
    with open(META_FILE, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    logger.info(f"已保存元数据，共 {len(meta)} 条")

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', type=str, help='指定日期 YYYY-MM-DD（默认今天）')
    return parser.parse_args()

def main():
    args = parse_args()
    date_str = args.date if args.date else datetime.date.today().isoformat()
    logger.info(f"Chunker/Indexer 启动 for date {date_str}")

    chunks = collect_chunks_for_date(date_str)
    if not chunks:
        logger.info("无切块，跳过索引构建")
        return

    try:
        build_faiss_index(chunks)
    except Exception as e:
        logger.error(f"构建 FAISS GPU 索引失败：{e}")
    logger.info("Chunker/Indexer 完成")

if __name__ == "__main__":
    main()
