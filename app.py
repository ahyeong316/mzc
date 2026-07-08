import os
import time
import html
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

from src.privacy import save_uploaded_file, delete_uploaded_file
from src.guardrails import sanitize_strategy_report, validate_user_request
from src.integration_agent import run_full_pipeline


TEMP_FOLDER = "temp"


def cleanup_temp_folder_once():
    os.makedirs(TEMP_FOLDER, exist_ok=True)

    for filename in os.listdir(TEMP_FOLDER):
        file_path = os.path.join(TEMP_FOLDER, filename)

        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass


def reset_uploaded_pdf_state():
    st.session_state.uploaded_pdf_path = None
    st.session_state.uploaded_pdf_name = None
    st.session_state.uploaded_pdf_size = None
    st.session_state.uploader_key += 1


def delete_current_uploaded_pdf():
    delete_target = st.session_state.uploaded_pdf_path

    deleted = False

    if delete_target is not None:
        deleted = delete_uploaded_file(delete_target)

    reset_uploaded_pdf_state()

    return deleted


def _safe(value):
    if value is None:
        return "-"
    return html.escape(str(value))


def _as_list(value):
    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]


def _course_name(course):
    if isinstance(course, dict):
        return (
            course.get("course_name")
            or course.get("name")
            or course.get("title")
            or str(course)
        )

    return str(course)


def _first_value(*sources, keys=None, default=None):
    """여러 dict에서 먼저 발견되는 유효한 값을 반환합니다."""
    keys = keys or []

    for source in sources:
        if not isinstance(source, dict):
            continue

        for key in keys:
            value = source.get(key)

            if value not in (None, "", [], {}):
                return value

    return default


def _nested_dict(source, keys):
    """여러 후보 key 중 dict 값을 찾아 반환합니다."""
    if not isinstance(source, dict):
        return {}

    for key in keys:
        value = source.get(key)

        if isinstance(value, dict):
            return value

    return {}


def _extract_courses(source):
    """성적 분석 결과 구조가 달라도 이수 과목 목록을 최대한 찾아냅니다."""
    if not isinstance(source, dict):
        return []

    direct_courses = _first_value(
        source,
        keys=[
            "completed_courses",
            "courses",
            "course_history",
            "subjects",
            "major_subjects",
            "completed_major_subjects",
            "이수과목",
            "수강과목",
            "전공 이수 과목",
        ],
        default=[]
    )

    if direct_courses:
        return _as_list(direct_courses)

    semester_courses = []

    for semester_key in ["semesters", "semester_records", "terms", "학기별성적"]:
        semesters = source.get(semester_key)

        if isinstance(semesters, list):
            for semester in semesters:
                if isinstance(semester, dict):
                    courses = _first_value(
                        semester,
                        keys=["courses", "subjects", "completed_courses", "수강과목", "이수과목"],
                        default=[]
                    )
                    semester_courses.extend(_as_list(courses))

    return semester_courses


def _sum_credits_from_courses(courses):
    total = 0

    for course in _as_list(courses):
        if not isinstance(course, dict):
            continue

        credit = (
            course.get("credit")
            or course.get("credits")
            or course.get("학점")
            or course.get("이수학점")
            or 0
        )

        try:
            total += float(credit)
        except Exception:
            pass

    if total == 0:
        return 0

    return int(total) if total.is_integer() else total


def call_full_pipeline_safely(pdf_path, department=None, user_request=None):
    """
    integration_agent.py의 run_full_pipeline 인자 구성이 달라도 최대한 실행되게 합니다.
    department를 받는 버전이면 학과까지 전달하고, 아니면 pdf_path만 전달합니다.
    """
    try:
        return run_full_pipeline(
            pdf_path=pdf_path,
            department=department,
            user_request=user_request,
        )
    except TypeError:
        try:
            return run_full_pipeline(
                pdf_path=pdf_path,
                department=department,
            )
        except TypeError:
            return run_full_pipeline(
                pdf_path=pdf_path
            )


