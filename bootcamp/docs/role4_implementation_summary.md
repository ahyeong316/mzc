# 역할 4 구현 설명서  
## 개인정보 보호·Guardrails·UI·통합 테스트

---

## 1. 담당 역할 개요

본 역할은 순천대학교 전략 큐레이터 시스템에서 사용자의 성적증명서 PDF 업로드 화면을 제공하고, 개인정보 보호와 안전한 서비스 이용을 위한 Guardrails 기능을 구현하는 것을 담당하였다.

사용자가 성적증명서 PDF를 업로드하면 시스템은 해당 PDF를 임시 저장한 뒤 분석 절차를 수행하고, 분석이 완료되거나 금지 요청이 감지되면 업로드된 PDF를 자동으로 삭제하도록 구성하였다.

또한 AI 분석 결과가 화면에 출력되기 전에 학번, 전화번호, 이메일 등의 개인정보가 노출되지 않도록 마스킹 기능을 적용하였다.

---

## 2. 구현 파일

```text
app.py
src/privacy.py
src/guardrails.py
src/display.py
.gitignore
requirements.txt
docs/interface_contract.md
docs/role4_implementation_summary.md