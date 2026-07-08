# src/integration_agent.py
"""
순천대학교 전략 큐레이터 - 통합 실행 파일 (v2)

docs/interface_contract.md 의 흐름을 따른다:
  1. 역할 1: analyze_transcript_pdf(pdf_path)            → transcript_data
  2. 역할 2: sync_latest_curriculum_pdf()                → 최신 교육과정 PDF 탐색
  3. 역할 2: get_curriculum_requirements(department)     → curriculum_requirements
  4. 역할 3: create_strategy_report(...)                 → strategy_report
  5. 역할 4: sanitize_strategy_report(strategy_report)   → 개인정보 마스킹

각 단계가 실패해도 (라이브러리 미설치, AWS 자격증명 없음 등)
mock 데이터로 파이프라인이 끝까지 돌아가고, warnings에 사유를 남긴다.

실행:
    python -m src.integration_agent
    python -m src.integration_agent --pdf data/samples/xxx.pdf
"""

import argparse
import json
import os
from datetime import datetime


# ─────────────────────────────────────────────
# 역할 3 (필수 의존성 - 없으면 즉시 에러)
# ─────────────────────────────────────────────
from src.agent import create_strategy_report, format_strategy_report


# ─────────────────────────────────────────────
# 역할 1 (실패해도 파이프라인이 죽지 않도록 try import)
# ─────────────────────────────────────────────
try:
    from src.transcript_agent import analyze_transcript_pdf
    ROLE1_IMPORT_ERROR = None
except ImportError as e:
    analyze_transcript_pdf = None
    ROLE1_IMPORT_ERROR = str(e)


# ─────────────────────────────────────────────
# 역할 2
# ─────────────────────────────────────────────
try:
    from src.curriculum_rag import get_curriculum_requirements
    ROLE2_RAG_IMPORT_ERROR = None
except ImportError as e:
    get_curriculum_requirements = None
    ROLE2_RAG_IMPORT_ERROR = str(e)

try:
    from src.curriculum_sync import sync_latest_curriculum_pdf
    ROLE2_SYNC_IMPORT_ERROR = None
except ImportError as e:  # requests / beautifulsoup4 미설치 등
    sync_latest_curriculum_pdf = None
    ROLE2_SYNC_IMPORT_ERROR = str(e)


# ─────────────────────────────────────────────
# 역할 4 (개인정보 마스킹 - 없으면 마스킹 없이 진행)
# ─────────────────────────────────────────────
try:
    from src.guardrails import sanitize_strategy_report
except ImportError:
    sanitize_strategy_report = None


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


# ─────────────────────────────────────────────
# Mock 데이터 (해당 역할 실행 실패 시 사용)
# ─────────────────────────────────────────────

def get_mock_transcript_data() -> dict:
    return {
        "department": "컴퓨터공학과",
        "student_year": 2,
        "total_credits": 42,
        "major_credits": 18,
        "general_credits": 15,
        "gpa": 4.1,
        "completed_courses": [
            {"course_name": "프로그래밍기초", "category": "전공필수",
             "credit": 3, "grade": "A0", "semester": "2024-1"},
            {"course_name": "자료구조", "category": "전공필수",
             "credit": 3, "grade": "B+", "semester": "2024-2"},
        ],
        "warnings": ["역할 1 PDF 분석이 실행되지 않아 임시 성적 데이터를 사용했습니다."],
        "extraction_confidence": "low",
    }


def get_mock_curriculum_requirements(department: str | None) -> dict:
    return {
        "department": department or "컴퓨터공학과",
        "required_total_credits": 130,
        "required_major_credits": 60,
        "required_general_credits": 30,
        "required_courses": [
            "프로그래밍기초", "자료구조", "컴퓨터구조",
            "운영체제", "데이터베이스", "캡스톤디자인",
        ],
        "source_pdf": "mock_curriculum_latest.pdf",
        "last_synced_at": _today(),
        "warnings": ["역할 2 RAG가 실행되지 않아 임시 교육과정 데이터를 사용했습니다."],
    }


def get_mock_scholarship_policy() -> dict:
    return {
        "source": "mock_scholarship_policy",
        "last_synced_at": _today(),
        "content": (
            "성적우수장학금은 직전학기 성적, 이수학점, 학과별 석차 등을 "
            "종합적으로 고려하여 선발한다. "
            "국가장학금은 한국장학재단 기준에 따라 소득구간, 성적 기준, "
            "이수학점 기준 등을 충족해야 한다. "
            "장학금별 세부 기준은 매 학기 공지되는 장학 안내문을 확인해야 한다."
        ),
    }


