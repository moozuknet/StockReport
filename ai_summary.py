import os
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Callable, Dict, Optional
import pypdf

def extract_text_from_pdf(pdf_path: Path, max_pages: int = 5) -> str:
    """PDF 파일에서 텍스트를 추출합니다."""
    text = ""
    try:
        reader = pypdf.PdfReader(str(pdf_path))
        num_pages = min(len(reader.pages), max_pages)
        for i in range(num_pages):
            page_text = reader.pages[i].extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        text = f"[PDF 텍스트 추출 failure: {e}]"
    return text.strip()

def call_gemini_api(api_key: str, prompt: str) -> Optional[str]:
    """Google Gemini REST API를 호출하여 AI 요약을 생성합니다."""
    if not api_key:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            res_data = resp.json()
            candidates = res_data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
    except Exception as e:
        print(f"[Gemini API 호출 예외] {e}")

    return None

def generate_ai_summary_for_folder(
    save_dir: Path, 
    date_str: str, 
    gemini_api_key: str = "", 
    log_fn: Optional[Callable[[str], None]] = None
) -> str:
    """지정 폴더 내의 PDF 파일들을 분석하여 AI 요약 보고서를 생성 및 저장합니다."""
    def _log(msg: str):
        if log_fn:
            log_fn(msg)

    if not save_dir.exists():
        _log(f"⚠️ [AI 요약] 지정 폴더가 존재하지 않습니다: {save_dir}")
        return ""

    pdf_files = list(save_dir.glob("*.pdf"))
    if not pdf_files:
        _log(f"⚠️ [AI 요약] {date_str} 폴더 내 분석할 PDF 파일이 없습니다.")
        return ""

    _log(f"🤖 [AI 분석 요약 시작] 총 {len(pdf_files)}개 PDF 리포트 검토 중...")

    report_summaries: List[Dict[str, str]] = []
    combined_texts: List[str] = []

    for pdf_path in pdf_files[:15]:  # 최대 15개 리포트 분석
        file_name = pdf_path.stem
        extracted = extract_text_from_pdf(pdf_path, max_pages=3)
        combined_texts.append(f"### 리포트 파일: {file_name}\n{extracted[:800]}\n")
        report_summaries.append({
            "name": file_name,
            "snippet": extracted[:200].replace("\n", " ") if extracted else "내용 없음"
        })

    prompt_body = "\n---\n".join(combined_texts)
    full_prompt = (
        f"당신은 금융 및 증권 리서치 전문 AI 분석가입니다.\n"
        f"다음은 {date_str} 기준 증권사에서 발행한 리포트 주요 내용입니다.\n\n"
        f"{prompt_body}\n\n"
        f"위 리포트들을 바탕으로 다음 규칙에 맞게 종합 분석 보고서를 작성하세요:\n"
        f"1. 📌 핵심 요약 (3~5줄로 오늘 시장/종목 총평)\n"
        f"2. 🏢 주요 종목 리포트 분석 (종목명, 투자의견/목표가, 핵심 포인트)\n"
        f"3. 📊 주요 산업 및 시장 동향\n"
        f"4. 💡 투자 유의사항 및 시사점\n\n"
        f"가독성 높은 이모지와 마크다운 형식으로 작성해주세요."
    )

    ai_result_text = None
    if gemini_api_key:
        _log("🤖 Gemini API를 호출하여 AI 전문 종합 요약을 생성합니다...")
        ai_result_text = call_gemini_api(gemini_api_key, full_prompt)
        if ai_result_text:
            _log("✅ Gemini AI 요약 생성 성공!")

    if not ai_result_text:
        _log("ℹ️ [자체 추출 요약 모드] Gemini API 미설정 또는 호출 실패로 자체 추출 요약서를 생성합니다.")
        lines = [
            f"# 📊 증권 리포트 요약 보고서 ({date_str})",
            f"**분석 파일 수:** 총 {len(pdf_files)}개 리포트\n",
            "## 📌 수집 및 분석 리포트 목록"
        ]
        for idx, item in enumerate(report_summaries, 1):
            lines.append(f"{idx}. **{item['name']}**")
            if item['snippet']:
                lines.append(f"   - *요약*: {item['snippet']}...")
        ai_result_text = "\n".join(lines)

    # 요약 파일 저장 (MD & TXT)
    md_file = save_dir / f"AI_Report_Summary_{date_str}.md"
    txt_file = save_dir / f"AI_Report_Summary_{date_str}.txt"

    with open(md_file, "w", encoding="utf-8") as f:
        f.write(ai_result_text)

    with open(txt_file, "w", encoding="utf-8") as f:
        f.write(ai_result_text)

    _log(f"💾 [AI 요약 저장 완료] {md_file.name}")
    return ai_result_text
