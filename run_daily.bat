@echo off
REM -------------------------------
REM Daily HF Blog Agent 批处理脚本
REM 在 Windows CMD 中运行，按顺序执行各模块
REM -------------------------------

REM 切换到批处理文件所在目录
cd /d %~dp0

REM 1. 抓取当天 Hugging Face 博客条目
REM 输出日志到 app.log
python scraper.py

REM 2. 分块并建立向量索引
python chunker_indexer.py

REM 3. 对文章生成中英双语摘要
python summarizer.py

REM 4. 汇总摘要，生成 Markdown 日报
python report.py

REM 完成
echo Daily HF Blog Report generation complete.
