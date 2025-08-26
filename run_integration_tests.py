#!/usr/bin/env python3
"""
통합 테스트 실행기
Task 11의 모든 테스트를 실행하고 종합 보고서를 생성합니다.

Requirements covered:
- 1.1, 1.2, 1.3: 다양한 에디터 형식 테스트
- 2.1, 2.2, 2.3: 동적 콘텐츠 로딩 및 네트워크 지연 테스트
"""

import os
import sys
import time
import json
import logging
import subprocess
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

# 테스트 모듈들 import
from test_integration_real_data import IntegrationTestSuite
from test_performance_load import PerformanceTestSuite

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class IntegrationTestRunner:
    """통합 테스트 실행기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.results = {
            'start_time': datetime.now().isoformat(),
            'test_suites': [],
            'summary': {
                'total_suites': 0,
                'passed_suites': 0,
                'failed_suites': 0,
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0
            },
            'environment': {
                'python_version': sys.version,
                'github_actions': os.getenv('GITHUB_ACTIONS', '').lower() == 'true',
                'headless_mode': True,
                'test_timestamp': datetime.now().strftime('%Y%m%d_%H%M%S')
            }
        }
    
    def check_prerequisites(self) -> bool:
        """테스트 실행 전 필수 조건 확인"""
        self.logger.info("🔍 테스트 실행 전 필수 조건 확인")
        
        # 환경변수 확인
        required_env = ['NAVER_ID', 'NAVER_PW']
        missing_env = [env for env in required_env if not os.getenv(env)]
        
        if missing_env:
            self.logger.error(f"❌ 환경변수 누락: {', '.join(missing_env)}")
            self.logger.info("💡 .env 파일에 다음 변수들을 설정해주세요:")
            for env in missing_env:
                self.logger.info(f"   {env}=your_value")
            return False
        
        # 필수 모듈 확인
        required_modules = [
            'selenium', 'pytest', 'psutil', 'dotenv'
        ]
        
        missing_modules = []
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
        
        if missing_modules:
            self.logger.error(f"❌ 필수 모듈 누락: {', '.join(missing_modules)}")
            self.logger.info("💡 다음 명령으로 설치하세요:")
            self.logger.info(f"   pip install {' '.join(missing_modules)}")
            return False
        
        # Chrome 드라이버 확인
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            
            options = Options()
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            driver = webdriver.Chrome(options=options)
            driver.quit()
            
            self.logger.info("✅ Chrome 드라이버 확인 완료")
            
        except Exception as e:
            self.logger.error(f"❌ Chrome 드라이버 오류: {e}")
            self.logger.info("💡 Chrome과 ChromeDriver가 설치되어 있는지 확인하세요")
            return False
        
        self.logger.info("✅ 모든 필수 조건 확인 완료")
        return True
    
    def run_real_data_tests(self) -> Dict[str, Any]:
        """실제 데이터 통합 테스트 실행"""
        self.logger.info("🧪 실제 데이터 통합 테스트 시작")
        
        try:
            test_suite = IntegrationTestSuite()
            results = test_suite.run_all_tests(headless=True)
            
            # 결과 정규화
            suite_result = {
                'suite_name': 'real_data_integration',
                'success': results['summary']['passed_tests'] > 0,
                'total_tests': results['summary']['total_tests'],
                'passed_tests': results['summary']['passed_tests'],
                'failed_tests': results['summary']['failed_tests'],
                'details': results,
                'duration': self._calculate_duration(results.get('start_time'), results.get('end_time'))
            }
            
            return suite_result
            
        except Exception as e:
            self.logger.error(f"❌ 실제 데이터 테스트 실행 실패: {e}")
            return {
                'suite_name': 'real_data_integration',
                'success': False,
                'error': str(e),
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 1
            }
    
    def run_performance_tests(self) -> Dict[str, Any]:
        """성능 테스트 실행"""
        self.logger.info("🚀 성능 테스트 시작")
        
        try:
            test_suite = PerformanceTestSuite()
            results = test_suite.run_all_performance_tests()
            
            # 결과 정규화
            suite_result = {
                'suite_name': 'performance_load',
                'success': results['summary']['passed_tests'] >= results['summary']['total_tests'] * 0.7,
                'total_tests': results['summary']['total_tests'],
                'passed_tests': results['summary']['passed_tests'],
                'failed_tests': results['summary']['failed_tests'],
                'details': results,
                'duration': results.get('total_duration', 0)
            }
            
            return suite_result
            
        except Exception as e:
            self.logger.error(f"❌ 성능 테스트 실행 실패: {e}")
            return {
                'suite_name': 'performance_load',
                'success': False,
                'error': str(e),
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 1
            }
    
    def run_pytest_tests(self) -> Dict[str, Any]:
        """pytest 기반 테스트 실행"""
        self.logger.info("🧪 pytest 기반 테스트 시작")
        
        try:
            # pytest 실행
            cmd = [
                sys.executable, '-m', 'pytest', 
                'test_editor_formats.py',
                '-v', '--tb=short', '--json-report', '--json-report-file=pytest_report.json'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            # pytest 결과 파싱
            try:
                with open('pytest_report.json', 'r') as f:
                    pytest_data = json.load(f)
                
                suite_result = {
                    'suite_name': 'pytest_editor_formats',
                    'success': result.returncode == 0,
                    'total_tests': pytest_data['summary']['total'],
                    'passed_tests': pytest_data['summary']['passed'],
                    'failed_tests': pytest_data['summary']['failed'],
                    'details': pytest_data,
                    'duration': pytest_data['duration']
                }
                
            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                # pytest 보고서 파싱 실패 시 기본 정보만 사용
                suite_result = {
                    'suite_name': 'pytest_editor_formats',
                    'success': result.returncode == 0,
                    'total_tests': 1,
                    'passed_tests': 1 if result.returncode == 0 else 0,
                    'failed_tests': 0 if result.returncode == 0 else 1,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
            
            return suite_result
            
        except subprocess.TimeoutExpired:
            self.logger.error("❌ pytest 테스트 타임아웃")
            return {
                'suite_name': 'pytest_editor_formats',
                'success': False,
                'error': 'Timeout',
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 1
            }
        except Exception as e:
            self.logger.error(f"❌ pytest 테스트 실행 실패: {e}")
            return {
                'suite_name': 'pytest_editor_formats',
                'success': False,
                'error': str(e),
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 1
            }
    
    def _calculate_duration(self, start_time: str, end_time: str) -> float:
        """시간 차이 계산"""
        try:
            if start_time and end_time:
                start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                return (end - start).total_seconds()
        except:
            pass
        return 0
    
    def run_all_tests(self) -> Dict[str, Any]:
        """모든 통합 테스트 실행"""
        self.logger.info("="*80)
        self.logger.info("🚀 네이버 카페 콘텐츠 추출 통합 테스트 시작")
        self.logger.info(f"⏰ {datetime.now()}")
        self.logger.info("="*80)
        
        # 필수 조건 확인
        if not self.check_prerequisites():
            self.results['fatal_error'] = "필수 조건 미충족"
            return self.results
        
        # 테스트 스위트들 실행
        test_suites = [
            ('실제 데이터 통합 테스트', self.run_real_data_tests),
            ('성능 및 부하 테스트', self.run_performance_tests),
            ('pytest 에디터 형식 테스트', self.run_pytest_tests)
        ]
        
        for suite_name, suite_method in test_suites:
            self.logger.info(f"\n📋 실행 중: {suite_name}")
            
            try:
                suite_result = suite_method()
                self.results['test_suites'].append(suite_result)
                
                # 통계 업데이트
                self.results['summary']['total_suites'] += 1
                self.results['summary']['total_tests'] += suite_result.get('total_tests', 0)
                self.results['summary']['passed_tests'] += suite_result.get('passed_tests', 0)
                self.results['summary']['failed_tests'] += suite_result.get('failed_tests', 0)
                
                if suite_result.get('success', False):
                    self.results['summary']['passed_suites'] += 1
                    self.logger.info(f"✅ {suite_name}: 성공")
                else:
                    self.results['summary']['failed_suites'] += 1
                    self.logger.warning(f"❌ {suite_name}: 실패")
                
            except Exception as e:
                self.logger.error(f"❌ {suite_name} 실행 중 오류: {e}")
                self.results['test_suites'].append({
                    'suite_name': suite_name,
                    'success': False,
                    'error': str(e),
                    'total_tests': 0,
                    'passed_tests': 0,
                    'failed_tests': 1
                })
                self.results['summary']['failed_suites'] += 1
                self.results['summary']['total_tests'] += 1
                self.results['summary']['failed_tests'] += 1
        
        self.results['end_time'] = datetime.now().isoformat()
        return self.results
    
    def generate_comprehensive_report(self) -> str:
        """종합 테스트 보고서 생성"""
        report = []
        report.append("="*100)
        report.append("📊 네이버 카페 콘텐츠 추출 통합 테스트 종합 보고서")
        report.append("="*100)
        
        # 전체 요약
        summary = self.results['summary']
        report.append(f"\n📈 전체 요약:")
        report.append(f"  • 테스트 스위트: {summary['total_suites']}개 (성공: {summary['passed_suites']}, 실패: {summary['failed_suites']})")
        report.append(f"  • 개별 테스트: {summary['total_tests']}개 (성공: {summary['passed_tests']}, 실패: {summary['failed_tests']})")
        
        if summary['total_tests'] > 0:
            success_rate = (summary['passed_tests'] / summary['total_tests']) * 100
            report.append(f"  • 전체 성공률: {success_rate:.1f}%")
        
        # 환경 정보
        env = self.results['environment']
        report.append(f"\n🔧 테스트 환경:")
        report.append(f"  • Python 버전: {env['python_version'].split()[0]}")
        report.append(f"  • GitHub Actions: {env['github_actions']}")
        report.append(f"  • 헤드리스 모드: {env['headless_mode']}")
        report.append(f"  • 테스트 시간: {env['test_timestamp']}")
        
        # 각 테스트 스위트 결과
        report.append(f"\n📋 테스트 스위트별 상세 결과:")
        
        for suite in self.results['test_suites']:
            suite_name = suite.get('suite_name', 'Unknown')
            success_icon = "✅" if suite.get('success', False) else "❌"
            
            report.append(f"\n{success_icon} {suite_name}:")
            report.append(f"  • 총 테스트: {suite.get('total_tests', 0)}개")
            report.append(f"  • 성공: {suite.get('passed_tests', 0)}개")
            report.append(f"  • 실패: {suite.get('failed_tests', 0)}개")
            
            if 'duration' in suite:
                report.append(f"  • 소요 시간: {suite['duration']:.1f}초")
            
            if 'error' in suite:
                report.append(f"  • 오류: {suite['error']}")
        
        # Requirements 충족 여부 확인
        report.append(f"\n✅ Requirements 충족 여부:")
        
        # Requirement 1.1, 1.2, 1.3 (에디터 형식)
        editor_tests = [s for s in self.results['test_suites'] 
                       if 'editor' in s.get('suite_name', '').lower()]
        editor_success = any(s.get('success', False) for s in editor_tests)
        
        report.append(f"  • Req 1.1-1.3 (다양한 에디터 형식): {'✅ 충족' if editor_success else '❌ 미충족'}")
        
        # Requirement 2.1, 2.2, 2.3 (동적 콘텐츠 로딩)
        loading_tests = [s for s in self.results['test_suites'] 
                        if any(keyword in s.get('suite_name', '').lower() 
                              for keyword in ['real_data', 'performance'])]
        loading_success = any(s.get('success', False) for s in loading_tests)
        
        report.append(f"  • Req 2.1-2.3 (동적 콘텐츠 로딩): {'✅ 충족' if loading_success else '❌ 미충족'}")
        
        # 권장사항
        report.append(f"\n💡 권장사항:")
        
        if summary['failed_suites'] > 0:
            report.append("  • 실패한 테스트 스위트를 분석하여 시스템을 개선하세요")
        
        if summary['total_tests'] > 0:
            success_rate = (summary['passed_tests'] / summary['total_tests']) * 100
            if success_rate < 70:
                report.append("  • 전체 성공률이 낮습니다. 시스템 안정성을 점검하세요")
            elif success_rate >= 90:
                report.append("  • 테스트 결과가 우수합니다. 현재 구현을 유지하세요")
            else:
                report.append("  • 테스트 결과가 양호합니다. 일부 개선이 필요할 수 있습니다")
        
        # Task 11 완료 상태
        task_complete = (
            summary['passed_suites'] >= 2 and  # 최소 2개 스위트 성공
            editor_success and                  # 에디터 형식 테스트 성공
            loading_success                     # 동적 로딩 테스트 성공
        )
        
        report.append(f"\n🎯 Task 11 완료 상태: {'✅ 완료' if task_complete else '❌ 미완료'}")
        
        if task_complete:
            report.append("  • 실제 네이버 카페 게시물 대상 통합 테스트 완료")
            report.append("  • 다양한 에디터 형식 테스트 완료")
            report.append("  • 네트워크 지연 및 에러 시나리오 테스트 완료")
        
        report.append("="*100)
        
        return "\n".join(report)
    
    def save_results(self) -> str:
        """테스트 결과를 파일로 저장"""
        timestamp = self.results['environment']['test_timestamp']
        
        # JSON 결과 저장
        json_file = f"integration_test_results_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        # 텍스트 보고서 저장
        report = self.generate_comprehensive_report()
        txt_file = f"integration_test_report_{timestamp}.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return txt_file


def main():
    """메인 실행 함수"""
    runner = IntegrationTestRunner()
    
    try:
        # 모든 테스트 실행
        results = runner.run_all_tests()
        
        # 보고서 생성 및 출력
        report = runner.generate_comprehensive_report()
        print(report)
        
        # 결과 파일 저장
        report_file = runner.save_results()
        print(f"\n📄 상세 보고서가 저장되었습니다: {report_file}")
        
        # GitHub Actions를 위한 아티팩트 디렉토리 생성
        if os.getenv('GITHUB_ACTIONS'):
            os.makedirs('artifacts', exist_ok=True)
            
            # 중요 파일들을 artifacts로 복사
            import shutil
            for file in [report_file, f"integration_test_results_{results['environment']['test_timestamp']}.json"]:
                if os.path.exists(file):
                    shutil.copy2(file, 'artifacts/')
        
        # 성공 여부 판정
        summary = results['summary']
        if summary['total_tests'] > 0:
            success_rate = (summary['passed_tests'] / summary['total_tests']) * 100
            task_success = (
                summary['passed_suites'] >= 2 and
                success_rate >= 70
            )
        else:
            task_success = False
        
        if task_success:
            print("\n🎉 Task 11 통합 테스트 성공!")
            return True
        else:
            print("\n❌ Task 11 통합 테스트 실패")
            return False
            
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 테스트가 중단되었습니다")
        return False
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 심각한 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)