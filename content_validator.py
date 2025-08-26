#!/usr/bin/env python3
"""
네이버 카페 콘텐츠 검증 및 정제를 위한 ContentValidator 클래스
"""

import re
import logging
from typing import List, Set, Optional
from content_extraction_models import (
    ValidationResult, 
    ContentValidatorInterface,
    ExtractionConfig
)


class ContentValidator(ContentValidatorInterface):
    """
    콘텐츠 품질 검증 및 정제를 담당하는 클래스
    
    Requirements 4.1, 4.2, 4.4를 구현:
    - 최소 30자 이상의 유효한 텍스트 검증
    - 불필요한 UI 텍스트 제거
    - 내용 정제 및 길이 제한 처리
    """
    
    def __init__(self, config: Optional[ExtractionConfig] = None):
        """
        ContentValidator 초기화
        
        Args:
            config: 추출 설정 (None인 경우 기본값 사용)
        """
        self.config = config or ExtractionConfig()
        self.logger = logging.getLogger(__name__)
        
        # 제거할 UI 텍스트 패턴들 (Requirements 4.2)
        self._ui_text_patterns = self._get_ui_text_patterns()
        
        # 의미없는 텍스트 패턴들
        self._meaningless_patterns = self._get_meaningless_patterns()
    
    def validate_content(self, content: str) -> ValidationResult:
        """
        추출된 콘텐츠의 품질을 검증합니다 (Requirements 4.1, 4.2, 4.4)
        
        Args:
            content: 검증할 콘텐츠
            
        Returns:
            ValidationResult: 검증 결과
        """
        if not isinstance(content, str):
            content = str(content) if content is not None else ""
        
        original_length = len(content)
        issues = []
        
        # 1단계: 기본 정제
        cleaned_content = self.clean_content(content)
        cleaned_length = len(cleaned_content)
        
        # 2단계: 최소 길이 검증 (Requirements 4.1)
        min_length_valid = cleaned_length >= self.config.min_content_length
        if not min_length_valid:
            issues.append(f"콘텐츠 길이가 최소 요구사항({self.config.min_content_length}자)보다 짧습니다: {cleaned_length}자")   
     
        # 3단계: 최대 길이 제한 처리 (Requirements 4.4)
        if cleaned_length > self.config.max_content_length:
            cleaned_content = self._truncate_content(cleaned_content, self.config.max_content_length)
            cleaned_length = len(cleaned_content)
            issues.append(f"콘텐츠가 최대 길이({self.config.max_content_length}자)를 초과하여 잘렸습니다")
        
        # 4단계: 의미있는 콘텐츠 여부 판단
        meaningful_content_ratio = self._calculate_meaningful_content_ratio(cleaned_content)
        if meaningful_content_ratio < 0.3:  # 30% 미만이면 의미없는 콘텐츠로 판단
            issues.append(f"의미있는 콘텐츠 비율이 낮습니다: {meaningful_content_ratio:.2%}")
        
        # 5단계: 품질 점수 계산
        quality_score = self._calculate_quality_score(
            cleaned_content, 
            min_length_valid, 
            meaningful_content_ratio
        )
        
        # 6단계: 전체 유효성 판단
        is_valid = min_length_valid and meaningful_content_ratio >= 0.3 and quality_score >= 0.5
        
        return ValidationResult(
            is_valid=is_valid,
            quality_score=quality_score,
            issues=issues,
            cleaned_content=cleaned_content,
            original_length=original_length,
            cleaned_length=cleaned_length
        )
    
    def clean_content(self, content: str) -> str:
        """
        콘텐츠를 정제합니다 (Requirements 4.2)
        
        Args:
            content: 정제할 콘텐츠
            
        Returns:
            str: 정제된 콘텐츠
        """
        if not content:
            return ""
        
        # 1단계: HTML 태그 제거 (먼저 처리)
        cleaned = self._remove_html_tags(content.strip())
        
        # 2단계: UI 텍스트 제거 (Requirements 4.2)
        cleaned = self._remove_ui_text(cleaned)
        
        # 3단계: 의미없는 패턴 제거
        cleaned = self._remove_meaningless_patterns(cleaned)
        
        # 4단계: 연속된 공백 및 줄바꿈 정리
        cleaned = self._normalize_whitespace(cleaned)
        
        return cleaned.strip()
    
    def _get_ui_text_patterns(self) -> List[str]:
        """
        제거할 UI 텍스트 패턴들을 반환합니다 (Requirements 4.2)
        
        Returns:
            List[str]: UI 텍스트 패턴 목록
        """
        return [
            # 로그인 관련
            r'로그인\s*하세요?',
            r'로그인이?\s*필요합니다?',
            r'회원가입',
            r'아이디\s*저장',
            
            # 메뉴 관련
            r'메뉴',
            r'홈으?로',
            r'목록으?로',
            r'이전\s*페이지',
            r'다음\s*페이지',
            r'페이지\s*이동',
            
            # 댓글 관련
            r'댓글\s*\d*\s*개?',
            r'댓글\s*쓰기',
            r'댓글\s*등록',
            r'답글',
            r'대댓글',
            
            # 공유 및 액션 관련
            r'공유하기',
            r'스크랩',
            r'좋아요\s*\d*',
            r'추천\s*\d*',
            r'신고하기',
            r'수정하기',
            r'삭제하기',
            
            # 네비게이션 관련
            r'카페\s*홈',
            r'게시판',
            r'검색',
            r'전체\s*메뉴',
            
            # 기타 UI 요소
            r'더보기',
            r'접기',
            r'펼치기',
            r'새창',
            r'인쇄',
            r'글자\s*크기',
            r'폰트\s*설정'
        ]
    
    def _get_meaningless_patterns(self) -> List[str]:
        """
        의미없는 텍스트 패턴들을 반환합니다
        
        Returns:
            List[str]: 의미없는 텍스트 패턴 목록
        """
        return [
            # 반복되는 특수문자
            r'[^\w\s가-힣]{3,}',
            
            # 의미없는 반복 텍스트
            r'(\w+)\s*\1\s*\1+',  # 같은 단어 3번 이상 반복
            
            # 광고성 텍스트
            r'광고',
            r'홍보',
            r'이벤트\s*참여',
            r'할인\s*쿠폰',
            
            # 시스템 메시지
            r'시스템\s*오류',
            r'페이지를?\s*찾을\s*수\s*없습니다',
            r'접근\s*권한이?\s*없습니다',
            r'로딩\s*중',
            r'잠시만\s*기다려\s*주세요',
            
            # 빈 콘텐츠 표시
            r'내용이?\s*없습니다',
            r'게시물이?\s*없습니다',
            r'작성된\s*글이?\s*없습니다'
        ]
    
    def _remove_ui_text(self, content: str) -> str:
        """
        UI 텍스트를 제거합니다
        
        Args:
            content: 원본 콘텐츠
            
        Returns:
            str: UI 텍스트가 제거된 콘텐츠
        """
        for pattern in self._ui_text_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.MULTILINE)
        
        return content
    
    def _remove_meaningless_patterns(self, content: str) -> str:
        """
        의미없는 패턴을 제거합니다
        
        Args:
            content: 원본 콘텐츠
            
        Returns:
            str: 의미없는 패턴이 제거된 콘텐츠
        """
        for pattern in self._meaningless_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.MULTILINE)
        
        return content
    
    def _normalize_whitespace(self, content: str) -> str:
        """
        공백과 줄바꿈을 정규화합니다
        
        Args:
            content: 원본 콘텐츠
            
        Returns:
            str: 공백이 정규화된 콘텐츠
        """
        # 연속된 공백을 하나로 통합
        content = re.sub(r'\s+', ' ', content)
        
        # 연속된 줄바꿈을 최대 2개로 제한
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        
        return content
    
    def _remove_html_tags(self, content: str) -> str:
        """
        HTML 태그를 제거합니다
        
        Args:
            content: 원본 콘텐츠
            
        Returns:
            str: HTML 태그가 제거된 콘텐츠
        """
        # HTML 태그 제거 (더 정확한 패턴 사용)
        content = re.sub(r'<[^<>]*>', '', content)
        
        # HTML 엔티티 디코딩
        html_entities = {
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&nbsp;': ' '
        }
        
        for entity, char in html_entities.items():
            content = content.replace(entity, char)
        
        return content    

    def _truncate_content(self, content: str, max_length: int) -> str:
        """
        콘텐츠를 지정된 길이로 자릅니다 (Requirements 4.4)
        
        Args:
            content: 원본 콘텐츠
            max_length: 최대 길이
            
        Returns:
            str: 잘린 콘텐츠
        """
        if len(content) <= max_length:
            return content
        
        # "..." 추가를 고려하여 실제 자를 길이 계산
        actual_max_length = max_length - 3  # "..." 길이 고려
        
        if actual_max_length <= 0:
            return "..."
        
        # 단어 경계에서 자르기 시도
        truncated = content[:actual_max_length]
        
        # 마지막 완전한 문장에서 자르기 시도
        sentence_endings = ['.', '!', '?', '。']  # 한국어 마침표 포함
        last_sentence_end = -1
        
        for ending in sentence_endings:
            pos = truncated.rfind(ending)
            if pos > last_sentence_end:
                last_sentence_end = pos
        
        if last_sentence_end > actual_max_length * 0.7:  # 70% 이상 위치에서 문장이 끝나면
            return truncated[:last_sentence_end + 1]
        
        # 마지막 완전한 단어에서 자르기 시도
        last_space = truncated.rfind(' ')
        if last_space > actual_max_length * 0.8:  # 80% 이상 위치에서 공백이 있으면
            return truncated[:last_space] + "..."
        
        # 그냥 자르고 "..." 추가
        return truncated.rstrip() + "..."
    
    def _calculate_meaningful_content_ratio(self, content: str) -> float:
        """
        의미있는 콘텐츠의 비율을 계산합니다
        
        Args:
            content: 분석할 콘텐츠
            
        Returns:
            float: 의미있는 콘텐츠 비율 (0.0-1.0)
        """
        if not content:
            return 0.0
        
        total_chars = len(content)
        
        # 한글, 영문, 숫자의 비율 계산
        meaningful_chars = len(re.findall(r'[가-힣a-zA-Z0-9]', content))
        
        # 기본 의미있는 문자 비율
        base_ratio = meaningful_chars / total_chars if total_chars > 0 else 0.0
        
        # 문장 구조 보너스 (마침표, 쉼표 등이 적절히 있는지)
        sentence_indicators = len(re.findall(r'[.!?。,]', content))
        sentence_bonus = min(sentence_indicators / (total_chars / 50), 0.2)  # 최대 20% 보너스
        
        # 단어 다양성 보너스
        words = re.findall(r'[가-힣a-zA-Z]+', content)
        unique_words = set(words)
        diversity_bonus = 0.0
        if words:
            diversity_ratio = len(unique_words) / len(words)
            diversity_bonus = min(diversity_ratio * 0.3, 0.15)  # 최대 15% 보너스
        
        final_ratio = min(base_ratio + sentence_bonus + diversity_bonus, 1.0)
        return final_ratio
    
    def _calculate_quality_score(self, content: str, min_length_valid: bool, 
                               meaningful_ratio: float) -> float:
        """
        콘텐츠의 전체 품질 점수를 계산합니다
        
        Args:
            content: 분석할 콘텐츠
            min_length_valid: 최소 길이 조건 만족 여부
            meaningful_ratio: 의미있는 콘텐츠 비율
            
        Returns:
            float: 품질 점수 (0.0-1.0)
        """
        score = 0.0
        
        # 기본 점수: 최소 길이 조건 (30%)
        if min_length_valid:
            score += 0.3
        
        # 의미있는 콘텐츠 비율 (40%)
        score += meaningful_ratio * 0.4
        
        # 콘텐츠 길이 보너스 (20%)
        length = len(content)
        if length >= self.config.min_content_length:
            # 최소 길이의 2배까지는 선형적으로 점수 증가
            optimal_length = self.config.min_content_length * 2
            length_ratio = min(length / optimal_length, 1.0)
            score += length_ratio * 0.2
        
        # 구조적 완성도 (10%)
        # 문단 구분, 문장 구조 등을 평가
        paragraphs = content.split('\n\n')
        if len(paragraphs) > 1:  # 여러 문단이 있으면
            score += 0.05
        
        sentences = re.split(r'[.!?。]', content)
        if len(sentences) > 2:  # 여러 문장이 있으면
            score += 0.05
        
        return min(score, 1.0)
    
    def is_content_too_short(self, content: str) -> bool:
        """
        콘텐츠가 너무 짧은지 확인합니다
        
        Args:
            content: 확인할 콘텐츠
            
        Returns:
            bool: 너무 짧으면 True
        """
        cleaned = self.clean_content(content)
        return len(cleaned) < self.config.min_content_length
    
    def get_content_summary(self, content: str, max_summary_length: int = 100) -> str:
        """
        콘텐츠의 요약을 생성합니다
        
        Args:
            content: 요약할 콘텐츠
            max_summary_length: 최대 요약 길이
            
        Returns:
            str: 콘텐츠 요약
        """
        cleaned = self.clean_content(content)
        
        if len(cleaned) <= max_summary_length:
            return cleaned
        
        # 첫 번째 문장을 우선적으로 사용
        first_sentence_end = min(
            pos for pos in [
                cleaned.find('.'),
                cleaned.find('!'),
                cleaned.find('?'),
                cleaned.find('。')
            ] if pos > 0
        ) if any(pos > 0 for pos in [
            cleaned.find('.'),
            cleaned.find('!'),
            cleaned.find('?'),
            cleaned.find('。')
        ]) else -1
        
        if first_sentence_end > 0 and first_sentence_end <= max_summary_length:
            return cleaned[:first_sentence_end + 1]
        
        # 단어 경계에서 자르기
        truncated = cleaned[:max_summary_length]
        last_space = truncated.rfind(' ')
        
        if last_space > max_summary_length * 0.8:
            return truncated[:last_space] + "..."
        
        return truncated + "..."