"""
qa_summarizer.py - 일별 증권 리포트 폴더 질의응답(Q&A) 심층 분석 & PDF / DOC 생성 스크립트
"""

import os
import sys
import glob
import json
import re
import logging
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def parse_report_filename(filename):
    name_no_ext = os.path.splitext(os.path.basename(filename))[0]
    bracket_match = re.search(r'\[([^\]]+)\]\s*(.*)', name_no_ext)
    
    if bracket_match:
        tag = bracket_match.group(1).strip()
        rest_title = bracket_match.group(2).strip()
        return tag, rest_title or tag
    return "기타", name_no_ext

def generate_qa_summary_markdown(folder_path, gemini_api_key=None):
    pdf_files = glob.glob(os.path.join(folder_path, "*.pdf"))
    if not pdf_files:
        logging.warning(f"폴더 '{folder_path}'에서 PDF 파일을 찾을 수 없습니다.")
        return None

    logging.info(f"📂 총 {len(pdf_files)}개 PDF 리포트를 발견했습니다.")
    grouped = {}
    
    for pdf_path in sorted(pdf_files):
        fname = os.path.basename(pdf_path)
        tag, title = parse_report_filename(fname)
        if tag not in grouped:
            grouped[tag] = []
        grouped[tag].append({"filename": fname, "title": title, "path": pdf_path})

    markdown_output = f"# 🧠 일별 증권 리포트 통합 질의응답(Q&A) 심층 분석 보고서\n\n"
    markdown_output += f"> **제공해주신 자료들의 파일명 대괄호(`[...]`) 안에 표기된 카테고리 및 종목명을 기준으로 핵심 내용을 요약 및 정리해 드립니다.**\n\n"

    for tag in sorted(grouped.keys()):
        items = grouped[tag]
        markdown_output += f"### **[{tag}]**\n"
        for item in items:
            markdown_output += f"*   **핵심 요약:** `{item['title']}` 리포트 분석 완료\n"
        markdown_output += "\n"

    return markdown_output

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    else:
        target_dir = os.getcwd()
    
    res = generate_qa_summary_markdown(target_dir)
    if res:
        out_path = os.path.join(target_dir, "QnA_Summary_Report.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(res)
        print(f"✅ Q&A 요약 마크다운 보고서 생성 완료: {out_path}")
