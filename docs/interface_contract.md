# 순천대학교 전략 큐레이터 인터페이스 정의서

## 1. 전체 서비스 흐름

사용자가 성적증명서 PDF를 업로드하면 시스템은 다음 순서로 동작한다.

1. 성적증명서 PDF 임시 저장
2. 성적증명서 PDF OCR/Textract 및 AI 모델 기반 성적정보 추출
3. 최신 교육과정 편람 조회
4. 학과별 졸업요건 검색
5. 졸업요건과 이수 현황 비교
6. 다음 학기 추천 수강 과목 생성
7. 장학금 가능성 및 전략 분석
8. AI 결과 개인정보 마스킹
9. 업로드 PDF 자동 삭제
10. 최종 결과 화면 출력

---

## 2. app.py 최종 연결 예정 흐름

현재 app.py에서는 임시 strategy_report를 사용하고 있다.

최종 통합 시에는 아래 흐름으로 교체한다.

```python
uploaded_pdf_path = st.session_state.uploaded_pdf_path

transcript_data = analyze_transcript_pdf(uploaded_pdf_path)

latest_curriculum_pdf = sync_latest_curriculum_pdf()

curriculum_requirements = get_curriculum_requirements(
    department=transcript_data["department"]
)

strategy_report = create_strategy_report(
    transcript_data=transcript_data,
    curriculum_requirements=curriculum_requirements
)

safe_strategy_report = sanitize_strategy_report(strategy_report)

st.session_state.strategy_report = safe_strategy_report

delete_current_uploaded_pdf()