def render_design_system():
    st.markdown(
        """
<style>
@import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css");

:root {
    --blue: #3182F6;
    --blue-hover: #1B64DA;
    --blue-light: #EEF4FF;

    --ink: #191F28;
    --body: #333D4B;
    --muted: #6B7684;
    --sub: #8B95A1;
    --faint: #B0B8C1;

    --line: #F4F5F7;
    --border-soft: #EDEFF2;
    --border: #E5E8EB;

    --bg: #F7F8FA;
    --card: #FFFFFF;

    --success: #008767;
    --success-bg: #E5F9F2;
    --error: #D32F3A;
    --error-bg: #FEECEE;
    --warn: #B25E00;
    --warn-bg: #FFF4E5;

    --r-card: 18px;
    --r-btn: 12px;
    --r-input: 11px;

    --shadow-card: 0 1px 2px rgba(0,0,0,0.03);
    --shadow-btn: 0 1px 2px rgba(49,130,246,0.30);
}

html, body, [class*="css"] {
    font-family: Pretendard, -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Segoe UI", sans-serif;
}

.stApp {
    background: var(--bg);
    color: var(--body);
}

.block-container {
    max-width: 1180px;
    padding: 40px 44px 90px 44px;
}

@media (max-width: 860px) {
    .block-container {
        padding: 28px 20px 80px 20px;
    }

    .app-rail {
        display: none;
    }
}

.app-rail {
    position: fixed;
    top: 0;
    left: 0;
    width: 86px;
    height: 100vh;
    z-index: 999;
    background: var(--card);
    border-right: 1px solid var(--line);
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 14px 8px;
    gap: 4px;
}

.rail-logo {
    width: 34px;
    height: 34px;
    border-radius: 10px;
    background: linear-gradient(135deg, var(--blue), #6BA6F9);
    color: #FFFFFF;
    display: grid;
    place-items: center;
    font-size: 15px;
    font-weight: 800;
    margin-bottom: 14px;
}

.rail-item {
    width: 70px;
    min-height: 64px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 5px;
    cursor: default;
}

.rail-box {
    width: 48px;
    height: 42px;
    border-radius: 13px;
    display: grid;
    place-items: center;
    color: var(--faint);
}

.rail-item.active .rail-box {
    background: var(--blue-light);
    color: var(--blue);
}

.rail-icon {
    position: relative;
    display: block;
    width: 22px;
    height: 22px;
    color: currentColor;
}

.icon-doc::before {
    content: "";
    position: absolute;
    left: 5px;
    top: 2px;
    width: 12px;
    height: 17px;
    border: 2px solid currentColor;
    border-radius: 3px;
}

.icon-doc::after {
    content: "";
    position: absolute;
    left: 8px;
    top: 11px;
    width: 8px;
    height: 2px;
    background: currentColor;
    box-shadow: 0 4px 0 currentColor;
    border-radius: 2px;
}

.icon-chart::before {
    content: "";
    position: absolute;
    left: 3px;
    bottom: 3px;
    width: 16px;
    height: 16px;
    border-left: 2px solid currentColor;
    border-bottom: 2px solid currentColor;
}

.icon-chart::after {
    content: "";
    position: absolute;
    left: 7px;
    bottom: 5px;
    width: 3px;
    height: 8px;
    background: currentColor;
    box-shadow: 5px -4px 0 currentColor, 10px -8px 0 currentColor;
    border-radius: 2px;
}

.icon-shield::before {
    content: "";
    position: absolute;
    left: 4px;
    top: 2px;
    width: 14px;
    height: 17px;
    border: 2px solid currentColor;
    border-radius: 8px 8px 10px 10px;
}

.icon-shield::after {
    content: "";
    position: absolute;
    left: 8px;
    top: 9px;
    width: 7px;
    height: 4px;
    border-left: 2px solid currentColor;
    border-bottom: 2px solid currentColor;
    transform: rotate(-45deg);
}

.rail-item span {
    font-size: 11px;
    font-weight: 600;
    color: var(--faint);
    letter-spacing: -0.3px;
}

.rail-item.active span {
    color: var(--blue);
    font-weight: 800;
}

.page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 18px;
    margin-bottom: 26px;
}

.page-title {
    color: var(--ink);
    font-size: 23px;
    font-weight: 800;
    letter-spacing: -0.6px;
    margin: 0;
}

.page-desc {
    color: var(--sub);
    font-size: 14px;
    margin-top: 7px;
    line-height: 1.55;
}

.header-actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 8px;
    padding-top: 2px;
}

.app-card {
    background: var(--card);
    border: 1px solid var(--border-soft);
    border-radius: var(--r-card);
    box-shadow: var(--shadow-card);
    padding: 22px;
    margin-bottom: 16px;
}

.card-title-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin-bottom: 14px;
}

.card-title {
    color: var(--ink);
    font-size: 16px;
    font-weight: 800;
    letter-spacing: -0.3px;
    margin: 0;
}

.card-desc {
    color: var(--sub);
    font-size: 13px;
    margin: 3px 0 0 0;
}

.pill {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 700;
    line-height: 1;
    white-space: nowrap;
}

.pill-info {
    background: var(--blue-light);
    color: var(--blue);
}

.pill-success {
    background: var(--success-bg);
    color: var(--success);
}

.pill-warn {
    background: var(--warn-bg);
    color: var(--warn);
}

.pill-error {
    background: var(--error-bg);
    color: var(--error);
}

.pill-muted {
    background: #F2F4F6;
    color: var(--muted);
}

.kpi-card {
    background: var(--card);
    border: 1px solid var(--border-soft);
    border-radius: var(--r-card);
    box-shadow: var(--shadow-card);
    padding: 18px;
    min-height: 110px;
}

.kpi-label {
    color: var(--muted);
    font-size: 12px;
    font-weight: 700;
}

.kpi-value {
    color: var(--ink);
    font-size: 28px;
    font-weight: 800;
    letter-spacing: -0.4px;
    margin-top: 8px;
    font-variant-numeric: tabular-nums;
}

.kpi-unit {
    color: var(--sub);
    font-size: 13px;
    font-weight: 700;
    margin-left: 2px;
}

.list-row {
    padding: 10px 0;
    border-bottom: 1px solid var(--line);
    color: var(--body);
    font-size: 14px;
}

.list-row:last-child {
    border-bottom: none;
}

.course-title {
    color: var(--ink);
    font-size: 14px;
    font-weight: 800;
}

.course-meta {
    color: var(--sub);
    font-size: 12.5px;
    margin-top: 4px;
}

.notice-card {
    background: var(--card);
    border: 1px solid var(--border-soft);
    border-radius: var(--r-card);
    box-shadow: var(--shadow-card);
    padding: 18px 20px;
}

.notice-title {
    color: var(--ink);
    font-size: 15px;
    font-weight: 800;
    margin-bottom: 6px;
}

.notice-text {
    color: var(--muted);
    font-size: 13px;
    line-height: 1.55;
}

.tnum {
    font-variant-numeric: tabular-nums;
}

div[data-testid="stFileUploader"] section {
    border-radius: 14px;
    border-color: var(--border);
    background: #FFFFFF;
}

div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea {
    border-radius: var(--r-input);
    border-color: var(--border);
    color: var(--ink);
}

div[data-testid="stTextInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus {
    border-color: var(--blue);
    box-shadow: 0 0 0 1px var(--blue);
}

.stButton > button {
    min-height: 44px;
    border-radius: var(--r-btn);
    font-weight: 800;
    border: 1px solid var(--border);
}

.stButton > button[kind="primary"] {
    background: var(--blue);
    border-color: var(--blue);
    box-shadow: var(--shadow-btn);
}

.stButton > button[kind="primary"]:hover {
    background: var(--blue-hover);
    border-color: var(--blue-hover);
}

div[data-testid="stAlert"] {
    border-radius: 14px;
}

hr {
    border-color: var(--line);
}
/* ===== SCNU 86px Safe Streamlit Rail ===== */

section[data-testid="stSidebar"] {
    width: 86px !important;
    min-width: 86px !important;
    max-width: 86px !important;
    background: var(--card) !important;
    border-right: 1px solid var(--line) !important;
}

section[data-testid="stSidebar"] > div:first-child {
    width: 86px !important;
    padding: 14px 8px !important;
    overflow: hidden !important;
}

section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
    text-align: center;
}

section[data-testid="stSidebar"] h2 {
    width: 34px;
    height: 34px;
    border-radius: 10px;
    margin: 0 auto 14px auto;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, var(--blue), #6BA6F9);
    color: #FFFFFF !important;
    font-size: 15px !important;
    font-weight: 900 !important;
}

section[data-testid="stSidebar"] .stButton {
    width: 70px !important;
    margin: 0 auto 8px auto !important;
}

section[data-testid="stSidebar"] .stButton > button {
    width: 70px !important;
    min-height: 64px !important;
    height: 64px !important;
    border-radius: 14px !important;
    border: 0 !important;
    background: transparent !important;
    color: var(--faint) !important;
    font-size: 11px !important;
    font-weight: 800 !important;
    letter-spacing: -0.3px !important;
    box-shadow: none !important;
    padding-top: 28px !important;
    position: relative !important;
}

section[data-testid="stSidebar"] .stButton:first-of-type > button {
    background: var(--blue-light) !important;
    color: var(--blue) !important;
}

section[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--blue-light) !important;
    color: var(--blue) !important;
}

section[data-testid="stSidebar"] .stButton > button::before {
    content: "";
    position: absolute;
    top: 12px;
    left: 50%;
    width: 18px;
    height: 18px;
    transform: translateX(-50%);
    border: 2px solid currentColor;
    border-radius: 5px;
}
/* ===== Hide Sidebar Completely ===== */

section[data-testid="stSidebar"] {
    display: none !important;
    width: 0 !important;
    min-width: 0 !important;
    max-width: 0 !important;
}

section[data-testid="stSidebarCollapsedControl"] {
    display: none !important;
}

div[data-testid="collapsedControl"] {
    display: none !important;
}

.block-container {
    max-width: 1180px !important;
    padding-left: 44px !important;
    padding-right: 44px !important;
}
</style>
""",
        unsafe_allow_html=True
    )


