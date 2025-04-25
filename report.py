import os
import glob
import json
import argparse
import datetime
from config import DATA_DIR, REPORTS_DIR
from logger import logger

def generate_report(date_str):
    # 对应的数据目录
    input_dir = os.path.join(DATA_DIR, date_str)
    # 如果目录不存在，则退出
    if not os.path.isdir(input_dir):
        logger.info(f"没有找到数据目录：{input_dir}")
        return False

    # 查找所有已生成的摘要文件
    summary_files = glob.glob(os.path.join(input_dir, "*_summary.json"))
    if not summary_files:
        logger.info(f"{date_str} 无摘要文件可生成报告")
        return False

    # 确保报告目录存在
    os.makedirs(REPORTS_DIR, exist_ok=True)
    # 报告输出路径，如 reports/2025-04-26-summary.md
    report_path = os.path.join(REPORTS_DIR, f"{date_str}-summary.md")

    try:
        with open(report_path, 'w', encoding='utf-8') as rf:
            # 写入标题
            count = len(summary_files)
            rf.write(f"# HF 博客日报 — {date_str}\n\n")
            rf.write(f"以下共有 {count} 篇博文，摘要如下：\n\n")
            # 逐篇拼接摘要
            for sf in summary_files:
                try:
                    with open(sf, encoding='utf-8') as f:
                        data = json.load(f)
                    title     = data.get("title", "")
                    link      = data.get("link", "")
                    published = data.get("published", "")
                    summary   = data.get("summary", "")
                    # 写入文章标题和链接
                    rf.write(f"## [{title}]({link}) （{published}）\n\n")
                    # 写入摘要正文
                    rf.write(f"{summary}\n\n")
                    # 分隔线
                    rf.write("---\n\n")
                except Exception as ex:
                    logger.error(f"处理摘要文件失败：{sf}，错误：{ex}")
        logger.info(f"已生成日报：{report_path}")
        return True
    except Exception as ex:
        logger.error(f"写入报告失败：{ex}")
        return False

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--date', type=str,
        help='指定生成报告的日期，格式 YYYY-MM-DD，默认今天'
    )
    return parser.parse_args()

def main():
    args = parse_args()
    # 确定日期字符串
    if args.date:
        try:
            dt = datetime.date.fromisoformat(args.date)
            date_str = dt.isoformat()
        except ValueError:
            logger.error(f"非法日期格式: {args.date}")
            return
    else:
        date_str = datetime.date.today().isoformat()

    logger.info(f"Report 生成器启动 for date: {date_str}")
    success = generate_report(date_str)
    if not success:
        # 无报告时返回 False，可供上层脚本处理
        logger.info(f"未生成 {date_str} 的日报")
    logger.info("Report 生成器完成")

if __name__ == "__main__":
    main()
