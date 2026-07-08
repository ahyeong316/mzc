import streamlit as st


def show_result(report):
    """역할 3의 strategy_report(dict)를 화면에 출력한다.

    report 구조:
    {
        "student_summary": {department, student_year, gpa, extraction_confidence},
        "curriculum_source": {source_pdf, last_synced_at},
        "graduation_analysis": {...},
        "course_recommendations": [...],
        "scholarship_strategy": {...},
        "warnings": [...],
    }
    """

    student = report.get("student_summary", {})
    grad = report.get("graduation_analysis", {})
    recommendations = report.get("course_recommendations", [])
    scholarship = report.get("scholarship_strategy", {})
    warnings = report.get("warnings", [])

    st.divider()

    # ── 학생 요약 ─────────────────────────────
    st.subheader("📄 현재 이수 현황")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("학과", student.get("department") or "-")

    with col2:
        st.metric(
            "총 취득학점",
            f'{grad.get("current_total_credits", 0)} / {grad.get("required_total_credits", 0)}',
        )

    with col3:
        st.metric("평균평점(GPA)", student.get("gpa") or "-")

    col4, col5 = st.columns(2)

    with col4:
        st.metric(
            "전공 학점",
            f'{grad.get("current_major_credits", 0)} / {grad.get("required_major_credits", 0)}',
        )

    with col5:
        st.metric(
            "교양 학점",
            f'{grad.get("current_general_credits", 0)} / {grad.get("required_general_credits", 0)}',
        )

    completed = grad.get("completed_required_courses", [])
    if completed:
        st.write("### ✅ 이수한 전공필수")
        st.write(", ".join(completed))

    st.divider()

    # ── 졸업 분석 ─────────────────────────────
    st.subheader("🎓 졸업 분석")

    if grad.get("is_graduation_ready"):
        st.success("🎉 졸업 요건을 모두 충족했습니다!")
    else:
        st.metric("남은 졸업학점", grad.get("remaining_total_credits", 0))

        missing = grad.get("missing_required_courses", [])
        if missing:
            st.write("### 📌 남은 전공필수")
            for subject in missing:
                st.write(f"- {subject}")

    st.divider()

    # ── 추천 과목 ─────────────────────────────
    st.subheader("📚 다음 학기 추천 과목")

    if recommendations:
        for rec in recommendations:
            name = rec.get("course_name", "-")
            category = rec.get("category", "")
            priority = rec.get("priority", "")
            reason = rec.get("reason", "")

            st.markdown(f"**{name}** ({category} · 우선순위: {priority})")
            if reason:
                st.caption(reason)
    else:
        st.write("추천 과목이 없습니다.")

    st.divider()

    # ── 장학금 전략 ───────────────────────────
    st.subheader("💰 장학금 전략")

    col6, col7 = st.columns(2)

    with col6:
        st.metric("현재 GPA", scholarship.get("current_gpa") or "-")

    with col7:
        st.metric("전체 가능성", scholarship.get("possibility") or "판단 불가")

    advice = scholarship.get("advice")
    if advice:
        st.success(advice)

    for item in scholarship.get("recommended_scholarships", []):
        with st.expander(f'🏅 {item.get("name", "장학금")} — 가능성: {item.get("possibility", "판단 불가")}'):
            if item.get("reason"):
                st.write(item["reason"])

            checks = item.get("requirements_to_check", [])
            if checks:
                st.write("**확인 필요 조건**")
                for c in checks:
                    st.write(f"- {c}")

    # ── 주의사항 ─────────────────────────────
    if warnings:
        st.divider()
        st.subheader("⚠️ 주의사항")
        for w in warnings:
            st.warning(w)
