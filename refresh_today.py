import datetime
import subprocess
from report import generate_report

def refresh_pipeline(date_str=None):
    if not date_str:
        date_str = datetime.date.today().isoformat()
    # 1. 爬虫抓取
    subprocess.run(['python', 'scraper.py', '--date', date_str])
    # 2. 摘要生成
    subprocess.run(['python', 'summarizer.py', '--date', date_str])
    # 3. 切片+索引
    subprocess.run(['python', 'chunker_indexer.py', '--date', date_str])
    # 4. 汇总日报
    generate_report(date_str)

if __name__ == "__main__":
    import sys
    date_str = sys.argv[1] if len(sys.argv) > 1 else None
    refresh_pipeline(date_str)
