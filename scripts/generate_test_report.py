"""
테스트 보고서 생성 스크립트
"""

import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path


def parse_junit_xml(xml_file):
    """JUnit XML 파일 파싱"""
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        test_results = {
            'total_tests': 0,
            'failures': 0,
            'errors': 0,
            'skipped': 0,
            'time': 0.0,
            'test_suites': []
        }
        
        for testsuite in root.findall('testsuite'):
            suite_name = testsuite.get('name', 'Unknown Suite')
            suite_tests = int(testsuite.get('tests', 0))
            suite_failures = int(testsuite.get('failures', 0))
            suite_errors = int(testsuite.get('errors', 0))
            suite_skipped = int(testsuite.get('skipped', 0))
            suite_time = float(testsuite.get('time', 0))
            
            test_cases = []
            for testcase in testsuite.findall('testcase'):
                case_name = testcase.get('name', 'Unknown Test')
                case_class = testcase.get('classname', 'Unknown Class')
                case_time = float(testcase.get('time', 0))
                
                failure = testcase.find('failure')
                error = testcase.find('error')
                
                case_result = {
                    'name': case_name,
                    'class': case_class,
                    'time': case_time,
                    'status': 'passed'
                }
                
                if failure is not None:
                    case_result['status'] = 'failed'
                    case_result['failure'] = {
                        'message': failure.get('message', ''),
                        'type': failure.get('type', '')
                    }
                
                if error is not None:
                    case_result['status'] = 'error'
                    case_result['error'] = {
                        'message': error.get('message', ''),
                        'type': error.get('type', '')
                    }
                
                test_cases.append(case_result)
            
            test_results['test_suites'].append({
                'name': suite_name,
                'tests': suite_tests,
                'failures': suite_failures,
                'errors': suite_errors,
                'skipped': suite_skipped,
                'time': suite_time,
                'test_cases': test_cases
            })
            
            test_results['total_tests'] += suite_tests
            test_results['failures'] += suite_failures
            test_results['errors'] += suite_errors
            test_results['skipped'] += suite_skipped
            test_results['time'] += suite_time
        
        return test_results
    
    except Exception as e:
        print(f"Error parsing JUnit XML {xml_file}: {str(e)}")
        return None


def parse_coverage_xml(xml_file):
    """커버리지 XML 파일 파싱"""
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        coverage_data = {
            'line_rate': 0.0,
            'branch_rate': 0.0,
            'complexity_rate': 0.0,
            'packages': []
        }
        
        for package in root.findall('package'):
            package_name = package.get('name', 'Unknown Package')
            line_rate = float(package.get('line-rate', 0))
            branch_rate = float(package.get('branch-rate', 0))
            complexity_rate = float(package.get('complexity-rate', 0))
            
            classes = []
            for cls in package.findall('class'):
                class_name = cls.get('name', 'Unknown Class')
                class_line_rate = float(cls.get('line-rate', 0))
                class_branch_rate = float(cls.get('branch-rate', 0))
                
                methods = []
                for method in cls.findall('method'):
                    method_name = method.get('name', 'Unknown Method')
                    method_line_rate = float(method.get('line-rate', 0))
                    method_branch_rate = float(method.get('branch-rate', 0))
                    method_complexity = float(method.get('complexity', 0))
                    
                    methods.append({
                        'name': method_name,
                        'line_rate': method_line_rate,
                        'branch_rate': method_branch_rate,
                        'complexity': method_complexity
                    })
                
                classes.append({
                    'name': class_name,
                    'line_rate': class_line_rate,
                    'branch_rate': class_branch_rate,
                    'methods': methods
                })
            
            coverage_data['packages'].append({
                'name': package_name,
                'line_rate': line_rate,
                'branch_rate': branch_rate,
                'complexity_rate': complexity_rate,
                'classes': classes
            })
        
        # 전체 평균 계산
        if coverage_data['packages']:
            total_line_rate = sum(p['line_rate'] for p in coverage_data['packages']) / len(coverage_data['packages'])
            total_branch_rate = sum(p['branch_rate'] for p in coverage_data['packages']) / len(coverage_data['packages'])
            total_complexity_rate = sum(p['complexity_rate'] for p in coverage_data['packages']) / len(coverage_data['packages'])
            
            coverage_data['line_rate'] = total_line_rate
            coverage_data['branch_rate'] = total_branch_rate
            coverage_data['complexity_rate'] = total_complexity_rate
        
        return coverage_data
    
    except Exception as e:
        print(f"Error parsing coverage XML {xml_file}: {str(e)}")
        return None