def render_sidebar():
    pass

def render_page_header():
    uploaded_state = "업로드 완료" if st.session_state.uploaded_pdf_path else "PDF 대기"
    uploaded_class = "pill-success" if st.session_state.uploaded_pdf_path else "pill-muted"

    st.markdown(
        '<div style="display:inline-flex;align-items:center;gap:8px;padding:6px 10px;border-radius:999px;background:#EEF4FF;color:#3182F6;font-size:12px;font-weight:800;margin-bottom:14px;">SCNU AI Strategy Agent</div>',
        unsafe_allow_html=True
    )

    header_left, header_right = st.columns([0.72, 0.28])

    with header_left:
        st.markdown(
            '<h1 class="page-title">순천대학교 전략 큐레이터</h1>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="page-desc">학생의 성적증명서를 업로드하면<br>AI가 졸업 전략과 다음 학기 수강계획을 추천합니다.</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:16px;"><span class="pill pill-info">PDF 성적분석</span><span class="pill pill-muted">교육과정 비교</span><span class="pill pill-success">개인정보 자동삭제</span></div>',
            unsafe_allow_html=True
        )

    with header_right:
        st.markdown(
            f'<div style="display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap;padding-top:8px;"><span class="pill {uploaded_class}">{uploaded_state}</span></div>',
            unsafe_allow_html=True
        )

    st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)

    def step_card(step, title):
        return (
            '<div style="background:#FFFFFF;border:1px solid #EDEFF2;border-radius:16px;'
            'padding:16px;box-shadow:0 1px 2px rgba(0,0,0,0.03);">'
            f'<div style="font-size:12px;color:#6B7684;font-weight:700;">STEP {step}</div>'
            f'<div style="font-size:15px;color:#191F28;font-weight:900;margin-top:6px;">{title}</div>'
            '</div>'
        )

    step1, step2, step3, step4 = st.columns(4)

    with step1:
        st.markdown(step_card("01", "PDF 업로드"), unsafe_allow_html=True)

    with step2:
        st.markdown(step_card("02", "성적 분석"), unsafe_allow_html=True)

    with step3:
        st.markdown(step_card("03", "졸업요건 비교"), unsafe_allow_html=True)

    with step4:
        st.markdown(step_card("04", "전략 추천"), unsafe_allow_html=True)

    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)

