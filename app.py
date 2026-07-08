import os
import time
import streamlit as st

from src.privacy import save_uploaded_file, delete_uploaded_file
from src.display import show_result
from src.guardrails import sanitize_strategy_report, validate_user_request
from src.integration_agent import (
    run_role1,
    run_role2_curriculum,
    run_role2_scholarship_policy,
    run_role3,
)


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


st.set_page_config(
    page_title="순천대학교 전략 큐레이터",
    page_icon="🎓",
    layout="wide"
)


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


st.title("🎓 순천대학교 전략 큐레이터")

st.write("학생의 성적증명서를 업로드하면")
st.write("AI가 졸업 전략과 다음 학기 수강계획을 추천합니다.")

st.divider()


uploaded_file = st.file_uploader(
    "📄 성적증명서 PDF 업로드",
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

    st.success("✅ PDF가 정상적으로 업로드되었습니다.")
    st.write(f"📄 파일 이름 : {uploaded_file.name}")


st.divider()


department = st.text_input(
    "학과를 입력하세요",
    placeholder="예) 컴퓨터공학과"
)

if department:
    st.write(f"🏫 학과 : {department}")


user_request = st.text_area(
    "본인 성적증명서 기준 추가 요청",
    placeholder="예) 제 성적증명서를 기준으로 졸업까지 남은 과목과 다음 학기 추천 과목을 알려줘.",
    height=100
)

if user_request:
    st.caption("📝 추가 요청이 입력되었습니다.")


st.divider()


analyze = st.button("🚀 분석 시작")


if analyze:

    st.session_state.guardrail_error_message = None
    st.session_state.privacy_notice_message = None

    validation = validate_user_request(user_request)

    if st.session_state.uploaded_pdf_path is None:
        st.error("성적증명서 PDF를 먼저 업로드해주세요.")

    elif not department:
        st.error("학과를 입력해주세요.")

    elif not validation["allowed"]:

        delete_current_uploaded_pdf()

        st.session_state.strategy_report = None
        st.session_state.guardrail_error_message = validation["message"]
        st.session_state.privacy_notice_message = "🔒 차단된 요청으로 인해 업로드된 PDF는 자동으로 삭제되었습니다."

        st.rerun()

    else:
        progress = st.progress(0)
        status = st.empty()

        # ── 역할 1: 성적증명서 PDF AI 분석 ──
        status.info("📄 성적증명서 PDF를 AI 에이전트가 분석하고 있습니다...")
        progress.progress(20)

        transcript_data = run_role1(st.session_state.uploaded_pdf_path)

        # ── 역할 2: 교육과정 검색 ──
        status.info("📚 최신 교육과정 편람을 검색하고 있습니다...")
        progress.progress(40)

        curriculum_requirements = run_role2_curriculum(
            transcript_data,
            department=department,
        )

        # ── 역할 2: 장학 제도 ──
        status.info("💰 장학 제도 정보를 불러오고 있습니다...")
        progress.progress(60)

        scholarship_policy = run_role2_scholarship_policy()

        # ── 역할 3: 전략 분석 ──
        status.info("🎓 졸업요건 비교와 수강/장학 전략을 분석하고 있습니다...")
        progress.progress(80)

        strategy_report = run_role3(
            transcript_data=transcript_data,
            curriculum_requirements=curriculum_requirements,
            scholarship_policy=scholarship_policy,
        )

        progress.progress(100)
        status.success("✅ 분석 완료!")

        safe_strategy_report = sanitize_strategy_report(strategy_report)

        st.session_state.strategy_report = safe_strategy_report

        delete_current_uploaded_pdf()

        st.session_state.privacy_notice_message = "🔒 분석 완료 후 업로드된 PDF는 자동으로 삭제되었습니다."

        st.rerun()


if st.session_state.guardrail_error_message is not None:
    st.error(st.session_state.guardrail_error_message)


if st.session_state.strategy_report is not None:
    show_result(st.session_state.strategy_report)


if st.session_state.privacy_notice_message is not None:
    st.success(st.session_state.privacy_notice_message)


st.divider()


st.subheader("🔒 개인정보 보호")

st.info("업로드된 PDF는 분석 과정에서만 임시 저장되며, 분석 완료 또는 금지 요청 차단 시 자동 삭제됩니다.")


if st.button("🗑 PDF 수동 삭제"):

    if st.session_state.uploaded_pdf_path is not None:

        delete_current_uploaded_pdf()

        st.session_state.privacy_notice_message = "✅ PDF가 안전하게 삭제되었습니다."

        st.rerun()

    else:
        st.warning("현재 임시 저장된 PDF가 없습니다.")