def generate_test_summary(test_results, coverage_data):
    """테스트 요약 생성"""
    summary = {
        'timestamp': datetime.utcnow().isoformat(),
        'test_results': test_results,
        'coverage_data': coverage_data,
        'overall_status': 'success'
    }
    
    # 전체 상태 결정
    if test_results:
        failure_rate = (test_results['failures'] + test_results['errors']) / test_results['total_tests'] * 100
        if failure_rate > 5:  # 5% 이상 실패
            summary['overall_status'] = 'failed'
        elif failure_rate > 0:  # 실패가 있는 경우
            summary['overall_status'] = 'partial'
    
    if coverage_data:
        if coverage_data['line_rate'] < 80:  # 80% 미만 커버리지
            if summary['overall_status'] == 'success':
                summary['overall_status'] = 'partial'
            elif summary['overall_status'] == 'partial':
                summary['overall_status'] = 'failed'
    
    return summary


def generate_html_report(summary, output_file):
    """HTML 보고서 생성"""
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>InsiteChart Test Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #eee;
        }}
        .status-success {{
            color: #28a745;
            font-size: 24px;
            font-weight: bold;
        }}
        .status-partial {{
            color: #ffc107;
            font-size: 24px;
            font-weight: bold;
        }}
        .status-failed {{
            color: #dc3545;
            font-size: 24px;
            font-weight: bold;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .summary-item {{
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 5px;
            border-left: 4px solid #007bff;
        }}
        .summary-item h3 {{
            margin: 0 0 10px 0;
            color: #007bff;
        }}
        .summary-item p {{
            margin: 0;
            font-size: 18px;
            font-weight: bold;
        }}
        .test-details {{
            margin-bottom: 30px;
        }}
        .test-suite {{
            margin-bottom: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
            overflow: hidden;
        }}
        .suite-header {{
            background-color: #007bff;
            color: white;
            padding: 10px;
            cursor: pointer;
        }}
        .suite-content {{
            padding: 15px;
            display: none;
        }}
        .suite-header:hover {{
            background-color: #0056b3;
        }}
        .test-case {{
            padding: 10px;
            border-bottom: 1px solid #eee;
        }}
        .test-case:last-child {{
            border-bottom: none;
        }}
        .test-passed {{
            background-color: #d4edda;
        }}
        .test-failed {{
            background-color: #f8d7da;
        }}
        .test-error {{
            background-color: #f5c6cb;
        }}
        .coverage-details {{
            margin-bottom: 30px;
        }}
        .coverage-item {{
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 5px;
            border-left: 4px solid #28a745;
            margin-bottom: 10px;
        }}
        .coverage-item h3 {{
            margin: 0 0 10px 0;
            color: #28a745;
        }}
        .coverage-item p {{
            margin: 0;
            font-size: 16px;
        }}
        .coverage-bar {{
            width: 100%;
            height: 20px;
            background-color: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin-top: 10px;
        }}
        .coverage-fill {{
            height: 100%;
            background-color: #28a745;
            transition: width 0.3s ease;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #eee;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>InsiteChart Test Report</h1>
            <p>Generated on {summary['timestamp']}</p>
            <div class="status-{summary['overall_status']}">
                Overall Status: {summary['overall_status'].upper()}
            </div>
        </div>
        
        <div class="summary-grid">
            <div class="summary-item">
                <h3>Test Results</h3>
                <p>Total Tests: {summary['test_results']['total_tests']}</p>
                <p>Passed: {summary['test_results']['total_tests'] - summary['test_results']['failures'] - summary['test_results']['errors']}</p>
                <p>Failed: {summary['test_results']['failures']}</p>
                <p>Errors: {summary['test_results']['errors']}</p>
                <p>Time: {summary['test_results']['time']:.2f}s</p>
            </div>
            <div class="summary-item">
                <h3>Coverage</h3>
                <p>Line Coverage: {summary['coverage_data']['line_rate']:.1f}%</p>
                <p>Branch Coverage: {summary['coverage_data']['branch_rate']:.1f}%</p>
                <p>Complexity Coverage: {summary['coverage_data']['complexity_rate']:.1f}%</p>
            </div>
        </div>
        
        <div class="test-details">
            <h2>Test Suite Details</h2>
    """
    
    # 테스트 스위트 상세 정보 추가
    for suite in summary['test_results']['test_suites']:
        html_content += f"""
            <div class="test-suite">
                <div class="suite-header" onclick="toggleSuite('{suite['name']}')">
                    <h3>{suite['name']}</h3>
                    <p>Tests: {suite['tests']} | Failed: {suite['failures']} | Time: {suite['time']:.2f}s</p>
                </div>
                <div class="suite-content" id="{suite['name']}">
        """
        
        # 테스트 케이스 상세 정보 (최대 10개만 표시)
        for i, case in enumerate(suite['test_cases'][:10]):
            status_class = case['status']
            html_content += f"""
                    <div class="test-case test-{status_class}">
                        <strong>{case['name']}</strong> ({case['class']})
                        <br>Status: {case['status']}
                        <br>Time: {case['time']:.3f}s
                    </div>
            """
        
        if len(suite['test_cases']) > 10:
            html_content += f"""
                    <p>... and {len(suite['test_cases']) - 10} more test cases</p>
            """
        
        html_content += """
                </div>
            </div>
        """
    
    # 커버리지 상세 정보 추가
    html_content += """
        </div>
        
        <div class="coverage-details">
            <h2>Coverage Details</h2>
    """
    
    for package in summary['coverage_data']['packages']:
        html_content += f"""
            <div class="coverage-item">
                <h3>{package['name']}</h3>
                <p>Line Coverage: {package['line_rate']:.1f}%</p>
                <p>Branch Coverage: {package['branch_rate']:.1f}%</p>
                <div class="coverage-bar">
                    <div class="coverage-fill" style="width: {package['line_rate']}%"></div>
                </div>
            </div>
        """
    
    html_content += """
        </div>
        
        <script>
            function toggleSuite(suiteName) {{
                const content = document.getElementById(suiteName);
                if (content.style.display === 'none') {{
                    content.style.display = 'block';
                }} else {{
                    content.style.display = 'none';
                }}
            }}
        </script>
        
        <div class="footer">
            <p>Report generated by InsiteChart Test System</p>
        </div>
    </div>
</body>
</html>
    """
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)


def generate_json_report(summary, output_file):
    """JSON 보고서 생성"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)


def generate_csv_report(test_results, output_file):
    """CSV 보고서 생성"""
    import csv
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Suite', 'Test Case', 'Class', 'Status', 'Time', 'Failure Message'])
        
        for suite in test_results['test_suites']:
            for case in suite['test_cases']:
                failure_msg = ''
                if 'failure' in case:
                    failure_msg = case['failure']['message']
                elif 'error' in case:
                    failure_msg = case['error']['message']
                
                writer.writerow([
                    suite['name'],
                    case['name'],
                    case['class'],
                    case['status'],
                    case['time'],
                    failure_msg
                ])


def main():
    """메인 함수"""
    reports_dir = Path('reports')
    reports_dir.mkdir(exist_ok=True)
    
    # JUnit XML 파일 찾기
    junit_files = list(reports_dir.glob('**/*-test-results.xml'))
    coverage_files = list(reports_dir.glob('**/coverage.xml'))
    
    if not junit_files:
        print("No JUnit XML files found")
        return
    
    # 테스트 결과 집계
    all_test_results = {
        'total_tests': 0,
        'failures': 0,
        'errors': 0,
        'skipped': 0,
        'time': 0.0,
        'test_suites': []
    }
    
    for junit_file in junit_files:
        test_results = parse_junit_xml(junit_file)
        if test_results:
            all_test_results['total_tests'] += test_results['total_tests']
            all_test_results['failures'] += test_results['failures']
            all_test_results['errors'] += test_results['errors']
            all_test_results['skipped'] += test_results['skipped']
            all_test_results['time'] += test_results['time']
            all_test_results['test_suites'].extend(test_results['test_suites'])
    
    # 커버리지 데이터 집계
    all_coverage_data = {
        'line_rate': 0.0,
        'branch_rate': 0.0,
        'complexity_rate': 0.0,
        'packages': []
    }
    
    for coverage_file in coverage_files:
        coverage_data = parse_coverage_xml(coverage_file)
        if coverage_data:
            all_coverage_data['packages'].extend(coverage_data['packages'])
    
    # 전체 평균 계산
    if all_coverage_data['packages']:
        all_coverage_data['line_rate'] = sum(p['line_rate'] for p in all_coverage_data['packages']) / len(all_coverage_data['packages'])
        all_coverage_data['branch_rate'] = sum(p['branch_rate'] for p in all_coverage_data['packages']) / len(all_coverage_data['packages'])
        all_coverage_data['complexity_rate'] = sum(p['complexity_rate'] for p in all_coverage_data['packages']) / len(all_coverage_data['packages'])
    
    # 보고서 요약 생성
    summary = generate_test_summary(all_test_results, all_coverage_data)
    
    # 다양한 형식으로 보고서 생성
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    generate_html_report(summary, f'reports/test_report_{timestamp}.html')
    generate_json_report(summary, f'reports/test_report_{timestamp}.json')
    generate_csv_report(all_test_results, f'reports/test_results_{timestamp}.csv')
    
    # 요약 정보 출력
    print(f"Test report generated:")
    print(f"  - Total tests: {all_test_results['total_tests']}")
    print(f"  - Failures: {all_test_results['failures']}")
    print(f"  - Errors: {all_test_results['errors']}")
    print(f"  - Success rate: {((all_test_results['total_tests'] - all_test_results['failures'] - all_test_results['errors']) / all_test_results['total_tests'] * 100):.1f}%")
    print(f"  - Line coverage: {all_coverage_data['line_rate']:.1f}%")
    print(f"  - Branch coverage: {all_coverage_data['branch_rate']:.1f}%")
    print(f"  - Overall status: {summary['overall_status']}")
    print(f"  - HTML report: reports/test_report_{timestamp}.html")
    print(f"  - JSON report: reports/test_report_{timestamp}.json")
    print(f"  - CSV report: reports/test_results_{timestamp}.csv")


if __name__ == '__main__':
    main()