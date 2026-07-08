# tests/test_integration_agent.py
"""
역할 1~4 통합 파이프라인 테스트

실행:
    python -m tests.test_integration_agent

AWS 자격증명이나 Gemini API 키가 없는 로컬 환경에서도 전부 통과해야 한다.
"""

from src import integration_agent as ia


FAKE_TRANSCRIPT = {
    "department": "컴퓨터공학과",
    "student_year": 3,
    "total_credits": 80,
    "major_credits": 40,
    "general_credits": 25,
    "gpa": 3.9,
    "completed_courses": [
        {"course_name": "프로그래밍기초", "category": "전공필수",
         "credit": 3, "grade": "A+", "semester": "2023-1"},
        {"course_name": "자료구조", "category": "전공필수",
         "credit": 3, "grade": "A0", "semester": "2023-2"},
        {"course_name": "운영체제", "category": "전공필수",
         "credit": 3, "grade": "B+", "semester": "2024-1"},
    ],
    "warnings": [],
    "extraction_confidence": "high",
}

# 역할 2의 현재 실제 반환 형식 (JSON 문자열, summary만 있음)
FAKE_ROLE2_RAW = (
    '{"department": "컴퓨터공학과", "summary": "졸업요건 검색 결과...", '
    '"status": "success", "data_format": "structured"}'
)


def test_pipeline_runs_without_aws():
    """AWS/Gemini 없이도 mock으로 전체 파이프라인이 완주하는지."""
    report = ia.run_full_pipeline(pdf_path="no_such_file.pdf")

    assert isinstance(report, dict)
    assert "graduation_analysis" in report
    assert "course_recommendations" in report
    assert "scholarship_strategy" in report
    print("  [PASS] test_pipeline_runs_without_aws")


def test_normalize_role2_current_format():
    """역할 2의 현재 반환 형식(JSON 문자열 + summary)이 역할 3 형식으로 변환되는지."""
    data = ia.normalize_curriculum_requirements(FAKE_ROLE2_RAW, "컴퓨터공학과")

    assert isinstance(data, dict)
    assert data["department"] == "컴퓨터공학과"
    # 없는 값은 기본값으로 채워지고 경고가 남아야 한다
    assert isinstance(data["required_total_credits"], (int, float))
    assert isinstance(data["required_courses"], list)
    assert any("기본값" in w for w in data["warnings"])
    print("  [PASS] test_normalize_role2_current_format")


def test_normalize_full_format():
    """역할 2가 나중에 완전한 형식을 반환하면 그대로 통과되는지."""
    full = {
        "department": "컴퓨터공학과",
        "required_total_credits": 130,
        "required_major_credits": 60,
        "required_general_credits": 30,
        "required_courses": ["프로그래밍기초", "자료구조"],
    }
    data = ia.normalize_curriculum_requirements(full, "컴퓨터공학과")
    assert data["required_total_credits"] == 130
    assert data["required_courses"] == ["프로그래밍기초", "자료구조"]
    # 완전한 형식이면 '기본값' 경고가 없어야 한다
    assert not any("기본값" in w for w in data["warnings"])
    print("  [PASS] test_normalize_full_format")


def test_pipeline_with_fake_roles():
    """역할 1, 2가 성공했다고 가정하고 데이터가 역할 3~4까지 흐르는지."""
    orig_role1 = ia.analyze_transcript_pdf
    orig_role2 = ia.get_curriculum_requirements
    orig_exists = ia.os.path.exists

    try:
        ia.analyze_transcript_pdf = lambda pdf_path: dict(FAKE_TRANSCRIPT)
        ia.get_curriculum_requirements = lambda department: FAKE_ROLE2_RAW
        ia.os.path.exists = lambda p: True

        report = ia.run_full_pipeline(pdf_path="fake.pdf")

        # 역할 1 데이터 반영 확인
        assert report["student_summary"]["gpa"] == 3.9

        # 미이수 필수 과목 계산 확인 (기본 과목 목록 기준)
        missing = report["graduation_analysis"].get("missing_required_courses", [])
        assert "프로그래밍기초" not in missing
        assert "캡스톤디자인" in missing

        print("  [PASS] test_pipeline_with_fake_roles")
    finally:
        ia.analyze_transcript_pdf = orig_role1
        ia.get_curriculum_requirements = orig_role2
        ia.os.path.exists = orig_exists


def run_all():
    print("=== 통합 파이프라인 테스트 시작 ===")
    test_pipeline_runs_without_aws()
    test_normalize_role2_current_format()
    test_normalize_full_format()
    test_pipeline_with_fake_roles()
    print("=== 전체 테스트 통과 ===")


if __name__ == "__main__":
    run_all()
