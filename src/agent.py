from src.graduation_analyzer import compare_graduation_requirements
from src.course_recommender import recommend_next_courses
from src.scholarship_analyzer import analyze_scholarship_possibility


def create_strategy_report(
    transcript_data: dict,
    curriculum_requirements: dict,
    scholarship_policy: dict | None = None
) -> dict:
    graduation_analysis = compare_graduation_requirements(
        transcript_data=transcript_data,
        curriculum_requirements=curriculum_requirements
    )

    course_recommendations = recommend_next_courses(
        transcript_data=transcript_data,
        curriculum_requirements=curriculum_requirements,
        graduation_analysis=graduation_analysis
    )

    scholarship_strategy = analyze_scholarship_possibility(
        transcript_data=transcript_data,
        scholarship_policy=scholarship_policy
    )

    warnings = []

    warnings.extend(transcript_data.get("warnings", []))
    warnings.extend(curriculum_requirements.get("warnings", []))
    warnings.extend(graduation_analysis.get("warnings", []))
    warnings.extend(scholarship_strategy.get("warnings", []))

    warnings = list(dict.fromkeys(warnings))

    return {
        "student_summary": {
            "department": transcript_data.get("department"),
            "student_year": transcript_data.get("student_year"),
            "gpa": transcript_data.get("gpa"),
            "extraction_confidence": transcript_data.get("extraction_confidence"),
        },
        "curriculum_source": {
            "source_pdf": curriculum_requirements.get("source_pdf"),
            "last_synced_at": curriculum_requirements.get("last_synced_at"),
        },
        "graduation_analysis": graduation_analysis,
        "course_recommendations": course_recommendations,
        "scholarship_strategy": scholarship_strategy,
        "warnings": warnings,
    }

def format_strategy_report(strategy_report: dict) -> str:
    student_summary = strategy_report.get("student_summary", {})
    curriculum_source = strategy_report.get("curriculum_source", {})
    graduation_analysis = strategy_report.get("graduation_analysis", {})
    course_recommendations = strategy_report.get("course_recommendations", [])
    scholarship_strategy = strategy_report.get("scholarship_strategy", {})
    warnings = strategy_report.get("warnings", [])

    lines = []

    lines.append("===== 순천대학교 전략 큐레이터 분석 결과 =====")
    lines.append("")

    lines.append("[1] 학생 요약")
    lines.append(f"- 학과: {student_summary.get('department')}")
    lines.append(f"- 학년: {student_summary.get('student_year')}")
    lines.append(f"- GPA: {student_summary.get('gpa')}")
    lines.append(f"- AI 분석 신뢰도: {student_summary.get('extraction_confidence')}")
    lines.append("")

    lines.append("[2] 교육과정 기준")
    lines.append(f"- 기준 PDF: {curriculum_source.get('source_pdf')}")
    lines.append(f"- 마지막 동기화: {curriculum_source.get('last_synced_at')}")
    lines.append("")

    lines.append("[3] 졸업요건 비교")
    lines.append(
        f"- 총 학점: {graduation_analysis.get('current_total_credits')} / "
        f"{graduation_analysis.get('required_total_credits')}"
    )
    lines.append(
        f"- 전공 학점: {graduation_analysis.get('current_major_credits')} / "
        f"{graduation_analysis.get('required_major_credits')}"
    )
    lines.append(
        f"- 교양 학점: {graduation_analysis.get('current_general_credits')} / "
        f"{graduation_analysis.get('required_general_credits')}"
    )
    lines.append(f"- 남은 총 학점: {graduation_analysis.get('remaining_total_credits')}")
    lines.append(f"- 남은 전공 학점: {graduation_analysis.get('remaining_major_credits')}")
    lines.append(f"- 남은 교양 학점: {graduation_analysis.get('remaining_general_credits')}")
    lines.append("")
    lines.append("[4] 미이수 필수 과목")
    missing_required_courses = graduation_analysis.get("missing_required_courses", [])

    if missing_required_courses:
        for course_name in missing_required_courses:
            lines.append(f"- {course_name}")
    else:
        lines.append("- 미이수 필수 과목 없음")

    lines.append("")

    lines.append("[5] 다음 학기 추천 과목")
    for recommendation in course_recommendations:
        lines.append(
            f"- {recommendation.get('course_name')} "
            f"({recommendation.get('category')}, 우선순위: {recommendation.get('priority')})"
        )
        lines.append(f"  이유: {recommendation.get('reason')}")

    lines.append("")

    lines.append("[6] 장학금 전략")
    lines.append(f"- 현재 GPA: {scholarship_strategy.get('current_gpa')}")
    lines.append(f"- 전체 가능성: {scholarship_strategy.get('possibility')}")
    lines.append(f"- 조언: {scholarship_strategy.get('advice')}")

    recommended_scholarships = scholarship_strategy.get("recommended_scholarships", [])

    if recommended_scholarships:
        lines.append("")
        lines.append("- 추천 장학금")

        for scholarship in recommended_scholarships:
            lines.append(f"  · {scholarship.get('name')}")
            lines.append(f"    가능성: {scholarship.get('possibility')}")
            lines.append(f"    이유: {scholarship.get('reason')}")

            requirements_to_check = scholarship.get("requirements_to_check", [])

            if requirements_to_check:
                lines.append("    확인 필요 조건:")

                for requirement in requirements_to_check:
                    lines.append(f"    - {requirement}")

    lines.append("")

    lines.append("[7] 주의사항")
    if warnings:
        for warning in warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("- 특별한 주의사항 없음")

    return "\n".join(lines)
