import os


# Base directory 
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
API_DEF_FILE = os.path.join(BASE_DIR, 'api.json')
BLOG_RSS_URL = 'https://huggingface.co/blog/feed.xml'
DATA_DIR = os.path.join(BASE_DIR, 'data')

#FAISS storage directory
INDEX_DIR = os.path.join(BASE_DIR, 'index')
FAISS_INDEX_FILE = os.path.join(INDEX_DIR, 'faiss_index.bin')
META_FILE = os.path.join(INDEX_DIR, 'meta.json')

REPORTS_DIR = os.path.join(BASE_DIR, 'reports')

#Log
LOG_FILE = os.path.join(BASE_DIR, 'app.log')


# Approximate number of characters per retrieval chunk
RETRIEVAL_CHUNK_SIZE = 500

# Approximate number of characters per summarization chunk
SUMMARY_CHUNK_SIZE = 2000

EMBEDDING_MODEL = 'sentence-transformers/LaBSE'

SUMMARIZER_KEY = 'summarize'
