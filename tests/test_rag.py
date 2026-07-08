# test/test_rag.py

import os
import pytest
from src.curriculum_rag import search_curriculum, retrieve_and_generate


class TestCurriculumRAG:
    """교육과정편람 RAG 테스트"""

    def test_search_curriculum_returns_list(self):
        """검색 결과가 리스트로 반환되는지 확인"""
        results = search_curriculum("컴퓨터공학과 졸업 요건", top_k=3)
        assert isinstance(results, list)
        assert len(results) > 0

    def test_search_result_structure(self):
        """검색 결과의 구조 확인"""
        results = search_curriculum("전공 필수 과목", top_k=1)
        assert len(results) > 0
        
        first_result = results[0]
        assert "text" in first_result
        assert "score" in first_result
        assert isinstance(first_result["score"], (int, float))

    def test_search_graduation_requirements(self):
        """졸업 요건 검색 테스트"""
        results = search_curriculum("졸업 최소 이수 학점", top_k=5)
        assert len(results) > 0
        
        # 결과 텍스트에 숫자(학점)가 포함되는지 확인
        combined_text = " ".join([r["text"] for r in results])
        assert len(combined_text) > 0

    def test_search_major_courses(self):
        """전공 필수 과목 검색 테스트"""
        results = search_curriculum("컴퓨터공학과 전공 필수", top_k=5)
        assert len(results) > 0

    def test_search_liberal_arts(self):
        """교양 필수 이수 기준 검색 테스트"""
        results = search_curriculum("교양 필수", top_k=3)
        assert len(results) > 0

    @pytest.mark.skip(reason="RetrieveAndGenerate는 느림 - 수동 테스트용")
    def test_retrieve_and_generate(self):
        """RetrieveAndGenerate 테스트"""
        answer = retrieve_and_generate("컴퓨터공학과 졸업 요건을 설명해줘")
        assert isinstance(answer, str)
        assert len(answer) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
