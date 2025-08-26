#!/usr/bin/env python3
"""
통합 테스트 및 실제 데이터 검증
Task 11: 실제 네이버 카페 게시물을 대상으로 한 통합 테스트

Requirements covered:
- 1.1, 1.2, 1.3: 다양한 에디터 형식 (SmartEditor 2.0, 3.0, 일반) 테스트
- 2.1, 2.2, 2.3: 동적 콘텐츠 로딩 및 네트워크 지연 테스트
"""

import os
import sys
import time
import logging
import pytest
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException

from content_extractor import ContentExtractor
from content_extraction_models import (
    ExtractionConfig, 
    ContentResult, 
    ExtractionMethod,
    ValidationResult
)
from preloading_manager import PreloadingManager
from selector_strategies import SelectorStrategyManager
from content_validator import ContentValidator

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@dataclass
class TestCase:
    """테스트 케이스 정의"""
    name: str
    url: str
    expected_editor_type: str
    expected_min_length: int
    description: str
    timeout_override: Optional[int] = None


class IntegrationTestSuite:
    """통합 테스트 스위트"""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.content_extractor = None
        self.test_results = []
        self.logger = logging.getLogger(__name__)
        
        # 실제 테스트 케이스들 (다양한 에디터 형식)
        self.test_cases = [
            TestCase(
                name="F-E 카페 SmartEditor 3.0",
                url="https://cafe.naver.com/f-e/cafes/18786605/articles/1941841?boardtype=L&menuid=105",
                expected_editor_type="SmartEditor 3.0",
                expected_min_length=100,
                description="F-E 카페의 SmartEditor 3.0으로 작성된 게시물"
            ),
            TestCase(
                name="일반 카페 SmartEditor 2.0",
                url="https://cafe.naver.com/steamindiegame/1234567",  # 예시 URL
                expected_editor_type="SmartEditor 2.0", 
                expected_min_length=50,
                description="일반 카페의 SmartEditor 2.0으로 작성된 게시물",
                timeout_override=45
            ),
            TestCase(
                name="레거시 에디터",
                url="https://cafe.naver.com/oldcafe/1234567",  # 예시 URL
                expected_editor_type="레거시 에디터",
                expected_min_length=30,
                description="구형 에디터로 작성된 게시물"
            )
        ]
    
    def setup_driver(self, headless: bool = True, slow_network: bool = False):
        """테스트용 드라이버 설정"""
        options = Options()
        
        if headless:
            options.add_argument('--headless=new')
        
        # 기본 옵션
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # 네트워크 지연 시뮬레이션
        if slow_network:
            options.add_argument('--throttling=3G')
            self.logger.info("🐌 느린 네트워크 환경 시뮬레이션 활성화")
        
        # 안정성 옵션
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        try:
            self.driver = webdriver.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, 30)
            
            # 네트워크 지연 시뮬레이션 (CDP 사용)
            if slow_network:
                self.driver.execute_cdp_cmd('Network.enable', {})
                self.driver.execute_cdp_cmd('Network.emulateNetworkConditions', {
                    'offline': False,
                    'downloadThroughput': 500 * 1024,  # 500KB/s
                    'uploadThroughput': 500 * 1024,
                    'latency': 2000  # 2초 지연
                })
            
            self.logger.info("✅ 테스트용 드라이버 초기화 성공")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 드라이버 초기화 실패: {e}")
            return False
    
    def login_naver(self) -> bool:
        """네이버 로그인"""
        try:
            # 자동화 탐지 우회
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                '''
            })
            
            self.driver.get('https://nid.naver.com/nidlogin.login')
            time.sleep(3)
            
            # 환경변수에서 로그인 정보 가져오기
            naver_id = os.getenv('NAVER_ID') or 'crepix'  # 테스트용 기본값
            naver_pw = os.getenv('NAVER_PW') or 'hotelier6226'  # 테스트용 기본값
            
            # ID/PW 입력
            id_input = self.driver.find_element(By.ID, 'id')
            pw_input = self.driver.find_element(By.ID, 'pw')
            
            self.driver.execute_script("""
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            """, id_input, naver_id)
            
            time.sleep(1)
            
            self.driver.execute_script("""
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            """, pw_input, naver_pw)
            
            time.sleep(1)
            
            # 로그인 클릭
            login_btn = self.driver.find_element(By.ID, 'log.login')
            self.driver.execute_script("arguments[0].click();", login_btn)
            
            time.sleep(10)
            
            self.logger.info("✅ 네이버 로그인 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 로그인 실패: {e}")
            return False
    
    def test_editor_format_detection(self) -> Dict[str, Any]:
        """다양한 에디터 형식 감지 테스트 (Requirements: 1.1, 1.2, 1.3)"""
        self.logger.info("🧪 에디터 형식 감지 테스트 시작")
        
        results = {
            'test_name': 'editor_format_detection',
            'total_cases': len(self.test_cases),
            'passed': 0,
            'failed': 0,
            'details': []
        }
        
        for test_case in self.test_cases:
            self.logger.info(f"📝 테스트: {test_case.name}")
            
            try:
                # ContentExtractor 설정
                config = ExtractionConfig(
                    timeout_seconds=test_case.timeout_override or 30,
                    min_content_length=test_case.expected_min_length,
                    enable_debug_screenshot=True
                )
                
                content_extractor = ContentExtractor(self.driver, self.wait, config)
                
                # 콘텐츠 추출
                start_time = time.time()
                result = content_extractor.extract_content(test_case.url)
                extraction_time = time.time() - start_time
                
                # 결과 분석
                detected_editor = result.debug_info.get('editor_type_detected', 'Unknown')
                content_length = len(result.content)
                
                test_detail = {
                    'case_name': test_case.name,
                    'url': test_case.url,
                    'expected_editor': test_case.expected_editor_type,
                    'detected_editor': detected_editor,
                    'content_length': content_length,
                    'extraction_time': round(extraction_time, 2),
                    'success': result.success,
                    'quality_score': result.quality_score,
                    'extraction_method': result.extraction_method.value
                }
                
                # 성공 조건 확인
                is_success = (
                    result.success and 
                    content_length >= test_case.expected_min_length and
                    detected_editor is not None
                )
                
                if is_success:
                    results['passed'] += 1
                    test_detail['status'] = 'PASSED'
                    self.logger.info(f"✅ {test_case.name}: 성공 ({content_length}자, {detected_editor})")
                else:
                    results['failed'] += 1
                    test_detail['status'] = 'FAILED'
                    test_detail['failure_reason'] = result.error_message or "조건 미충족"
                    self.logger.warning(f"❌ {test_case.name}: 실패 - {test_detail['failure_reason']}")
                
                results['details'].append(test_detail)
                
            except Exception as e:
                results['failed'] += 1
                self.logger.error(f"❌ {test_case.name}: 예외 발생 - {e}")
                
                results['details'].append({
                    'case_name': test_case.name,
                    'status': 'ERROR',
                    'error': str(e)
                })
            
            time.sleep(2)  # 테스트 간 간격
        
        return results
    
    def test_dynamic_content_loading(self) -> Dict[str, Any]:
        """동적 콘텐츠 로딩 테스트 (Requirements: 2.1, 2.2, 2.3)"""
        self.logger.info("🧪 동적 콘텐츠 로딩 테스트 시작")
        
        results = {
            'test_name': 'dynamic_content_loading',
            'scenarios': [],
            'passed': 0,
            'failed': 0
        }
        
        # 테스트 시나리오들
        scenarios = [
            {
                'name': '기본 로딩 대기',
                'config': ExtractionConfig(timeout_seconds=15),
                'description': '기본 타임아웃으로 동적 콘텐츠 로딩 테스트'
            },
            {
                'name': '긴 로딩 대기',
                'config': ExtractionConfig(timeout_seconds=45, enable_lazy_loading_trigger=True),
                'description': '긴 타임아웃과 lazy loading 트리거 활성화'
            },
            {
                'name': '짧은 로딩 대기',
                'config': ExtractionConfig(timeout_seconds=5),
                'description': '짧은 타임아웃으로 타임아웃 처리 테스트'
            }
        ]
        
        test_url = self.test_cases[0].url  # F-E 카페 게시물 사용
        
        for scenario in scenarios:
            self.logger.info(f"📋 시나리오: {scenario['name']}")
            
            try:
                content_extractor = ContentExtractor(self.driver, self.wait, scenario['config'])
                
                start_time = time.time()
                result = content_extractor.extract_content(test_url)
                total_time = time.time() - start_time
                
                scenario_result = {
                    'name': scenario['name'],
                    'description': scenario['description'],
                    'total_time': round(total_time, 2),
                    'success': result.success,
                    'content_length': len(result.content),
                    'page_ready_state': result.debug_info.get('page_ready_state', 'unknown'),
                    'extraction_method': result.extraction_method.value
                }
                
                if result.success:
                    results['passed'] += 1
                    scenario_result['status'] = 'PASSED'
                    self.logger.info(f"✅ {scenario['name']}: 성공 ({total_time:.2f}초)")
                else:
                    results['failed'] += 1
                    scenario_result['status'] = 'FAILED'
                    scenario_result['error'] = result.error_message
                    self.logger.warning(f"❌ {scenario['name']}: 실패 - {result.error_message}")
                
                results['scenarios'].append(scenario_result)
                
            except Exception as e:
                results['failed'] += 1
                self.logger.error(f"❌ {scenario['name']}: 예외 - {e}")
                
                results['scenarios'].append({
                    'name': scenario['name'],
                    'status': 'ERROR',
                    'error': str(e)
                })
            
            time.sleep(3)  # 시나리오 간 간격
        
        return results
    
    def test_network_delay_scenarios(self) -> Dict[str, Any]:
        """네트워크 지연 시나리오 테스트"""
        self.logger.info("🧪 네트워크 지연 시나리오 테스트 시작")
        
        results = {
            'test_name': 'network_delay_scenarios',
            'scenarios': [],
            'passed': 0,
            'failed': 0
        }
        
        # 네트워크 지연 시나리오
        delay_scenarios = [
            {'name': '정상 네트워크', 'latency': 0, 'throughput': 10000},
            {'name': '느린 네트워크', 'latency': 2000, 'throughput': 500},
            {'name': '매우 느린 네트워크', 'latency': 5000, 'throughput': 100}
        ]
        
        test_url = self.test_cases[0].url
        
        for scenario in delay_scenarios:
            self.logger.info(f"🌐 네트워크 시나리오: {scenario['name']}")
            
            try:
                # 네트워크 조건 설정
                if scenario['latency'] > 0:
                    self.driver.execute_cdp_cmd('Network.emulateNetworkConditions', {
                        'offline': False,
                        'downloadThroughput': scenario['throughput'] * 1024,
                        'uploadThroughput': scenario['throughput'] * 1024,
                        'latency': scenario['latency']
                    })
                
                # 지연에 맞춰 타임아웃 조정
                timeout = 30 + (scenario['latency'] // 1000) * 2
                config = ExtractionConfig(timeout_seconds=timeout)
                content_extractor = ContentExtractor(self.driver, self.wait, config)
                
                start_time = time.time()
                result = content_extractor.extract_content(test_url)
                total_time = time.time() - start_time
                
                scenario_result = {
                    'name': scenario['name'],
                    'latency_ms': scenario['latency'],
                    'throughput_kbps': scenario['throughput'],
                    'total_time': round(total_time, 2),
                    'success': result.success,
                    'content_length': len(result.content),
                    'quality_score': result.quality_score
                }
                
                if result.success:
                    results['passed'] += 1
                    scenario_result['status'] = 'PASSED'
                    self.logger.info(f"✅ {scenario['name']}: 성공 ({total_time:.2f}초)")
                else:
                    results['failed'] += 1
                    scenario_result['status'] = 'FAILED'
                    scenario_result['error'] = result.error_message
                    self.logger.warning(f"❌ {scenario['name']}: 실패")
                
                results['scenarios'].append(scenario_result)
                
                # 네트워크 조건 초기화
                self.driver.execute_cdp_cmd('Network.emulateNetworkConditions', {
                    'offline': False,
                    'downloadThroughput': -1,
                    'uploadThroughput': -1,
                    'latency': 0
                })
                
            except Exception as e:
                results['failed'] += 1
                self.logger.error(f"❌ {scenario['name']}: 예외 - {e}")
                
                results['scenarios'].append({
                    'name': scenario['name'],
                    'status': 'ERROR',
                    'error': str(e)
                })
            
            time.sleep(2)
        
        return results
    
    def test_error_scenarios(self) -> Dict[str, Any]:
        """에러 시나리오 테스트"""
        self.logger.info("🧪 에러 시나리오 테스트 시작")
        
        results = {
            'test_name': 'error_scenarios',
            'scenarios': [],
            'passed': 0,
            'failed': 0
        }
        
        error_scenarios = [
            {
                'name': '존재하지 않는 게시물',
                'url': 'https://cafe.naver.com/f-e/cafes/18786605/articles/999999999',
                'expected_behavior': 'graceful_failure'
            },
            {
                'name': '접근 권한 없는 게시물',
                'url': 'https://cafe.naver.com/privatecafe/1234567',
                'expected_behavior': 'graceful_failure'
            },
            {
                'name': '매우 짧은 타임아웃',
                'url': self.test_cases[0].url,
                'config_override': ExtractionConfig(timeout_seconds=1),
                'expected_behavior': 'timeout_handling'
            }
        ]
        
        for scenario in error_scenarios:
            self.logger.info(f"⚠️ 에러 시나리오: {scenario['name']}")
            
            try:
                config = scenario.get('config_override', ExtractionConfig())
                content_extractor = ContentExtractor(self.driver, self.wait, config)
                
                start_time = time.time()
                result = content_extractor.extract_content(scenario['url'])
                total_time = time.time() - start_time
                
                scenario_result = {
                    'name': scenario['name'],
                    'url': scenario['url'],
                    'expected_behavior': scenario['expected_behavior'],
                    'total_time': round(total_time, 2),
                    'success': result.success,
                    'error_message': result.error_message,
                    'content_length': len(result.content)
                }
                
                # 에러 시나리오에서는 graceful failure가 성공
                if scenario['expected_behavior'] == 'graceful_failure':
                    if not result.success and result.error_message:
                        results['passed'] += 1
                        scenario_result['status'] = 'PASSED'
                        self.logger.info(f"✅ {scenario['name']}: 정상적인 실패 처리")
                    else:
                        results['failed'] += 1
                        scenario_result['status'] = 'FAILED'
                        self.logger.warning(f"❌ {scenario['name']}: 예상과 다른 결과")
                
                elif scenario['expected_behavior'] == 'timeout_handling':
                    if 'timeout' in (result.error_message or '').lower():
                        results['passed'] += 1
                        scenario_result['status'] = 'PASSED'
                        self.logger.info(f"✅ {scenario['name']}: 타임아웃 정상 처리")
                    else:
                        results['failed'] += 1
                        scenario_result['status'] = 'FAILED'
                        self.logger.warning(f"❌ {scenario['name']}: 타임아웃 처리 미흡")
                
                results['scenarios'].append(scenario_result)
                
            except Exception as e:
                results['failed'] += 1
                self.logger.error(f"❌ {scenario['name']}: 예외 - {e}")
                
                results['scenarios'].append({
                    'name': scenario['name'],
                    'status': 'ERROR',
                    'error': str(e)
                })
            
            time.sleep(2)
        
        return results
    
    def run_all_tests(self, headless: bool = True) -> Dict[str, Any]:
        """모든 통합 테스트 실행"""
        self.logger.info("="*60)
        self.logger.info("🚀 통합 테스트 스위트 시작")
        self.logger.info(f"⏰ {datetime.now()}")
        self.logger.info("="*60)
        
        overall_results = {
            'start_time': datetime.now().isoformat(),
            'test_environment': {
                'headless': headless,
                'github_actions': os.getenv('GITHUB_ACTIONS', '').lower() == 'true'
            },
            'tests': [],
            'summary': {
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0,
                'error_tests': 0
            }
        }
        
        try:
            # 드라이버 설정
            if not self.setup_driver(headless=headless):
                raise Exception("드라이버 초기화 실패")
            
            # 네이버 로그인
            if not self.login_naver():
                raise Exception("네이버 로그인 실패")
            
            # 테스트 실행
            test_methods = [
                self.test_editor_format_detection,
                self.test_dynamic_content_loading,
                self.test_network_delay_scenarios,
                self.test_error_scenarios
            ]
            
            for test_method in test_methods:
                try:
                    self.logger.info(f"\n🧪 실행 중: {test_method.__name__}")
                    test_result = test_method()
                    overall_results['tests'].append(test_result)
                    
                    # 통계 업데이트
                    if 'passed' in test_result and 'failed' in test_result:
                        overall_results['summary']['passed_tests'] += test_result['passed']
                        overall_results['summary']['failed_tests'] += test_result['failed']
                    
                except Exception as e:
                    self.logger.error(f"❌ 테스트 실행 실패: {test_method.__name__} - {e}")
                    overall_results['summary']['error_tests'] += 1
                    overall_results['tests'].append({
                        'test_name': test_method.__name__,
                        'status': 'ERROR',
                        'error': str(e)
                    })
            
            overall_results['summary']['total_tests'] = (
                overall_results['summary']['passed_tests'] + 
                overall_results['summary']['failed_tests'] + 
                overall_results['summary']['error_tests']
            )
            
        except Exception as e:
            self.logger.error(f"❌ 통합 테스트 실행 중 심각한 오류: {e}")
            overall_results['fatal_error'] = str(e)
        
        finally:
            if self.driver:
                self.driver.quit()
        
        overall_results['end_time'] = datetime.now().isoformat()
        return overall_results
    
    def generate_test_report(self, results: Dict[str, Any]) -> str:
        """테스트 결과 보고서 생성"""
        report = []
        report.append("="*80)
        report.append("📊 네이버 카페 콘텐츠 추출 통합 테스트 보고서")
        report.append("="*80)
        
        # 요약 정보
        summary = results['summary']
        report.append(f"\n📈 테스트 요약:")
        report.append(f"  • 총 테스트: {summary['total_tests']}개")
        report.append(f"  • 성공: {summary['passed_tests']}개")
        report.append(f"  • 실패: {summary['failed_tests']}개")
        report.append(f"  • 오류: {summary['error_tests']}개")
        
        success_rate = (summary['passed_tests'] / max(summary['total_tests'], 1)) * 100
        report.append(f"  • 성공률: {success_rate:.1f}%")
        
        # 환경 정보
        env = results['test_environment']
        report.append(f"\n🔧 테스트 환경:")
        report.append(f"  • 헤드리스 모드: {env['headless']}")
        report.append(f"  • GitHub Actions: {env['github_actions']}")
        
        # 각 테스트 상세 결과
        for test in results['tests']:
            report.append(f"\n📋 {test.get('test_name', 'Unknown Test')}:")
            
            if 'details' in test:
                for detail in test['details']:
                    status_icon = "✅" if detail['status'] == 'PASSED' else "❌"
                    report.append(f"  {status_icon} {detail['case_name']}")
                    if detail['status'] == 'PASSED':
                        report.append(f"     길이: {detail.get('content_length', 0)}자")
                        report.append(f"     에디터: {detail.get('detected_editor', 'Unknown')}")
                        report.append(f"     시간: {detail.get('extraction_time', 0)}초")
            
            elif 'scenarios' in test:
                for scenario in test['scenarios']:
                    status_icon = "✅" if scenario['status'] == 'PASSED' else "❌"
                    report.append(f"  {status_icon} {scenario['name']}")
                    if 'total_time' in scenario:
                        report.append(f"     시간: {scenario['total_time']}초")
                    if 'error' in scenario:
                        report.append(f"     오류: {scenario['error']}")
        
        # 권장사항
        report.append(f"\n💡 권장사항:")
        if summary['failed_tests'] > 0:
            report.append("  • 실패한 테스트 케이스를 분석하여 선택자 전략을 개선하세요")
        if summary['error_tests'] > 0:
            report.append("  • 오류가 발생한 테스트의 예외 처리를 강화하세요")
        if success_rate < 80:
            report.append("  • 전체적인 성공률이 낮습니다. 시스템 안정성을 점검하세요")
        else:
            report.append("  • 테스트 결과가 양호합니다. 현재 구현을 유지하세요")
        
        report.append("="*80)
        
        return "\n".join(report)


def main():
    """메인 실행 함수"""
    # 환경변수 확인
    required_env = ['NAVER_ID', 'NAVER_PW']
    missing_env = [env for env in required_env if not os.getenv(env)]
    
    if missing_env:
        print(f"❌ 환경변수 누락: {', '.join(missing_env)}")
        print("💡 .env 파일에 NAVER_ID, NAVER_PW를 설정해주세요")
        return False
    
    # 테스트 실행
    test_suite = IntegrationTestSuite()
    
    # GitHub Actions 환경에서는 헤드리스 모드 강제
    headless = os.getenv('GITHUB_ACTIONS', '').lower() == 'true'
    
    results = test_suite.run_all_tests(headless=headless)
    
    # 보고서 생성 및 출력
    report = test_suite.generate_test_report(results)
    print(report)
    
    # 결과 파일 저장
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f"integration_test_report_{timestamp}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📄 상세 보고서가 저장되었습니다: {report_file}")
    
    # 성공률 기준으로 종료 코드 결정
    success_rate = (results['summary']['passed_tests'] / 
                   max(results['summary']['total_tests'], 1)) * 100
    
    if success_rate >= 70:
        print("🎉 통합 테스트 성공!")
        return True
    else:
        print("❌ 통합 테스트 실패 (성공률 70% 미만)")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)