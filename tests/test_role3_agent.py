from src.agent import create_strategy_report, format_strategy_report


transcript_data = {
    "department": "컴퓨터공학과",
    "student_year": 2,
    "total_credits": 42,
    "major_credits": 18,
    "general_credits": 15,
    "gpa": 4.1,
    "completed_courses": [
        {
            "course_name": "프로그래밍기초",
            "category": "전공필수",
            "credit": 3,
            "grade": "A0",
            "semester": "2024-1"
        },
        {
            "course_name": "컴퓨터개론",
            "category": "전공선택",
            "credit": 3,
            "grade": "A+",
            "semester": "2024-1"
        },
        {
            "course_name": "자료구조",
            "category": "전공필수",
            "credit": 3,
            "grade": "B+",
            "semester": "2024-2"
        },
        {
            "course_name": "글쓰기",
            "category": "교양필수",
            "credit": 2,
            "grade": "A0",
            "semester": "2024-2"
        }
    ],
    "warnings": [],
    "extraction_confidence": "high"
}

curriculum_requirements = {
    "department": "컴퓨터공학과",
    "required_total_credits": 130,
    "required_major_credits": 60,
    "required_general_credits": 30,
    "required_courses": [
        "프로그래밍기초",
        "자료구조",
        "컴퓨터구조",
        "운영체제",
        "데이터베이스",
        "캡스톤디자인"
    ],
    "source_pdf": "curriculum_latest.pdf",
    "last_synced_at": "2026-07-08",
    "warnings": []
}


scholarship_policy = {
    "source": "순천대학교 장학 제도 홈페이지",
    "last_synced_at": "2026-07-08",
    "content": """
성적우수장학금은 직전학기 성적, 이수학점, 학과별 석차 등을 종합적으로 고려하여 선발한다.
일부 교내 장학금은 직전학기 일정 학점 이상 이수와 일정 평점 이상을 요구할 수 있다.
국가장학금은 한국장학재단 기준에 따라 소득구간, 성적 기준, 이수학점 기준 등을 충족해야 한다.
장학금별 세부 기준은 매 학기 공지되는 장학 안내문을 반드시 확인해야 한다.
"""
}

def run_test():
    strategy_report = create_strategy_report(
        transcript_data=transcript_data,
        curriculum_requirements=curriculum_requirements,
        scholarship_policy=scholarship_policy
    )

    print(format_strategy_report(strategy_report))

    assert strategy_report["graduation_analysis"]["remaining_total_credits"] == 88
    assert strategy_report["graduation_analysis"]["remaining_major_credits"] == 42
    assert strategy_report["graduation_analysis"]["remaining_general_credits"] == 15

    assert "컴퓨터구조" in strategy_report["graduation_analysis"]["missing_required_courses"]
    assert "운영체제" in strategy_report["graduation_analysis"]["missing_required_courses"]

    assert len(strategy_report["course_recommendations"]) > 0

    assert "scholarship_strategy" in strategy_report
    assert "possibility" in strategy_report["scholarship_strategy"]
    assert "advice" in strategy_report["scholarship_strategy"]

    print("\n역할 3 테스트 성공")


if __name__ == "__main__":
    run_test()