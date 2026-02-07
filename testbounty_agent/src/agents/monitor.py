"""
Test Monitoring Agent - Analyzes test coverage, execution quality, and stability
Provides continuous monitoring and recommendations for test improvements
"""

import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict
import statistics


class TestMonitor:
    """
    Monitors test execution quality and provides insights on:
    - Test coverage across modules
    - Pass/fail rates and trends
    - Common failure patterns
    - Missing test scenarios
    - Test stability metrics
    """

    def __init__(self, plans_file: str = "test_plans.json", runs_file: str = "runs.json"):
        self.plans_file = plans_file
        self.runs_file = runs_file
        self.plans = self._load_json(plans_file)
        self.runs = self._load_json(runs_file)

    def _load_json(self, file_path: str) -> Dict:
        """Load JSON file or return empty dict"""
        if not os.path.exists(file_path):
            return {}
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except:
            return {}

    def analyze_all(self, plan_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Comprehensive analysis of all test aspects
        """
        if plan_id:
            plan_ids = [plan_id]
        else:
            plan_ids = list(self.plans.keys())

        if not plan_ids:
            return {
                "status": "error",
                "message": "No test plans found",
                "recommendations": ["Create a test plan by exploring an application"]
            }

        # Analyze the most recent plan
        latest_plan_id = plan_ids[-1]
        plan = self.plans[latest_plan_id]

        # Get runs for this plan
        plan_runs = self._get_plan_runs(latest_plan_id)

        analysis = {
            "plan_id": latest_plan_id,
            "url": plan.get("url"),
            "timestamp": datetime.now().isoformat(),
            "coverage_analysis": self._analyze_coverage(plan),
            "execution_quality": self._analyze_execution_quality(plan, plan_runs),
            "failure_patterns": self._analyze_failure_patterns(plan_runs),
            "stability_metrics": self._analyze_stability(plan_runs),
            "missing_scenarios": self._identify_missing_scenarios(plan),
            "recommendations": []
        }

        # Generate recommendations
        analysis["recommendations"] = self._generate_recommendations(analysis)

        return analysis

    def _get_plan_runs(self, plan_id: str) -> List[Dict]:
        """Get all runs for a specific plan"""
        runs = []
        for run_id, run in self.runs.items():
            if run.get("plan_id") == plan_id and run.get("type") == "scenario_run":
                runs.append(run)
        return runs

    def _analyze_coverage(self, plan: Dict) -> Dict[str, Any]:
        """Analyze test coverage across modules and scenarios"""
        test_plan = plan.get("test_plan", {})
        modules = test_plan.get("modules", {})
        app_map = plan.get("app_map", {})

        coverage = {
            "total_pages": app_map.get("total_pages", 0),
            "total_scenarios": test_plan.get("total_scenarios", 0),
            "modules_covered": len(modules),
            "module_breakdown": {},
            "coverage_gaps": []
        }

        # Analyze each module
        for module_name, module_data in modules.items():
            scenarios = module_data.get("scenarios", [])
            coverage["module_breakdown"][module_name] = {
                "scenario_count": len(scenarios),
                "scenario_types": self._count_scenario_types(scenarios),
                "priority_distribution": self._count_priorities(scenarios)
            }

        # Identify coverage gaps
        pages = app_map.get("pages", [])
        tested_paths = set()
        for module_data in modules.values():
            for scenario in module_data.get("scenarios", []):
                for step in scenario.get("steps", []):
                    if step.get("action") == "navigate":
                        tested_paths.add(step.get("target", ""))

        untested_pages = []
        for page in pages:
            if page.get("url") not in tested_paths:
                untested_pages.append({
                    "url": page.get("url"),
                    "type": page.get("type"),
                    "title": page.get("title")
                })

        coverage["coverage_gaps"] = untested_pages
        coverage["pages_tested"] = len(tested_paths)
        coverage["pages_untested"] = len(untested_pages)
        coverage["coverage_percentage"] = round(
            (len(tested_paths) / max(coverage["total_pages"], 1)) * 100, 2
        )

        return coverage

    def _analyze_execution_quality(self, plan: Dict, runs: List[Dict]) -> Dict[str, Any]:
        """Analyze how well tests are executing"""
        if not runs:
            return {
                "status": "no_runs",
                "message": "No test runs found for this plan"
            }

        latest_run = runs[-1]
        scenarios = latest_run.get("scenarios", [])

        if not scenarios:
            return {
                "status": "no_scenarios",
                "message": "No scenarios in latest run"
            }

        total = len(scenarios)
        passed = sum(1 for s in scenarios if s.get("status") == "passed")
        failed = sum(1 for s in scenarios if s.get("status") == "failed")
        skipped = sum(1 for s in scenarios if s.get("status") == "skipped")

        quality = {
            "latest_run": {
                "run_id": latest_run.get("id"),
                "status": latest_run.get("status"),
                "total_scenarios": total,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "pass_rate": round((passed / max(total, 1)) * 100, 2),
                "completion_rate": round(((passed + failed) / max(total, 1)) * 100, 2)
            },
            "trends": self._calculate_trends(runs)
        }

        return quality

    def _analyze_failure_patterns(self, runs: List[Dict]) -> Dict[str, Any]:
        """Identify common failure patterns"""
        if not runs:
            return {"patterns": [], "message": "No runs to analyze"}

        # Collect all failures
        failures = []
        error_messages = defaultdict(list)
        failing_modules = defaultdict(int)
        failing_actions = defaultdict(int)

        for run in runs:
            for scenario in run.get("scenarios", []):
                if scenario.get("status") == "failed":
                    error = scenario.get("error", "Unknown error")
                    module = scenario.get("module", "unknown")
                    scenario_id = scenario.get("id", "unknown")

                    failures.append({
                        "scenario_id": scenario_id,
                        "module": module,
                        "error": error
                    })

                    error_messages[error].append(scenario_id)
                    failing_modules[module] += 1

                    # Extract action type from error
                    if "Could not click" in error:
                        failing_actions["click"] += 1
                    elif "Could not find element" in error:
                        failing_actions["fill"] += 1
                    elif "timeout" in error.lower():
                        failing_actions["timeout"] += 1

        # Find most common error messages
        common_errors = sorted(
            error_messages.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:5]

        patterns = {
            "total_failures": len(failures),
            "most_common_errors": [
                {
                    "error": error,
                    "count": len(scenarios),
                    "affected_scenarios": scenarios
                }
                for error, scenarios in common_errors
            ],
            "failing_modules": dict(failing_modules),
            "failing_actions": dict(failing_actions),
            "insights": self._generate_failure_insights(
                error_messages, failing_modules, failing_actions
            )
        }

        return patterns

    def _analyze_stability(self, runs: List[Dict]) -> Dict[str, Any]:
        """Analyze test stability over multiple runs"""
        if len(runs) < 2:
            return {
                "status": "insufficient_data",
                "message": "Need at least 2 runs to analyze stability"
            }

        # Track scenario results across runs
        scenario_results = defaultdict(list)

        for run in runs:
            for scenario in run.get("scenarios", []):
                scenario_id = scenario.get("id")
                status = scenario.get("status")
                scenario_results[scenario_id].append(status)

        # Calculate stability metrics
        flaky_scenarios = []
        stable_failures = []
        stable_passes = []

        for scenario_id, results in scenario_results.items():
            unique_results = set(results)
            if len(unique_results) > 1:
                flaky_scenarios.append({
                    "scenario_id": scenario_id,
                    "results": results,
                    "pass_rate": round((results.count("passed") / len(results)) * 100, 2)
                })
            elif "failed" in unique_results:
                stable_failures.append(scenario_id)
            elif "passed" in unique_results:
                stable_passes.append(scenario_id)

        stability = {
            "total_runs": len(runs),
            "flaky_tests": {
                "count": len(flaky_scenarios),
                "scenarios": flaky_scenarios
            },
            "stable_failures": {
                "count": len(stable_failures),
                "scenarios": stable_failures
            },
            "stable_passes": {
                "count": len(stable_passes),
                "scenarios": stable_passes
            },
            "stability_score": round(
                ((len(stable_passes) + len(stable_failures)) /
                 max(len(scenario_results), 1)) * 100, 2
            )
        }

        return stability

    def _identify_missing_scenarios(self, plan: Dict) -> Dict[str, Any]:
        """Identify missing or inadequate test scenarios"""
        test_plan = plan.get("test_plan", {})
        modules = test_plan.get("modules", {})
        app_map = plan.get("app_map", {})

        missing = {
            "untested_pages": [],
            "insufficient_coverage": [],
            "missing_negative_tests": [],
            "missing_edge_cases": []
        }

        # Check for pages without tests
        pages = app_map.get("pages", [])
        for page in pages:
            page_type = page.get("type")
            page_url = page.get("url")

            # Check if page is tested
            tested = False
            for module_data in modules.values():
                for scenario in module_data.get("scenarios", []):
                    for step in scenario.get("steps", []):
                        if step.get("action") == "navigate" and step.get("target") == page_url:
                            tested = True
                            break
                    if tested:
                        break
                if tested:
                    break

            if not tested:
                missing["untested_pages"].append({
                    "url": page_url,
                    "type": page_type,
                    "title": page.get("title")
                })

        # Check for modules with insufficient test coverage
        for module_name, module_data in modules.items():
            scenarios = module_data.get("scenarios", [])

            # Count scenario types
            happy_paths = sum(1 for s in scenarios if s.get("type") == "happy_path")
            negative_tests = sum(1 for s in scenarios if s.get("type") in ["negative", "security", "edge_case"])

            if happy_paths > 0 and negative_tests < happy_paths:
                missing["insufficient_coverage"].append({
                    "module": module_name,
                    "happy_paths": happy_paths,
                    "negative_tests": negative_tests,
                    "recommendation": "Add more negative and edge case tests"
                })

            # Check for security module
            if module_name == "auth" and negative_tests < 3:
                missing["missing_negative_tests"].append({
                    "module": module_name,
                    "current_count": negative_tests,
                    "recommended_tests": [
                        "SQL Injection",
                        "XSS attacks",
                        "Session hijacking",
                        "Brute force protection"
                    ]
                })

        return missing

    def _count_scenario_types(self, scenarios: List[Dict]) -> Dict[str, int]:
        """Count scenarios by type"""
        types = defaultdict(int)
        for scenario in scenarios:
            types[scenario.get("type", "unknown")] += 1
        return dict(types)

    def _count_priorities(self, scenarios: List[Dict]) -> Dict[str, int]:
        """Count scenarios by priority"""
        priorities = defaultdict(int)
        for scenario in scenarios:
            priorities[scenario.get("priority", "medium")] += 1
        return dict(priorities)

    def _calculate_trends(self, runs: List[Dict]) -> Dict[str, Any]:
        """Calculate trends across multiple runs"""
        if len(runs) < 2:
            return {"message": "Need at least 2 runs for trend analysis"}

        pass_rates = []
        for run in runs[-5:]:  # Last 5 runs
            scenarios = run.get("scenarios", [])
            if scenarios:
                total = len(scenarios)
                passed = sum(1 for s in scenarios if s.get("status") == "passed")
                pass_rates.append((passed / total) * 100)

        if not pass_rates:
            return {"message": "No scenario data found"}

        return {
            "recent_pass_rates": [round(pr, 2) for pr in pass_rates],
            "average_pass_rate": round(statistics.mean(pass_rates), 2),
            "trend": "improving" if len(pass_rates) > 1 and pass_rates[-1] > pass_rates[0] else "declining" if len(pass_rates) > 1 and pass_rates[-1] < pass_rates[0] else "stable"
        }

    def _generate_failure_insights(
        self,
        error_messages: Dict[str, List[str]],
        failing_modules: Dict[str, int],
        failing_actions: Dict[str, int]
    ) -> List[str]:
        """Generate insights from failure patterns"""
        insights = []

        # Most common error
        if error_messages:
            most_common = max(error_messages.items(), key=lambda x: len(x[1]))
            insights.append(
                f"Most common error: '{most_common[0]}' affecting {len(most_common[1])} scenarios"
            )

        # Module with most failures
        if failing_modules:
            worst_module = max(failing_modules.items(), key=lambda x: x[1])
            insights.append(
                f"Module '{worst_module[0]}' has the most failures ({worst_module[1]})"
            )

        # Action type causing issues
        if failing_actions:
            problematic_action = max(failing_actions.items(), key=lambda x: x[1])
            insights.append(
                f"Action '{problematic_action[0]}' is the most problematic ({problematic_action[1]} failures)"
            )

        # Selector-related issues
        selector_errors = sum(
            len(scenarios) for error, scenarios in error_messages.items()
            if "Could not click" in error or "Could not find element" in error
        )
        if selector_errors > 0:
            insights.append(
                f"{selector_errors} failures related to element selectors - may need selector improvements"
            )

        return insights

    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Coverage recommendations
        coverage = analysis.get("coverage_analysis", {})
        coverage_pct = coverage.get("coverage_percentage", 0)
        if coverage_pct < 70:
            recommendations.append(
                f"LOW COVERAGE: Only {coverage_pct}% of pages are tested. Add tests for untested pages."
            )

        untested = coverage.get("pages_untested", 0)
        if untested > 0:
            recommendations.append(
                f"Found {untested} untested pages. Review coverage_gaps for details."
            )

        # Execution quality recommendations
        quality = analysis.get("execution_quality", {})
        latest = quality.get("latest_run", {})
        pass_rate = latest.get("pass_rate", 0)

        if pass_rate < 50:
            recommendations.append(
                f"CRITICAL: Pass rate is only {pass_rate}%. Investigate failure patterns urgently."
            )
        elif pass_rate < 80:
            recommendations.append(
                f"Pass rate is {pass_rate}%. Work on improving test reliability."
            )

        # Failure pattern recommendations
        patterns = analysis.get("failure_patterns", {})
        common_errors = patterns.get("most_common_errors", [])
        if common_errors:
            top_error = common_errors[0]
            if top_error["count"] >= 3:
                recommendations.append(
                    f"PATTERN DETECTED: '{top_error['error'][:50]}...' affects {top_error['count']} tests. Fix this systematically."
                )

        # Selector-specific recommendations
        for error in common_errors:
            if "Could not click" in error["error"] or "Could not find element" in error["error"]:
                recommendations.append(
                    "Selector issues detected. Consider improving selector strategy (use IDs, data-testid, or more specific classes)."
                )
                break

        # Stability recommendations
        stability = analysis.get("stability_metrics", {})
        flaky_count = stability.get("flaky_tests", {}).get("count", 0)
        if flaky_count > 0:
            recommendations.append(
                f"Found {flaky_count} flaky tests. Investigate timing issues, waits, or race conditions."
            )

        stability_score = stability.get("stability_score", 100)
        if stability_score < 80:
            recommendations.append(
                f"Test stability is {stability_score}%. Add explicit waits and improve element detection."
            )

        # Missing scenarios
        missing = analysis.get("missing_scenarios", {})
        insufficient = missing.get("insufficient_coverage", [])
        if insufficient:
            for item in insufficient:
                recommendations.append(
                    f"Module '{item['module']}' needs more negative tests ({item['negative_tests']}/{item['happy_paths']} ratio)"
                )

        if not recommendations:
            recommendations.append("Tests are in good shape! Keep monitoring for regressions.")

        return recommendations

    def print_report(self, analysis: Dict):
        """Print a formatted report"""
        print("\n" + "="*80)
        print("TEST MONITORING REPORT")
        print("="*80)
        print(f"Plan ID: {analysis['plan_id']}")
        print(f"URL: {analysis['url']}")
        print(f"Timestamp: {analysis['timestamp']}")
        print()

        # Coverage
        print("COVERAGE ANALYSIS")
        print("-"*80)
        coverage = analysis['coverage_analysis']
        print(f"Total Pages: {coverage['total_pages']}")
        print(f"Total Scenarios: {coverage['total_scenarios']}")
        print(f"Pages Tested: {coverage['pages_tested']} ({coverage['coverage_percentage']}%)")
        print(f"Pages Untested: {coverage['pages_untested']}")
        print()

        # Execution Quality
        print("EXECUTION QUALITY")
        print("-"*80)
        quality = analysis['execution_quality']
        if 'latest_run' in quality:
            latest = quality['latest_run']
            print(f"Latest Run: {latest['run_id']}")
            print(f"Total Scenarios: {latest['total_scenarios']}")
            print(f"Passed: {latest['passed']}")
            print(f"Failed: {latest['failed']}")
            print(f"Skipped: {latest['skipped']}")
            print(f"Pass Rate: {latest['pass_rate']}%")
        print()

        # Failure Patterns
        print("FAILURE PATTERNS")
        print("-"*80)
        patterns = analysis['failure_patterns']
        print(f"Total Failures: {patterns.get('total_failures', 0)}")
        if patterns.get('most_common_errors'):
            print("\nMost Common Errors:")
            for error_data in patterns['most_common_errors'][:3]:
                print(f"  - {error_data['error'][:60]}... ({error_data['count']} occurrences)")
        if patterns.get('insights'):
            print("\nInsights:")
            for insight in patterns['insights']:
                print(f"  • {insight}")
        print()

        # Stability
        print("STABILITY METRICS")
        print("-"*80)
        stability = analysis['stability_metrics']
        if 'total_runs' in stability:
            print(f"Total Runs Analyzed: {stability['total_runs']}")
            print(f"Stability Score: {stability.get('stability_score', 'N/A')}%")
            print(f"Stable Passes: {stability['stable_passes']['count']}")
            print(f"Stable Failures: {stability['stable_failures']['count']}")
            print(f"Flaky Tests: {stability['flaky_tests']['count']}")
        else:
            print(stability.get('message', 'No stability data'))
        print()

        # Recommendations
        print("RECOMMENDATIONS")
        print("-"*80)
        for i, rec in enumerate(analysis['recommendations'], 1):
            print(f"{i}. {rec}")
        print()
        print("="*80)


def monitor_tests(plan_id: Optional[str] = None, output_file: Optional[str] = None):
    """
    Run monitoring analysis and optionally save to file
    """
    monitor = TestMonitor()
    analysis = monitor.analyze_all(plan_id)

    # Print report
    monitor.print_report(analysis)

    # Save to file if requested
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2)
        print(f"\nDetailed analysis saved to: {output_file}")

    return analysis


if __name__ == "__main__":
    import sys
    plan_id = sys.argv[1] if len(sys.argv) > 1 else None
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    monitor_tests(plan_id, output_file)