# ─────────────────────────────────────────────
# 역할 2 결과 정규화 어댑터
#
# 현재 get_curriculum_requirements()는 JSON "문자열"을 반환하고,
# 구조도 {department, summary, status, ...} 형태라서
# 역할 3이 기대하는 curriculum_requirements 형식과 다르다.
# 여기서 형식을 맞추고, 부족한 값은 mock으로 보충한다.
# ─────────────────────────────────────────────

REQUIRED_CURRICULUM_KEYS = [
    "required_total_credits",
    "required_major_credits",
    "required_general_credits",
]


def normalize_curriculum_requirements(raw, department: str) -> dict:
    warnings = []

    # 1) 문자열이면 JSON 파싱
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raise ValueError("역할 2 반환값이 JSON 형식이 아닙니다.")

    if not isinstance(raw, dict):
        raise ValueError(f"역할 2 반환값이 dict가 아닙니다: {type(raw)}")

    data = dict(raw)
    mock = get_mock_curriculum_requirements(department)

    # 2) 역할 3이 필요로 하는 숫자 키 보충
    for key in REQUIRED_CURRICULUM_KEYS:
        if not isinstance(data.get(key), (int, float)):
            # 임시 값을 넣지 않고 빈 값(None)으로 둔 뒤 상태를 기록합니다.
            data[key] = None
            warnings.append(f"오류: {key} 정보를 교육과정 편람에서 찾을 수 없어 분석이 불가능합니다.")

    # 3) 전공필수 과목 목록 보충
    if not isinstance(data.get("required_courses"), list) or not data.get("required_courses"):
        data["required_courses"] = mock["required_courses"]
        warnings.append("역할 2 결과에 전공필수 과목 목록이 없어 기본값을 사용했습니다.")

    data.setdefault("department", department)
    data.setdefault("source_pdf", "bedrock_knowledge_base")
    data["last_synced_at"] = _today()
    data["warnings"] = data.get("warnings", []) + warnings

    return data


# ─────────────────────────────────────────────
# 역할별 실행 함수
# ─────────────────────────────────────────────

def get_pdf_path(pdf_path: str | None = None) -> str:
    if pdf_path:
        return pdf_path
    return os.environ.get(
        "TRANSCRIPT_SAMPLE_PATH",
        "data/samples/sample_transcript_anonymized.pdf",
    )


def run_role1(pdf_path: str) -> dict:
    print("===== 역할 1 실행: 성적증명서 PDF AI 분석 =====")

    if analyze_transcript_pdf is None:
        print(f"역할 1 모듈을 불러오지 못했습니다: {ROLE1_IMPORT_ERROR}")
        print("임시 transcript_data를 사용합니다.")
        return get_mock_transcript_data()

    if not os.path.exists(pdf_path):
        print(f"성적증명서 PDF가 없습니다: {pdf_path}")
        print("임시 transcript_data를 사용합니다.")
        return get_mock_transcript_data()

    try:
        transcript_data = analyze_transcript_pdf(pdf_path)
    except Exception as e:
        print(f"역할 1 PDF 분석 중 오류: {e}")
        print("임시 transcript_data를 사용합니다.")
        return get_mock_transcript_data()

    # AI 호출은 됐지만 추출 실패로 빈 결과가 온 경우 → mock으로 대체
    if not transcript_data.get("completed_courses") or not transcript_data.get("department"):
        error_warnings = transcript_data.get("warnings", [])
        print("역할 1 추출 결과가 비어 있어 임시 transcript_data를 사용합니다.")
        for w in error_warnings:
            print(f"  (원인: {w})")
        mock = get_mock_transcript_data()
        mock["warnings"] = mock["warnings"] + error_warnings
        return mock

    print("역할 1 완료 / 학과:", transcript_data.get("department"),
          "/ GPA:", transcript_data.get("gpa"))
    return transcript_data


def run_role2_sync() -> None:
    print("\n===== 역할 2 실행: 최신 교육과정 PDF 탐색 =====")

    if sync_latest_curriculum_pdf is None:
        print(f"교육과정 동기화 모듈을 불러오지 못했습니다: {ROLE2_SYNC_IMPORT_ERROR}")
        return None

    try:
        sync_latest_curriculum_pdf()
    except Exception as e:
        print(f"교육과정 PDF 탐색 중 오류: {e}")
    return None


