#!/usr/bin/env python3
"""
성능 및 부하 테스트
네트워크 지연, 동시 요청, 메모리 사용량 등을 테스트
"""

import time
import threading
import psutil
import gc
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from dataclasses import dataclass
from statistics import mean, median, stdev

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from content_extractor import ContentExtractor
from content_extraction_models import ExtractionConfig

logging.basicConfig(level=logging.INFO)


@dataclass
class PerformanceMetrics:
    """성능 메트릭 데이터 클래스"""
    extraction_time: float
    memory_usage_mb: float
    success: bool
    content_length: int
    extraction_method: str
    error_message: str = None


class PerformanceTestSuite:
    """성능 테스트 스위트"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.test_urls = [
            "https://cafe.naver.com/f-e/cafes/18786605/articles/1941841?boardtype=L&menuid=105",
            # 추가 테스트 URL들을 여기에 추가
        ]
    
    def create_driver(self, headless: bool = True) -> tuple:
        """테스트용 드라이버 생성"""
        options = Options()
        
        if headless:
            options.add_argument('--headless=new')
        
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        # 메모리 사용량 최적화
        options.add_argument('--memory-pressure-off')
        options.add_argument('--max_old_space_size=4096')
        
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 30)
        
        return driver, wait
    
    def measure_memory_usage(self) -> float:
        """현재 메모리 사용량 측정 (MB)"""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def single_extraction_test(self, url: str, config: ExtractionConfig) -> PerformanceMetrics:
        """단일 추출 성능 테스트"""
        driver, wait = self.create_driver()
        
        try:
            # 네이버 로그인 (간소화)
            driver.get('https://nid.naver.com/nidlogin.login')
            time.sleep(2)
            
            # 메모리 사용량 측정 시작
            memory_before = self.measure_memory_usage()
            
            # ContentExtractor 생성
            extractor = ContentExtractor(driver, wait, config)
            
            # 추출 시간 측정
            start_time = time.time()
            result = extractor.extract_content(url)
            extraction_time = time.time() - start_time
            
            # 메모리 사용량 측정 종료
            memory_after = self.measure_memory_usage()
            memory_usage = memory_after - memory_before
            
            return PerformanceMetrics(
                extraction_time=extraction_time,
                memory_usage_mb=memory_usage,
                success=result.success,
                content_length=len(result.content),
                extraction_method=result.extraction_method.value,
                error_message=result.error_message
            )
            
        except Exception as e:
            return PerformanceMetrics(
                extraction_time=0,
                memory_usage_mb=0,
                success=False,
                content_length=0,
                extraction_method="error",
                error_message=str(e)
            )
        
        finally:
            driver.quit()
            gc.collect()  # 가비지 컬렉션 강제 실행
    
    def test_extraction_speed(self, iterations: int = 10) -> Dict[str, Any]:
        """추출 속도 테스트 (Requirements: 2.1, 2.2, 2.3)"""
        self.logger.info(f"🚀 추출 속도 테스트 시작 ({iterations}회 반복)")
        
        config = ExtractionConfig(timeout_seconds=30)
        metrics = []
        
        for i in range(iterations):
            self.logger.info(f"📊 테스트 {i+1}/{iterations}")
            
            for url in self.test_urls:
                metric = self.single_extraction_test(url, config)
                metrics.append(metric)
                
                self.logger.info(f"  ⏱️ 시간: {metric.extraction_time:.2f}초, "
                               f"메모리: {metric.memory_usage_mb:.1f}MB, "
                               f"성공: {metric.success}")
                
                time.sleep(1)  # 테스트 간 간격
        
        # 통계 계산
        successful_metrics = [m for m in metrics if m.success]
        
        if not successful_metrics:
            return {
                'test_name': 'extraction_speed',
                'status': 'FAILED',
                'error': '모든 추출 실패'
            }
        
        extraction_times = [m.extraction_time for m in successful_metrics]
        memory_usages = [m.memory_usage_mb for m in successful_metrics]
        
        return {
            'test_name': 'extraction_speed',
            'iterations': iterations,
            'successful_extractions': len(successful_metrics),
            'failed_extractions': len(metrics) - len(successful_metrics),
            'success_rate': len(successful_metrics) / len(metrics) * 100,
            'extraction_time_stats': {
                'mean': mean(extraction_times),
                'median': median(extraction_times),
                'min': min(extraction_times),
                'max': max(extraction_times),
                'std_dev': stdev(extraction_times) if len(extraction_times) > 1 else 0
            },
            'memory_usage_stats': {
                'mean': mean(memory_usages),
                'median': median(memory_usages),
                'min': min(memory_usages),
                'max': max(memory_usages),
                'std_dev': stdev(memory_usages) if len(memory_usages) > 1 else 0
            }
        }
    
    def test_timeout_scenarios(self) -> Dict[str, Any]:
        """다양한 타임아웃 시나리오 테스트"""
        self.logger.info("⏰ 타임아웃 시나리오 테스트 시작")
        
        timeout_scenarios = [
            {'name': '매우 짧은 타임아웃', 'timeout': 5, 'expected_failures': True},
            {'name': '짧은 타임아웃', 'timeout': 15, 'expected_failures': False},
            {'name': '일반 타임아웃', 'timeout': 30, 'expected_failures': False},
            {'name': '긴 타임아웃', 'timeout': 60, 'expected_failures': False}
        ]
        
        results = []
        
        for scenario in timeout_scenarios:
            self.logger.info(f"⏱️ 시나리오: {scenario['name']} ({scenario['timeout']}초)")
            
            config = ExtractionConfig(timeout_seconds=scenario['timeout'])
            
            # 각 시나리오당 3회 테스트
            scenario_metrics = []
            for i in range(3):
                metric = self.single_extraction_test(self.test_urls[0], config)
                scenario_metrics.append(metric)
            
            successful = [m for m in scenario_metrics if m.success]
            success_rate = len(successful) / len(scenario_metrics) * 100
            
            avg_time = mean([m.extraction_time for m in successful]) if successful else 0
            
            scenario_result = {
                'name': scenario['name'],
                'timeout_seconds': scenario['timeout'],
                'success_rate': success_rate,
                'average_time': avg_time,
                'expected_failures': scenario['expected_failures'],
                'meets_expectation': (
                    (scenario['expected_failures'] and success_rate < 50) or
                    (not scenario['expected_failures'] and success_rate >= 70)
                )
            }
            
            results.append(scenario_result)
            
            self.logger.info(f"  📊 성공률: {success_rate:.1f}%, 평균 시간: {avg_time:.2f}초")
        
        return {
            'test_name': 'timeout_scenarios',
            'scenarios': results,
            'overall_success': all(r['meets_expectation'] for r in results)
        }
    
    def test_concurrent_extractions(self, max_workers: int = 3) -> Dict[str, Any]:
        """동시 추출 테스트"""
        self.logger.info(f"🔄 동시 추출 테스트 시작 (워커: {max_workers}개)")
        
        def worker_task(worker_id: int) -> Dict[str, Any]:
            """워커 태스크"""
            self.logger.info(f"👷 워커 {worker_id} 시작")
            
            config = ExtractionConfig(timeout_seconds=45)  # 동시 실행 시 여유있게
            
            start_time = time.time()
            metric = self.single_extraction_test(self.test_urls[0], config)
            total_time = time.time() - start_time
            
            return {
                'worker_id': worker_id,
                'total_time': total_time,
                'extraction_time': metric.extraction_time,
                'success': metric.success,
                'memory_usage': metric.memory_usage_mb,
                'error': metric.error_message
            }
        
        # 동시 실행
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(worker_task, i) for i in range(max_workers)]
            worker_results = []
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    worker_results.append(result)
                    self.logger.info(f"✅ 워커 {result['worker_id']} 완료: {result['success']}")
                except Exception as e:
                    self.logger.error(f"❌ 워커 실행 오류: {e}")
                    worker_results.append({
                        'worker_id': -1,
                        'success': False,
                        'error': str(e)
                    })
        
        total_concurrent_time = time.time() - start_time
        
        successful_workers = [r for r in worker_results if r['success']]
        success_rate = len(successful_workers) / len(worker_results) * 100
        
        return {
            'test_name': 'concurrent_extractions',
            'max_workers': max_workers,
            'total_concurrent_time': total_concurrent_time,
            'success_rate': success_rate,
            'successful_workers': len(successful_workers),
            'failed_workers': len(worker_results) - len(successful_workers),
            'worker_results': worker_results,
            'average_extraction_time': mean([r['extraction_time'] for r in successful_workers]) if successful_workers else 0
        }
    
    def test_memory_leak_detection(self, iterations: int = 20) -> Dict[str, Any]:
        """메모리 누수 감지 테스트"""
        self.logger.info(f"🧠 메모리 누수 감지 테스트 시작 ({iterations}회)")
        
        config = ExtractionConfig(timeout_seconds=20)
        memory_snapshots = []
        
        # 초기 메모리 상태
        initial_memory = self.measure_memory_usage()
        memory_snapshots.append(initial_memory)
        
        for i in range(iterations):
            self.logger.info(f"🔍 메모리 테스트 {i+1}/{iterations}")
            
            # 추출 실행
            metric = self.single_extraction_test(self.test_urls[0], config)
            
            # 메모리 측정
            current_memory = self.measure_memory_usage()
            memory_snapshots.append(current_memory)
            
            self.logger.info(f"  📊 메모리: {current_memory:.1f}MB (+{current_memory - initial_memory:.1f}MB)")
            
            # 강제 가비지 컬렉션
            gc.collect()
            time.sleep(1)
        
        # 메모리 증가 분석
        memory_increases = [memory_snapshots[i] - memory_snapshots[i-1] 
                           for i in range(1, len(memory_snapshots))]
        
        total_increase = memory_snapshots[-1] - memory_snapshots[0]
        average_increase = mean(memory_increases)
        
        # 메모리 누수 판정 (임계값: 100MB 이상 증가)
        has_memory_leak = total_increase > 100
        
        return {
            'test_name': 'memory_leak_detection',
            'iterations': iterations,
            'initial_memory_mb': initial_memory,
            'final_memory_mb': memory_snapshots[-1],
            'total_increase_mb': total_increase,
            'average_increase_mb': average_increase,
            'max_increase_mb': max(memory_increases),
            'has_memory_leak': has_memory_leak,
            'memory_snapshots': memory_snapshots
        }
    
    def test_network_conditions(self) -> Dict[str, Any]:
        """다양한 네트워크 조건 테스트"""
        self.logger.info("🌐 네트워크 조건 테스트 시작")
        
        # 네트워크 조건별 테스트는 실제 환경에서만 의미가 있으므로
        # 여기서는 타임아웃 조정을 통한 간접 테스트
        
        network_scenarios = [
            {'name': '빠른 네트워크', 'timeout': 15, 'expected_success_rate': 90},
            {'name': '보통 네트워크', 'timeout': 30, 'expected_success_rate': 95},
            {'name': '느린 네트워크', 'timeout': 60, 'expected_success_rate': 80}
        ]
        
        results = []
        
        for scenario in network_scenarios:
            self.logger.info(f"📡 네트워크 시나리오: {scenario['name']}")
            
            config = ExtractionConfig(timeout_seconds=scenario['timeout'])
            
            # 시나리오당 5회 테스트
            scenario_results = []
            for i in range(5):
                metric = self.single_extraction_test(self.test_urls[0], config)
                scenario_results.append(metric)
            
            successful = [r for r in scenario_results if r.success]
            success_rate = len(successful) / len(scenario_results) * 100
            avg_time = mean([r.extraction_time for r in successful]) if successful else 0
            
            scenario_result = {
                'name': scenario['name'],
                'timeout': scenario['timeout'],
                'success_rate': success_rate,
                'average_time': avg_time,
                'expected_success_rate': scenario['expected_success_rate'],
                'meets_expectation': success_rate >= scenario['expected_success_rate'] * 0.8  # 80% 허용
            }
            
            results.append(scenario_result)
            
            self.logger.info(f"  📊 성공률: {success_rate:.1f}% (기대: {scenario['expected_success_rate']}%)")
        
        return {
            'test_name': 'network_conditions',
            'scenarios': results,
            'overall_success': all(r['meets_expectation'] for r in results)
        }
    
    def run_all_performance_tests(self) -> Dict[str, Any]:
        """모든 성능 테스트 실행"""
        self.logger.info("="*60)
        self.logger.info("🚀 성능 테스트 스위트 시작")
        self.logger.info("="*60)
        
        results = {
            'start_time': time.time(),
            'tests': [],
            'summary': {
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0
            }
        }
        
        # 실행할 테스트들
        test_methods = [
            ('extraction_speed', lambda: self.test_extraction_speed(5)),
            ('timeout_scenarios', self.test_timeout_scenarios),
            ('concurrent_extractions', lambda: self.test_concurrent_extractions(2)),
            ('memory_leak_detection', lambda: self.test_memory_leak_detection(10)),
            ('network_conditions', self.test_network_conditions)
        ]
        
        for test_name, test_method in test_methods:
            try:
                self.logger.info(f"\n🧪 실행 중: {test_name}")
                test_result = test_method()
                
                # 성공/실패 판정
                if 'overall_success' in test_result:
                    success = test_result['overall_success']
                elif 'success_rate' in test_result:
                    success = test_result['success_rate'] >= 70
                elif 'has_memory_leak' in test_result:
                    success = not test_result['has_memory_leak']
                else:
                    success = test_result.get('status') != 'FAILED'
                
                test_result['success'] = success
                results['tests'].append(test_result)
                
                if success:
                    results['summary']['passed_tests'] += 1
                    self.logger.info(f"✅ {test_name}: 성공")
                else:
                    results['summary']['failed_tests'] += 1
                    self.logger.warning(f"❌ {test_name}: 실패")
                
                results['summary']['total_tests'] += 1
                
            except Exception as e:
                self.logger.error(f"❌ {test_name}: 예외 발생 - {e}")
                results['tests'].append({
                    'test_name': test_name,
                    'success': False,
                    'error': str(e)
                })
                results['summary']['failed_tests'] += 1
                results['summary']['total_tests'] += 1
        
        results['end_time'] = time.time()
        results['total_duration'] = results['end_time'] - results['start_time']
        
        return results
    
    def generate_performance_report(self, results: Dict[str, Any]) -> str:
        """성능 테스트 보고서 생성"""
        report = []
        report.append("="*80)
        report.append("📊 네이버 카페 콘텐츠 추출 성능 테스트 보고서")
        report.append("="*80)
        
        # 요약
        summary = results['summary']
        report.append(f"\n📈 테스트 요약:")
        report.append(f"  • 총 테스트: {summary['total_tests']}개")
        report.append(f"  • 성공: {summary['passed_tests']}개")
        report.append(f"  • 실패: {summary['failed_tests']}개")
        report.append(f"  • 전체 소요 시간: {results['total_duration']:.1f}초")
        
        # 각 테스트 상세 결과
        for test in results['tests']:
            test_name = test.get('test_name', 'Unknown')
            report.append(f"\n📋 {test_name}:")
            
            if test_name == 'extraction_speed':
                stats = test.get('extraction_time_stats', {})
                report.append(f"  • 평균 추출 시간: {stats.get('mean', 0):.2f}초")
                report.append(f"  • 최소/최대 시간: {stats.get('min', 0):.2f}초 / {stats.get('max', 0):.2f}초")
                report.append(f"  • 성공률: {test.get('success_rate', 0):.1f}%")
            
            elif test_name == 'concurrent_extractions':
                report.append(f"  • 동시 워커: {test.get('max_workers', 0)}개")
                report.append(f"  • 전체 소요 시간: {test.get('total_concurrent_time', 0):.2f}초")
                report.append(f"  • 성공률: {test.get('success_rate', 0):.1f}%")
            
            elif test_name == 'memory_leak_detection':
                report.append(f"  • 메모리 증가: {test.get('total_increase_mb', 0):.1f}MB")
                report.append(f"  • 메모리 누수: {'있음' if test.get('has_memory_leak', False) else '없음'}")
            
            status = "✅ 성공" if test.get('success', False) else "❌ 실패"
            report.append(f"  • 결과: {status}")
        
        report.append("="*80)
        
        return "\n".join(report)


def main():
    """메인 실행 함수"""
    test_suite = PerformanceTestSuite()
    results = test_suite.run_all_performance_tests()
    
    # 보고서 생성 및 출력
    report = test_suite.generate_performance_report(results)
    print(report)
    
    # 결과 파일 저장
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    report_file = f"performance_test_report_{timestamp}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📄 성능 테스트 보고서가 저장되었습니다: {report_file}")
    
    # 성공률 기준으로 종료 코드 결정
    success_rate = (results['summary']['passed_tests'] / 
                   max(results['summary']['total_tests'], 1)) * 100
    
    return success_rate >= 70


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)