#!/usr/bin/env python3
"""
에디터 형식별 특화 테스트
다양한 네이버 카페 에디터 형식에 대한 세부 테스트
"""

import pytest
import time
import logging
from typing import Dict, List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from content_extractor import ContentExtractor
from content_extraction_models import ExtractionConfig, ExtractionMethod
from selector_strategies import (
    SmartEditor3Strategy,
    SmartEditor2Strategy, 
    GeneralEditorStrategy,
    LegacyEditorStrategy
)

logging.basicConfig(level=logging.INFO)


class TestEditorFormats:
    """에디터 형식별 테스트 클래스"""
    
    @pytest.fixture(scope="class")
    def driver_setup(self):
        """테스트용 드라이버 설정"""
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 30)
        
        yield driver, wait
        
        driver.quit()
    
    @pytest.fixture(scope="class")
    def logged_in_driver(self, driver_setup):
        """로그인된 드라이버"""
        driver, wait = driver_setup
        
        # 네이버 로그인 (실제 테스트에서는 환경변수 사용)
        driver.get('https://nid.naver.com/nidlogin.login')
        time.sleep(2)
        
        # 로그인 로직 (간소화)
        # 실제 구현에서는 환경변수에서 계정 정보 가져오기
        
        yield driver, wait
    
    def test_smart_editor_3_detection(self, logged_in_driver):
        """SmartEditor 3.0 감지 및 추출 테스트 (Requirement 1.1)"""
        driver, wait = logged_in_driver
        
        # SmartEditor 3.0 전략 테스트
        strategy = SmartEditor3Strategy()
        selectors = strategy.get_selectors()
        
        # 선택자가 올바르게 정의되어 있는지 확인
        assert '.se-main-container' in selectors
        assert '.se-text-paragraph' in selectors
        
        # 실제 게시물에서 테스트 (모의 HTML 사용)
        test_html = """
        <div class="se-main-container">
            <div class="se-text-paragraph">
                <span class="se-text">테스트 내용입니다.</span>
            </div>
            <div class="se-image-container">
                <img class="se-image-resource" src="test.jpg" />
            </div>
        </div>
        """
        
        # JavaScript로 테스트 HTML 삽입
        driver.execute_script(f"document.body.innerHTML = `{test_html}`;")
        
        # 전략으로 추출 시도
        content = strategy.extract_with_selectors(driver)
        
        assert content is not None
        assert "테스트 내용입니다" in content
        assert strategy.get_strategy_name() == "SmartEditor 3.0"
    
    def test_smart_editor_2_detection(self, logged_in_driver):
        """SmartEditor 2.0 감지 및 추출 테스트 (Requirement 1.2)"""
        driver, wait = logged_in_driver
        
        strategy = SmartEditor2Strategy()
        selectors = strategy.get_selectors()
        
        # SmartEditor 2.0 선택자 확인
        assert '.ContentRenderer' in selectors
        assert '#postViewArea' in selectors
        
        # 모의 HTML로 테스트
        test_html = """
        <div class="ContentRenderer">
            <div id="postViewArea">
                <p>SmartEditor 2.0 테스트 내용</p>
                <img src="image.jpg" alt="테스트 이미지" />
            </div>
        </div>
        """
        
        driver.execute_script(f"document.body.innerHTML = `{test_html}`;")
        
        content = strategy.extract_with_selectors(driver)
        
        assert content is not None
        assert "SmartEditor 2.0 테스트 내용" in content
        assert strategy.get_strategy_name() == "SmartEditor 2.0"
    
    def test_general_editor_detection(self, logged_in_driver):
        """일반 에디터 감지 및 추출 테스트 (Requirement 1.3)"""
        driver, wait = logged_in_driver
        
        strategy = GeneralEditorStrategy()
        selectors = strategy.get_selectors()
        
        # 일반 에디터 선택자 확인
        assert '#content-area' in selectors
        assert '.content-body' in selectors
        
        # 모의 HTML로 테스트
        test_html = """
        <div id="content-area">
            <div class="content-body">
                <p>일반 에디터 테스트 내용입니다.</p>
                <div>추가 내용</div>
            </div>
        </div>
        """
        
        driver.execute_script(f"document.body.innerHTML = `{test_html}`;")
        
        content = strategy.extract_with_selectors(driver)
        
        assert content is not None
        assert "일반 에디터 테스트 내용" in content
        assert strategy.get_strategy_name() == "일반 에디터"
    
    def test_legacy_editor_detection(self, logged_in_driver):
        """레거시 에디터 감지 및 추출 테스트 (Requirement 1.3)"""
        driver, wait = logged_in_driver
        
        strategy = LegacyEditorStrategy()
        selectors = strategy.get_selectors()
        
        # 레거시 에디터 선택자 확인
        assert '#tbody' in selectors
        assert 'table.board-content' in selectors
        
        # 모의 HTML로 테스트
        test_html = """
        <table class="board-content">
            <tbody id="tbody">
                <tr>
                    <td>레거시 에디터 내용</td>
                </tr>
                <tr>
                    <td>추가 행 내용</td>
                </tr>
            </tbody>
        </table>
        """
        
        driver.execute_script(f"document.body.innerHTML = `{test_html}`;")
        
        content = strategy.extract_with_selectors(driver)
        
        assert content is not None
        assert "레거시 에디터 내용" in content
        assert strategy.get_strategy_name() == "레거시 에디터"
    
    def test_extraction_method_priority(self, logged_in_driver):
        """추출 방법 우선순위 테스트"""
        driver, wait = logged_in_driver
        
        config = ExtractionConfig(timeout_seconds=15)
        extractor = ContentExtractor(driver, wait, config)
        
        # 여러 에디터 요소가 동시에 존재하는 경우 테스트
        mixed_html = """
        <div class="se-main-container">
            <div class="se-text-paragraph">SmartEditor 3.0 내용</div>
        </div>
        <div class="ContentRenderer">
            <div>SmartEditor 2.0 내용</div>
        </div>
        <div id="content-area">
            <div>일반 에디터 내용</div>
        </div>
        """
        
        driver.execute_script(f"document.body.innerHTML = `{mixed_html}`;")
        
        # 전략 매니저를 통한 추출
        strategy_manager = extractor.selector_strategy
        result = strategy_manager.extract_with_strategies(driver)
        
        # SmartEditor 3.0이 최우선이므로 해당 내용이 추출되어야 함
        assert result is not None
        assert result['content'] is not None
        assert "SmartEditor 3.0 내용" in result['content']
        assert result['extraction_method'] == ExtractionMethod.SMART_EDITOR_3
    
    def test_content_quality_validation(self, logged_in_driver):
        """콘텐츠 품질 검증 테스트"""
        driver, wait = logged_in_driver
        
        config = ExtractionConfig(
            min_content_length=20,
            max_content_length=1000
        )
        extractor = ContentExtractor(driver, wait, config)
        
        # 품질이 낮은 콘텐츠 테스트
        low_quality_html = """
        <div class="se-main-container">
            <div class="se-text-paragraph">짧음</div>
        </div>
        """
        
        driver.execute_script(f"document.body.innerHTML = `{low_quality_html}`;")
        
        # 콘텐츠 검증기 직접 테스트
        validator = extractor.validator
        validation_result = validator.validate_content("짧음")
        
        # 최소 길이 미달로 품질이 낮아야 함
        assert validation_result.quality_score < 0.5
        assert not validation_result.is_valid
        assert "내용이 너무 짧습니다" in validation_result.issues
    
    def test_image_extraction(self, logged_in_driver):
        """이미지 추출 테스트"""
        driver, wait = logged_in_driver
        
        # 이미지가 포함된 HTML
        image_html = """
        <div class="se-main-container">
            <div class="se-text-paragraph">
                <span class="se-text">이미지가 포함된 게시물입니다.</span>
            </div>
            <div class="se-image-container">
                <img class="se-image-resource" 
                     data-src="https://example.com/image1.jpg" 
                     alt="테스트 이미지 1" />
            </div>
            <div class="se-image-container">
                <img class="se-image-resource" 
                     src="https://example.com/image2.jpg" 
                     alt="테스트 이미지 2" />
            </div>
        </div>
        """
        
        driver.execute_script(f"document.body.innerHTML = `{image_html}`;")
        
        strategy = SmartEditor3Strategy()
        content = strategy.extract_with_selectors(driver)
        
        assert content is not None
        assert "이미지가 포함된 게시물입니다" in content
        # 이미지 URL이 포함되어야 함
        assert "https://example.com/image1.jpg" in content or "https://example.com/image2.jpg" in content
    
    @pytest.mark.parametrize("editor_type,html_template", [
        ("SmartEditor 3.0", """
            <div class="se-main-container">
                <div class="se-text-paragraph">
                    <span class="se-text">{content}</span>
                </div>
            </div>
        """),
        ("SmartEditor 2.0", """
            <div class="ContentRenderer">
                <div id="postViewArea">
                    <p>{content}</p>
                </div>
            </div>
        """),
        ("일반 에디터", """
            <div id="content-area">
                <div class="content-body">
                    <p>{content}</p>
                </div>
            </div>
        """),
        ("레거시 에디터", """
            <table class="board-content">
                <tbody id="tbody">
                    <tr><td>{content}</td></tr>
                </tbody>
            </table>
        """)
    ])
    def test_all_editor_formats(self, logged_in_driver, editor_type, html_template):
        """모든 에디터 형식에 대한 매개변수화된 테스트"""
        driver, wait = logged_in_driver
        
        test_content = f"{editor_type} 테스트 내용입니다. 이것은 충분히 긴 내용으로 품질 검증을 통과해야 합니다."
        html = html_template.format(content=test_content)
        
        driver.execute_script(f"document.body.innerHTML = `{html}`;")
        
        config = ExtractionConfig(min_content_length=20)
        extractor = ContentExtractor(driver, wait, config)
        
        # 전략 매니저를 통한 추출
        result = extractor.selector_strategy.extract_with_strategies(driver)
        
        assert result is not None
        assert result['content'] is not None
        assert test_content in result['content']
        
        # 품질 검증
        validation = extractor.validator.validate_content(result['content'])
        assert validation.is_valid
        assert validation.quality_score > 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])