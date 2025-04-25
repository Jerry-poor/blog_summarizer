import os
import sys
import subprocess
import datetime
import dateparser
from config import REPORTS_DIR
from logger import logger

def parse_date(input_str):
    # 用 dateparser 支持多种日期格式和相对日期
    dt = dateparser.parse(
        input_str,
        languages=['zh', 'en'],
        settings={
            'PREFER_DATES_FROM': 'past',
            'RELATIVE_BASE': datetime.datetime.now()
        }
    )
    return dt.date() if dt else None

def ensure_report_for(date_str):
    """
    对应日期生成报告的流水线调用，
    假设各脚本新增了 --date 参数来处理指定日期
    """
    cmds = [
        ['python', 'scraper.py', '--date', date_str],
        ['python', 'chunker_indexer.py', '--date', date_str],
        ['python', 'summarizer.py', '--date', date_str],
        ['python', 'report.py', '--date', date_str]
    ]
    for cmd in cmds:
        logger.info(f"Running: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Step failed: {' '.join(cmd)} → {e}")
            return False
    return True

def view_report():
    # 首先尝试今天
    today = datetime.date.today()
    today_file = os.path.join(REPORTS_DIR, f"{today.isoformat()}-summary.md")
    if os.path.exists(today_file):
        print(open(today_file, encoding='utf-8').read())
        return

    # 没有今天的，进入日期选择
    print("wow，今天没有新的报告欸，不过可以看看以往的日报，你想看哪天的呢？")
    while True:
        user_input = input("> ").strip()
        if user_input.lower() in ("exit", "quit"):
            print("已退出查看日报。")
            return

        parsed = parse_date(user_input)
        if not parsed:
            print("无法识别日期格式，请重试（例如：昨天、2025-4-25、4月25、4.25）")
            continue

        date_str = parsed.isoformat()
        report_file = os.path.join(REPORTS_DIR, f"{date_str}-summary.md")
        if not os.path.exists(report_file):
            # 先尝试自动生成
            print(f"正在尝试抓取并生成 {date_str} 的日报，请稍候…")
            success = ensure_report_for(date_str)
            if success and os.path.exists(report_file):
                print(open(report_file, encoding='utf-8').read())
                return
            else:
                print(f"但这天也没有新内容欸（{date_str}），请换个日期或输入 exit 退出。")
                continue

        # 如果已存在，直接打印
        print(open(report_file, encoding='utf-8').read())
        return

if __name__ == "__main__":
    logger.info("ViewReport 模块启动")
    view_report()
    logger.info("ViewReport 模块结束")
