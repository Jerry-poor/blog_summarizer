import os
import glob
import json
import argparse
import datetime
from config import DATA_DIR, REPORTS_DIR, INDEX_DIR, FAISS_INDEX_FILE, META_FILE
from logger import logger

def generate_report(date_str):
    input_dir = os.path.join(DATA_DIR, date_str)
    if not os.path.isdir(input_dir):
        logger.info(f"没有找到数据目录：{input_dir}")
        return False

    summary_files = glob.glob(os.path.join(input_dir, "*_summary.json"))
    if not summary_files:
        logger.info(f"{date_str} 无摘要文件可生成报告")
        return False

    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_path = os.path.join(REPORTS_DIR, f"{date_str}-summary.md")

    try:
        with open(report_path, 'w', encoding='utf-8') as rf:
            count = len(summary_files)
            rf.write(f"# HF 博客日报 — {date_str}\n\n")
            rf.write(f"以下共有 {count} 篇博文，摘要如下：\n\n")
            for sf in summary_files:
                try:
                    with open(sf, encoding='utf-8') as f:
                        data = json.load(f)
                    title     = data.get("title", "")
                    link      = data.get("link", "")
                    published = data.get("published", "")
                    summary   = data.get("summary", "")
                    rf.write(f"## [{title}]({link}) （{published}）\n\n")
                    rf.write(f"{summary}\n\n")
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
    parser.add_argument('--date', type=str,
                        help='指定生成报告的日期，格式 YYYY-MM-DD，默认今天')
    return parser.parse_args()

def main():
    args = parse_args()
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
        logger.info(f"未生成 {date_str} 的日报")
    logger.info("Report 生成器完成")

def create_app():
    from flask import Flask, request, jsonify, send_file
    from flask_cors import CORS
    import subprocess

    # 导入 chat 相关工具
    from chat import load_api_defs, load_index_and_meta, retrieve_context, answer_query
    # 导入刷新流水线
    from refresh_today import refresh_pipeline

    app = Flask(__name__)
    CORS(app)

    @app.route('/api/report')
    def api_report():
        date_str = request.args.get('date') or datetime.date.today().isoformat()
        report_path = os.path.join(REPORTS_DIR, f"{date_str}-summary.md")
        if os.path.exists(report_path):
            return send_file(report_path, mimetype='text/markdown')
        else:
            return "Not found", 404

    @app.route('/api/refresh', methods=['POST'])
    def api_refresh():
        date_str = request.args.get('date')
        refresh_pipeline(date_str)
        return jsonify({'status': 'ok'})

    @app.route('/api/chat', methods=['POST'])
    def api_chat():
        data    = request.get_json(force=True)
        query   = data.get('question') or data.get('query')
        date_str= data.get('date')
        if not query:
            return jsonify({'error': '缺少 question'}), 400

        # 尝试加载索引和元数据
        index, meta = load_index_and_meta(date_str)
        if index is None or meta is None:
            # 若无索引，主动刷新当天全流程后重试
            refresh_pipeline(date_str)
            index, meta = load_index_and_meta(date_str)
            if index is None or meta is None:
                return jsonify({'error': '索引仍未就绪，请稍后重试'}), 503

        api_defs = load_api_defs()
        contexts = retrieve_context(query, index, meta, top_k=3)
        answer   = answer_query(query, contexts, api_defs)
        return jsonify({'answer': answer})

    return app

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'api':
        app = create_app()
        # debug=True 可在开发时自动重载
        app.run(host='0.0.0.0', port=8000)
    else:
        main()