def open_card(title, description=None, pill=None, pill_class="pill-info"):
    pill_html = ""

    if pill:
        pill_html = f'<span class="pill {pill_class}">{_safe(pill)}</span>'

    desc_html = ""

    if description:
        desc_html = f'<p class="card-desc">{_safe(description)}</p>'

    st.markdown(
        f"""
<div class="app-card">
    <div class="card-title-row">
        <div>
            <h2 class="card-title">{_safe(title)}</h2>
            {desc_html}
        </div>
        {pill_html}
    </div>
""",
        unsafe_allow_html=True
    )


def close_card():
    st.markdown("</div>", unsafe_allow_html=True)


def render_kpi(label, value, unit=""):
    st.markdown(
        f"""
<div class="kpi-card">
    <div class="kpi-label">{_safe(label)}</div>
    <div class="kpi-value tnum">{_safe(value)}<span class="kpi-unit">{_safe(unit)}</span></div>
</div>
""",
        unsafe_allow_html=True
    )


def render_simple_list(items, empty_message):
    items = _as_list(items)

    if not items:
        st.info(empty_message)
        return

    for item in items:
        st.markdown(
            f"""
<div class="list-row">{_safe(_course_name(item))}</div>
""",
            unsafe_allow_html=True
        )


def show_integrated_result(report):
    st.markdown('<div id="result-area"></div>', unsafe_allow_html=True)

    if not isinstance(report, dict):
        open_card("분석 결과", "AI 분석 결과를 표시합니다.", "완료", "pill-success")
        st.write(report)
        close_card()
        return

    # run_full_pipeline 결과가 아래처럼 중첩되어 와도 읽을 수 있게 정규화합니다.
    # 예: {"transcript_data": {...}, "strategy_report": {...}}
    transcript_data = _nested_dict(
        report,
        [
            "transcript_data",
            "transcript",
            "role1_result",
            "role1",
            "student_record",
            "student_data",
        ]
    )

    final_report = _nested_dict(
        report,
        [
            "strategy_report",
            "final_report",
            "analysis_result",
            "result",
            "role3_result",
            "role3",
        ]
    )

    if not final_report:
        final_report = report

    student_summary = _nested_dict(
        final_report,
        ["student_summary", "summary", "student", "학생요약"]
    ) or _nested_dict(
        transcript_data,
        ["student_summary", "summary", "student", "학생요약"]
    )

    graduation_status = _nested_dict(
        final_report,
        ["graduation_status", "graduation", "graduation_analysis", "졸업요건", "졸업상태"]
    )

    completed_courses = (
        _extract_courses(final_report)
        or _extract_courses(student_summary)
        or _extract_courses(transcript_data)
        or _extract_courses(report)
    )

    earned_credit = _first_value(
        final_report,
        report,
        student_summary,
        transcript_data,
        graduation_status,
        keys=[
            "earned_credit",
            "earned_credits",
            "total_credits",
            "total_credit",
            "completed_credits",
            "acquired_credits",
            "current_total_credits",
            "total_earned_credits",
            "총취득학점",
            "총 취득학점",
            "취득학점",
            "이수학점",
        ],
        default=None
    )

    if earned_credit is None:
        earned_credit = _sum_credits_from_courses(completed_courses)

    gpa = _first_value(
        final_report,
        report,
        student_summary,
        transcript_data,
        keys=[
            "gpa",
            "average_gpa",
            "grade_point_average",
            "평균평점",
            "평점평균",
            "전체평점",
            "평점",
        ],
        default="-"
    )

    remaining_credit = _first_value(
        final_report,
        report,
        graduation_status,
        keys=[
            "remaining_credit",
            "remaining_credits",
            "remaining_total_credits",
            "부족학점",
            "남은학점",
            "남은 졸업학점",
        ],
        default="-"
    )

    major_subjects = _first_value(
        final_report,
        report,
        student_summary,
        transcript_data,
        keys=[
            "major_subjects",
            "completed_major_subjects",
            "completed_courses",
            "courses",
            "course_history",
            "subjects",
            "전공 이수 과목",
            "이수과목",
            "수강과목",
        ],
        default=completed_courses
    )

    missing_courses = _first_value(
        final_report,
        report,
        graduation_status,
        keys=[
            "remaining_subjects",
            "missing_required_courses",
            "missing_courses",
            "required_missing_courses",
            "미이수과목",
            "미이수 필수 과목",
            "남은과목",
        ],
        default=[]
    )

    recommended_courses = _first_value(
        final_report,
        report,
        keys=[
            "recommend_subjects",
            "recommended_courses",
            "recommend_courses",
            "course_recommendations",
            "next_semester_courses",
            "추천과목",
            "다음학기추천과목",
        ],
        default=[]
    )

    scholarship_analysis = _first_value(
        final_report,
        report,
        keys=[
            "scholarship",
            "scholarship_analysis",
            "scholarship_strategy",
            "장학금전략",
            "장학분석",
        ],
        default={}
    )

    warnings = _first_value(
        final_report,
        report,
        keys=["warnings", "warning", "주의사항"],
        default=[]
    )

    open_card("현재 이수 현황", "성적증명서에서 추출한 학점과 평점 정보를 요약합니다.", "요약", "pill-info")

    col1, col2, col3 = st.columns(3)

    with col1:
        render_kpi("총 취득학점", earned_credit, "학점")

    with col2:
        render_kpi("평균평점", gpa, "")

    with col3:
        render_kpi("남은 졸업학점", remaining_credit, "학점")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="card-title">전공 이수 과목</div>', unsafe_allow_html=True)
    render_simple_list(major_subjects, "전공 이수 과목 정보가 없습니다.")

    close_card()

    open_card("졸업요건 비교", "현재 이수 현황과 교육과정 기준을 비교합니다.", "분석", "pill-info")

    if graduation_status:
        total_current = graduation_status.get("current_total_credits", earned_credit)
        total_required = graduation_status.get("required_total_credits", "-")
        major_current = graduation_status.get("current_major_credits", "-")
        major_required = graduation_status.get("required_major_credits", "-")
        general_current = graduation_status.get("current_general_credits", "-")
        general_required = graduation_status.get("required_general_credits", "-")

        st.markdown(
            f"""
<div class="list-row tnum">총 학점: {_safe(total_current)} / {_safe(total_required)}</div>
<div class="list-row tnum">전공 학점: {_safe(major_current)} / {_safe(major_required)}</div>
<div class="list-row tnum">교양 학점: {_safe(general_current)} / {_safe(general_required)}</div>
""",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
<div class="list-row tnum">남은 졸업학점: {_safe(remaining_credit)}</div>
""",
            unsafe_allow_html=True
        )

    close_card()

    open_card("미이수 필수 과목", "졸업까지 남은 필수 과목을 표시합니다.", "필수", "pill-warn")
    render_simple_list(missing_courses, "미이수 필수 과목 정보가 없습니다.")
    close_card()

    open_card("다음 학기 추천 과목", "졸업요건과 이수 현황을 기준으로 추천 과목을 제시합니다.", "추천", "pill-success")

    recommended_courses = _as_list(recommended_courses)

    if not recommended_courses:
        st.info("추천 과목 정보가 없습니다.")
    else:
        for course in recommended_courses:
            if isinstance(course, dict):
                name = course.get("course_name") or course.get("name") or "추천 과목"
                category = course.get("category", "")
                priority = course.get("priority", "")
                reason = course.get("reason", "")

                meta_parts = []

                if category:
                    meta_parts.append(category)

                if priority:
                    meta_parts.append(f"우선순위: {priority}")

                meta = " · ".join(meta_parts)

                st.markdown(
                    f"""
<div class="list-row">
    <div class="course-title">{_safe(name)}</div>
    <div class="course-meta">{_safe(meta)}</div>
    <div class="course-meta">{_safe(reason)}</div>
</div>
""",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"""
<div class="list-row">{_safe(course)}</div>
""",
                    unsafe_allow_html=True
                )

    close_card()

    open_card("장학금 전략", "성적 정보를 바탕으로 장학금 가능성과 전략을 안내합니다.", "장학", "pill-info")

    if isinstance(scholarship_analysis, dict):
        possibility = (
            scholarship_analysis.get("overall_possibility")
            or scholarship_analysis.get("possibility")
            or scholarship_analysis.get("status")
        )

        advice = (
            scholarship_analysis.get("advice")
            or scholarship_analysis.get("message")
            or scholarship_analysis.get("summary")
        )

        current_gpa = scholarship_analysis.get("current_gpa") or gpa

        st.markdown(
            f"""
<div class="list-row tnum">현재 GPA: {_safe(current_gpa)}</div>
<div class="list-row">전체 가능성: {_safe(possibility)}</div>
<div class="list-row">조언: {_safe(advice)}</div>
""",
            unsafe_allow_html=True
        )

        recommended_scholarships = scholarship_analysis.get("recommended_scholarships", [])

        if recommended_scholarships:
            st.markdown('<div class="card-title" style="margin-top:14px;">추천 장학금</div>', unsafe_allow_html=True)

            for item in recommended_scholarships:
                if isinstance(item, dict):
                    name = item.get("name", "장학금")
                    item_possibility = item.get("possibility", "-")
                    reason = item.get("reason", "")

                    st.markdown(
                        f"""
<div class="list-row">
    <div class="course-title">{_safe(name)}</div>
    <div class="course-meta">가능성: {_safe(item_possibility)}</div>
    <div class="course-meta">{_safe(reason)}</div>
</div>
""",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(f'<div class="list-row">{_safe(item)}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="list-row">{_safe(scholarship_analysis)}</div>', unsafe_allow_html=True)

    close_card()

    if warnings:
        open_card("주의사항", "분석 과정에서 확인이 필요한 내용을 표시합니다.", "확인 필요", "pill-warn")

        for warning in _as_list(warnings):
            st.markdown(f'<div class="list-row">{_safe(warning)}</div>', unsafe_allow_html=True)

        close_card()

    open_card("원본 분석 JSON 보기", "역할별 통합 파이프라인이 반환한 원본 결과입니다.", "JSON", "pill-muted")

    with st.expander("원본 분석 JSON 보기"):
        st.json(report)

    close_card()


st.set_page_config(
    page_title="순천대학교 전략 큐레이터",
    page_icon="🎓",
    layout="wide"
)


render_design_system()


if "temp_cleanup_done" not in st.session_state:
    cleanup_temp_folder_once()
    st.session_state.temp_cleanup_done = True

if "uploaded_pdf_path" not in st.session_state:
    st.session_state.uploaded_pdf_path = None

if "uploaded_pdf_name" not in st.session_state:
    st.session_state.uploaded_pdf_name = None

if "uploaded_pdf_size" not in st.session_state:
    st.session_state.uploaded_pdf_size = None

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

if "strategy_report" not in st.session_state:
    st.session_state.strategy_report = None

if "privacy_notice_message" not in st.session_state:
    st.session_state.privacy_notice_message = None

if "guardrail_error_message" not in st.session_state:
    st.session_state.guardrail_error_message = None


render_sidebar()
render_page_header()

department = ""
user_request = ""
analyze = False

st.markdown('<div id="input-area"></div>', unsafe_allow_html=True)


open_card(
    title="성적증명서 PDF 업로드",
    description="학생 본인의 성적증명서 PDF를 업로드하면 분석 과정에서만 임시 저장됩니다.",
    pill="필수",
    pill_class="pill-info"
)

uploaded_file = st.file_uploader(
    "성적증명서 PDF 업로드",
    type=["pdf"],
    key=f"pdf_uploader_{st.session_state.uploader_key}"
)

if uploaded_file is not None:

    is_new_file = (
        st.session_state.uploaded_pdf_name != uploaded_file.name
        or st.session_state.uploaded_pdf_size != uploaded_file.size
        or st.session_state.uploaded_pdf_path is None
    )

    if is_new_file:

        if st.session_state.uploaded_pdf_path is not None:
            delete_uploaded_file(st.session_state.uploaded_pdf_path)

        saved_path = save_uploaded_file(uploaded_file)

        st.session_state.uploaded_pdf_path = saved_path
        st.session_state.uploaded_pdf_name = uploaded_file.name
        st.session_state.uploaded_pdf_size = uploaded_file.size
        st.session_state.strategy_report = None
        st.session_state.privacy_notice_message = None
        st.session_state.guardrail_error_message = None

    st.markdown(
        f"""
<div class="list-row">
    <span class="pill pill-success">업로드 완료</span>
    <span style="margin-left:8px;">PDF가 정상적으로 업로드되었습니다.</span>
</div>
<div class="list-row">파일 이름 : {_safe(uploaded_file.name)}</div>
""",
        unsafe_allow_html=True
    )

close_card()


open_card(
    title="학생 기본 정보",
    description="교육과정 편람과 졸업요건 비교에 사용할 학과 정보를 입력합니다.",
    pill="입력",
    pill_class="pill-muted"
)

department = st.text_input(
    "학과를 입력하세요",
    placeholder="예) 컴퓨터공학과"
)

if department:
    st.markdown(
        f"""
<div class="list-row">학과 : {_safe(department)}</div>
""",
        unsafe_allow_html=True
    )

close_card()


open_card(
    title="본인 성적증명서 기준 추가 요청",
    description="분석 결과에서 더 자세히 보고 싶은 내용을 입력할 수 있습니다.",
    pill="선택",
    pill_class="pill-muted"
)

user_request = st.text_area(
    "본인 성적증명서 기준 추가 요청",
    placeholder="예) 제 성적증명서를 기준으로 졸업까지 남은 과목과 다음 학기 추천 과목을 알려줘.",
    height=100
)

if user_request:
    st.markdown(
        """
<div class="list-row">
    <span class="pill pill-info">입력됨</span>
    <span style="margin-left:8px;">추가 요청이 입력되었습니다.</span>
</div>
""",
        unsafe_allow_html=True
    )

close_card()


open_card(
    title="AI 전략 분석 실행",
    description="성적증명서 PDF 분석, 교육과정 검색, 졸업요건 비교, 추천 수강 과목 및 장학금 전략 생성을 시작합니다.",
    pill="실행",
    pill_class="pill-info"
)

analyze = st.button("분석 시작", type="primary", use_container_width=True)

close_card()


if analyze:

    st.session_state.guardrail_error_message = None
    st.session_state.privacy_notice_message = None
    st.session_state.strategy_report = None

    validation = validate_user_request(user_request)

    if st.session_state.uploaded_pdf_path is None:
        st.error("성적증명서 PDF를 먼저 업로드해주세요.")

    elif not department:
        st.error("학과를 입력해주세요.")

    elif not validation["allowed"]:

        delete_current_uploaded_pdf()

        st.session_state.strategy_report = None
        st.session_state.guardrail_error_message = validation["message"]
        st.session_state.privacy_notice_message = "차단된 요청으로 인해 업로드된 PDF는 자동으로 삭제되었습니다."

        st.rerun()

    else:
        open_card(
            title="분석 진행 중",
            description="성적증명서와 교육과정 데이터를 기반으로 전략을 생성하고 있습니다.",
            pill="진행 중",
            pill_class="pill-info"
        )

        progress = st.progress(0)
        status = st.empty()

        try:
            uploaded_pdf_path = st.session_state.uploaded_pdf_path

            if not os.getenv("GOOGLE_API_KEY"):
                st.warning("GOOGLE_API_KEY가 설정되어 있지 않아 실제 Gemini 분석이 제한될 수 있습니다.")

            status.info("성적증명서 PDF를 Gemini AI가 분석하고 있습니다.")
            progress.progress(20)
            time.sleep(0.5)

            status.info("교육과정 편람과 졸업요건을 검색하고 있습니다.")
            progress.progress(45)
            time.sleep(0.5)

            status.info("졸업요건, 추천 과목, 장학 전략을 생성하고 있습니다.")
            progress.progress(70)

            strategy_report = call_full_pipeline_safely(
                pdf_path=uploaded_pdf_path,
                department=department.strip(),
                user_request=user_request,
            )

            status.info("개인정보를 마스킹하고 결과를 정리하고 있습니다.")
            progress.progress(90)

            safe_strategy_report = sanitize_strategy_report(strategy_report)

            st.session_state.strategy_report = safe_strategy_report
            st.session_state.privacy_notice_message = "분석 완료 후 업로드된 PDF는 자동으로 삭제되었습니다."

            progress.progress(100)
            status.success("분석 완료")

        except Exception as error:
            st.session_state.strategy_report = None
            st.session_state.guardrail_error_message = "분석 중 오류가 발생했습니다. Gemini API 또는 역할별 함수 연결 상태를 확인해주세요."
            print(error)

        finally:
            close_card()
            delete_current_uploaded_pdf()
            st.rerun()


if st.session_state.guardrail_error_message is not None:
    st.error(st.session_state.guardrail_error_message)


if st.session_state.strategy_report is not None:
    show_integrated_result(st.session_state.strategy_report)


if st.session_state.privacy_notice_message is not None:
    st.success(st.session_state.privacy_notice_message)


st.markdown('<div id="privacy-area"></div>', unsafe_allow_html=True)

open_card(
    title="개인정보 보호",
    description="업로드된 PDF는 분석 과정에서만 임시 저장되며, 분석 완료 또는 금지 요청 차단 시 자동 삭제됩니다.",
    pill="보안",
    pill_class="pill-success"
)

st.markdown(
    """
<div class="notice-text">
업로드된 PDF는 분석 과정에서만 임시 저장되며, 분석 완료 또는 금지 요청 차단 시 자동 삭제됩니다.
</div>
""",
    unsafe_allow_html=True
)

delete_button = st.button("PDF 수동 삭제", type="secondary")

if delete_button:

    if st.session_state.uploaded_pdf_path is not None:

        delete_current_uploaded_pdf()

        st.session_state.privacy_notice_message = "PDF가 안전하게 삭제되었습니다."

        st.rerun()

    else:
        st.warning("현재 임시 저장된 PDF가 없습니다.")

close_card()
