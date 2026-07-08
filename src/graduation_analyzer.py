def normalize_course_name(course_name: str) -> str:
    if not course_name:
        return ""

    return course_name.replace(" ", "").strip()


def get_completed_course_names(transcript_data: dict) -> set:
    completed_courses = transcript_data.get("completed_courses", [])
    course_names = set()

    for course in completed_courses:
        course_name = course.get("course_name")
        normalized_name = normalize_course_name(course_name)

        if normalized_name:
            course_names.add(normalized_name)

    return course_names

def compare_graduation_requirements(
    transcript_data: dict,
    curriculum_requirements: dict
) -> dict:
    current_total_credits = transcript_data.get("total_credits", 0) or 0
    current_major_credits = transcript_data.get("major_credits", 0) or 0
    current_general_credits = transcript_data.get("general_credits", 0) or 0

    required_total_credits = curriculum_requirements.get("required_total_credits", 0) or 0
    required_major_credits = curriculum_requirements.get("required_major_credits", 0) or 0
    required_general_credits = curriculum_requirements.get("required_general_credits", 0) or 0

    remaining_total_credits = max(required_total_credits - current_total_credits, 0)
    remaining_major_credits = max(required_major_credits - current_major_credits, 0)
    remaining_general_credits = max(required_general_credits - current_general_credits, 0)

    completed_course_names = get_completed_course_names(transcript_data)
    required_courses = curriculum_requirements.get("required_courses", [])

    missing_required_courses = []
    completed_required_courses = []

    for required_course in required_courses:
        normalized_required_course = normalize_course_name(required_course)

        if normalized_required_course in completed_course_names:
            completed_required_courses.append(required_course)
        else:
            missing_required_courses.append(required_course)

    is_graduation_ready = (
        remaining_total_credits == 0
        and remaining_major_credits == 0
        and remaining_general_credits == 0
        and len(missing_required_courses) == 0
    )

    warnings = []

    if not transcript_data.get("department"):
        warnings.append("성적증명서에서 학과 정보를 찾지 못했습니다.")

    if transcript_data.get("extraction_confidence") == "low":
        warnings.append("성적증명서 AI 분석 신뢰도가 낮습니다. 결과 확인이 필요합니다.")

    if not required_courses:
        warnings.append("교육과정에서 필수 과목 목록을 찾지 못했습니다.")

    return {
        "current_total_credits": current_total_credits,
        "current_major_credits": current_major_credits,
        "current_general_credits": current_general_credits,
        "required_total_credits": required_total_credits,
        "required_major_credits": required_major_credits,
        "required_general_credits": required_general_credits,
        "remaining_total_credits": remaining_total_credits,
        "remaining_major_credits": remaining_major_credits,
        "remaining_general_credits": remaining_general_credits,
        "completed_required_courses": completed_required_courses,
        "missing_required_courses": missing_required_courses,
        "is_graduation_ready": is_graduation_ready,
        "warnings": warnings,
    }