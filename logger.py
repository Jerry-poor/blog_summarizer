import logging
import os
from config import LOG_FILE

# 确保日志目录存在
log_dir = os.path.dirname(LOG_FILE)
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 创建 logger 实例
logger = logging.getLogger('hf_daily_agent')
logger.setLevel(logging.INFO)

# 创建文件处理器，将日志写入文件
file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setLevel(logging.INFO)

# 创建控制台处理器，方便在 CMD 中查看输出
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# 定义日志输出格式
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# 将处理器添加到 logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)