def run_role2_curriculum(transcript_data: dict, department: str | None = None) -> dict:
    """department 인자를 주면 (예: UI 입력값) 성적표의 학과보다 우선 사용한다."""
    print("\n===== 역할 2 실행: 교육과정 Knowledge Base 검색 =====")

    department = department or transcript_data.get("department") or "컴퓨터공학과"

    if get_curriculum_requirements is None:
        print(f"역할 2 RAG 모듈을 불러오지 못했습니다: {ROLE2_RAG_IMPORT_ERROR}")
        print("임시 curriculum_requirements를 사용합니다.")
        return get_mock_curriculum_requirements(department)

    try:
        raw = get_curriculum_requirements(department, student_year=transcript_data.get("admission_year"))
        curriculum_requirements = normalize_curriculum_requirements(raw, department)
    except Exception as e:
        print(f"교육과정 검색 중 오류: {e}")
        # 오류가 나면 임시 데이터를 주는 대신, 분석이 불가능하다는 상태를 반환합니다.
        return {
            "department": department,
            "status": "error",
            "message": "교육과정 기준을 확인하지 못해 분석할 수 없습니다.",
            "warnings": [f"검색 오류: {e}"]
        }

    print("역할 2 교육과정 검색 완료 / 학과:",
          curriculum_requirements.get("department"))
    return curriculum_requirements


try:
    from src.scholarship_rag import get_scholarship_policy
except ImportError:
    get_scholarship_policy = None

def run_role2_scholarship_policy() -> dict:
    print("\n===== 역할 2 실행: 장학 제도 정보 =====")
    
    if get_scholarship_policy is None:
        print("장학 제도 조회 함수(scholarship_rag)가 없어 임시 scholarship_policy를 사용합니다.")
        return get_mock_scholarship_policy()
        
    try:
        policy = get_scholarship_policy()
        print("장학 제도 Knowledge Base 검색 완료")
        return policy
    except Exception as e:
        print(f"장학 제도 검색 중 오류: {e}")
        return {
            "source": "error",
            "last_synced_at": _today(),
            "content": f"장학 정보를 불러올 수 없습니다. 오류: {e}"
        }


def run_role3(
    transcript_data: dict,
    curriculum_requirements: dict,
    scholarship_policy: dict,
) -> dict:
    print("\n===== 역할 3 실행: 전략 분석 =====")

    strategy_report = create_strategy_report(
        transcript_data=transcript_data,
        curriculum_requirements=curriculum_requirements,
        scholarship_policy=scholarship_policy,
    )

    print("역할 3 전략 분석 완료")
    return strategy_report


def run_role4_sanitize(strategy_report: dict) -> dict:
    print("\n===== 역할 4 실행: 개인정보 마스킹 =====")

    if sanitize_strategy_report is None:
        print("guardrails 모듈이 없어 마스킹 없이 진행합니다.")
        return strategy_report

    try:
        safe_report = sanitize_strategy_report(strategy_report)
        print("역할 4 마스킹 완료")
        return safe_report
    except Exception as e:
        print(f"마스킹 중 오류: {e} / 마스킹 없이 진행합니다.")
        return strategy_report


# ─────────────────────────────────────────────
# 통합 파이프라인
# ─────────────────────────────────────────────

def run_full_pipeline(pdf_path: str | None = None, 
department: str | None = None, user_request: str | None = None) -> dict:
    final_pdf_path = get_pdf_path(pdf_path)

    print("===== 순천대학교 전략 큐레이터 통합 실행 =====")
    print("성적증명서 PDF:", final_pdf_path)

    transcript_data = run_role1(final_pdf_path)

    # run_role2_sync()  # <-- 학교 홈페이지 PDF 스크래핑 기능 제거 (AWS S3 Knowledge Base 사용)

    curriculum_requirements = run_role2_curriculum(transcript_data, department=department)
    scholarship_policy = run_role2_scholarship_policy()

    strategy_report = run_role3(
        transcript_data=transcript_data,
        curriculum_requirements=curriculum_requirements,
        scholarship_policy=scholarship_policy,
    )

    safe_report = run_role4_sanitize(strategy_report)

    print("\n===== 최종 보고서 =====")
    print(format_strategy_report(safe_report))

    return safe_report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="역할 1~4 통합 실행")
    parser.add_argument("--pdf", help="성적증명서 PDF 경로")
    args = parser.parse_args()

    run_full_pipeline(pdf_path=args.pdf)
