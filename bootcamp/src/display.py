import streamlit as st


def show_result(result):

    st.divider()

    st.subheader("📄 현재 이수 현황")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("총 취득학점", result["earned_credit"])

    with col2:
        st.metric("평균평점", result["gpa"])

    st.write("### ✅ 전공 이수 과목")

    for subject in result["major_subjects"]:
        st.write(subject)

    st.divider()

    st.subheader("🎓 졸업 분석")

    st.metric("남은 졸업학점", result["remaining_credit"])

    st.write("### 📌 남은 전공필수")

    for subject in result["remaining_subjects"]:
        st.write(subject)

    st.divider()

    st.subheader("📚 추천 수강 과목")

    for subject in result["recommend_subjects"]:
        st.write(subject)

    st.divider()

    st.subheader("💰 장학금 전략")

    st.success(result["scholarship"])