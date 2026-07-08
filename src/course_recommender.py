def recommend_next_courses(
    transcript_data: dict,
    curriculum_requirements: dict,
    graduation_analysis: dict,
    max_courses: int = 6
) -> list[dict]:
    recommendations = []

    missing_required_courses = graduation_analysis.get("missing_required_courses", [])
    remaining_major_credits = graduation_analysis.get("remaining_major_credits", 0)
    remaining_general_credits = graduation_analysis.get("remaining_general_credits", 0)

    for course_name in missing_required_courses:
        recommendations.append({
            "course_name": course_name,
            "category": "전공필수",
            "priority": "높음",
            "reason": "졸업 필수 과목이지만 아직 이수하지 않았기 때문에 우선 수강을 추천합니다."
        })

        if len(recommendations) >= max_courses:
            return recommendations

    if remaining_major_credits > 0 and len(recommendations) < max_courses:
        recommendations.append({
            "course_name": "전공선택 과목",
            "category": "전공선택",
            "priority": "중간",
            "reason": f"전공 학점이 {remaining_major_credits}학점 부족하므로 전공선택 과목 수강이 필요합니다."
        })

    if remaining_general_credits > 0 and len(recommendations) < max_courses:
        recommendations.append({
            "course_name": "교양 과목",
            "category": "교양",
            "priority": "중간",
            "reason": f"교양 학점이 {remaining_general_credits}학점 부족하므로 교양 과목 수강이 필요합니다."
        })

    if not recommendations:
        recommendations.append({
            "course_name": "추가 확인 필요",
            "category": "확인 필요",
            "priority": "낮음",
            "reason": "현재 데이터 기준으로 즉시 추천할 과목이 없습니다. 교육과정표와 학과 상담을 통해 확인이 필요합니다."
        })

    return recommendations[:max_courses]