"""Evaluation framework data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
import json
import csv
from pathlib import Path


@dataclass
class TestCase:
    """Individual test case from YAML configuration."""

    id: str
    category: str
    query: str
    expected: str
    expected_tools: List[str] = field(default_factory=list)
    expected_patterns: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    tech_support_file: Optional[str] = None


@dataclass
class TestResult:
    """Result of a single test execution."""

    test_id: str
    category: str
    query: str
    response: str
    tools_used: List[str]
    response_time: float
    score: Optional[int] = None
    feedback: Optional[str] = None
    passed: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    expected_tools: List[str] = field(default_factory=list)
    expected_patterns: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "test_id": self.test_id,
            "category": self.category,
            "query": self.query,
            "response": self.response,
            "tools_used": self.tools_used,
            "response_time": self.response_time,
            "score": self.score,
            "feedback": self.feedback,
            "passed": self.passed,
            "timestamp": self.timestamp.isoformat(),
            "expected_tools": self.expected_tools,
            "expected_patterns": self.expected_patterns,
            "context": self.context,
        }


@dataclass
class EvaluationResults:
    """Complete results for an evaluation run."""

    test_name: str
    results: List[TestResult]
    timestamp: datetime = field(default_factory=datetime.now)
    total_tests: int = field(init=False)
    passed_tests: int = field(init=False)
    pass_rate: float = field(init=False)
    avg_response_time: float = field(init=False)
    avg_score: Optional[float] = field(init=False)

    def __post_init__(self):
        """Calculate summary statistics."""
        self.total_tests = len(self.results)
        self.passed_tests = sum(1 for r in self.results if r.passed)
        self.pass_rate = self.passed_tests / self.total_tests if self.total_tests > 0 else 0.0
        self.avg_response_time = (
            sum(r.response_time for r in self.results) / self.total_tests if self.total_tests > 0 else 0.0
        )

        scores = [r.score for r in self.results if r.score is not None]
        self.avg_score = sum(scores) / len(scores) if scores else None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "test_name": self.test_name,
            "timestamp": self.timestamp.isoformat(),
            "summary": {
                "total_tests": self.total_tests,
                "passed_tests": self.passed_tests,
                "pass_rate": self.pass_rate,
                "avg_response_time": self.avg_response_time,
                "avg_score": self.avg_score,
            },
            "results": [r.to_dict() for r in self.results],
        }

    def save_json(self, output_dir: Path) -> Path:
        """Save results to JSON file."""
        timestamp_str = self.timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"{self.test_name}_{timestamp_str}.json"
        file_path = output_dir / filename

        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

        return file_path

    def save_csv_summary(self, output_dir: Path) -> Path:
        """Save summary results to CSV file."""
        timestamp_str = self.timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"{self.test_name}_{timestamp_str}_summary.csv"
        file_path = output_dir / filename

        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "test_id",
                    "category",
                    "passed",
                    "score",
                    "response_time",
                    "tools_used_count",
                    "expected_tools_match",
                    "pattern_match",
                ]
            )

            for result in self.results:
                expected_tools_match = all(tool in result.tools_used for tool in result.expected_tools)
                pattern_match = any(pattern.lower() in result.response.lower() for pattern in result.expected_patterns)

                writer.writerow(
                    [
                        result.test_id,
                        result.category,
                        result.passed,
                        result.score,
                        result.response_time,
                        len(result.tools_used),
                        expected_tools_match,
                        pattern_match,
                    ]
                )

        return file_path


@dataclass
class EvalAgentTester:
    """Main evaluation framework for testing SONiC agents."""

    test_cases: List[TestCase]
    mcp_client: Any
    llm_judge: Optional[Any] = None
    results_dir: Path = field(default_factory=lambda: Path("test/evaluation/results"))

    def evaluate_agent(self, test_name: str) -> EvaluationResults:
        """Run all test cases and return results."""
        results = []

        for test_case in self.test_cases:
            print(f"\nRunning test: {test_case.id}")
            print(f"Query: {test_case.query}")

            start_time = datetime.now()

            try:
                # Execute test via MCP client
                response, tools_used = self._execute_test_case(test_case)

                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds()

                # Evaluate with LLM judge if available
                score, feedback = self._evaluate_response(test_case, response, tools_used)

                # Determine pass/fail
                passed = self._determine_pass_fail(test_case, response, tools_used, score)

                result = TestResult(
                    test_id=test_case.id,
                    category=test_case.category,
                    query=test_case.query,
                    response=response,
                    tools_used=tools_used,
                    response_time=response_time,
                    score=score,
                    feedback=feedback,
                    passed=passed,
                    expected_tools=test_case.expected_tools,
                    expected_patterns=test_case.expected_patterns,
                    context=test_case.context,
                )

                results.append(result)
                print(f"✓ Test {test_case.id}: {'PASS' if passed else 'FAIL'} (Score: {score})")

            except Exception as e:
                print(f"✗ Test {test_case.id}: ERROR - {e}")
                result = TestResult(
                    test_id=test_case.id,
                    category=test_case.category,
                    query=test_case.query,
                    response=f"ERROR: {str(e)}",
                    tools_used=[],
                    response_time=0.0,
                    passed=False,
                    expected_tools=test_case.expected_tools,
                    expected_patterns=test_case.expected_patterns,
                    context=test_case.context,
                )
                results.append(result)

        return EvaluationResults(test_name=test_name, results=results)

    def _execute_test_case(self, test_case: TestCase) -> tuple[str, List[str]]:
        """Execute a single test case via MCP client."""
        # This would integrate with actual MCP client
        # For now, return mock response
        return "Mock response for testing", ["extract_tech_support_file"]

    def _evaluate_response(
        self, test_case: TestCase, response: str, tools_used: List[str]
    ) -> tuple[Optional[int], Optional[str]]:
        """Evaluate response using LLM judge."""
        if not self.llm_judge:
            return None, None

        # LLM judge evaluation would go here
        # For now, return basic scoring
        score = 4 if len(tools_used) > 0 else 2
        feedback = "Basic evaluation - tools used correctly" if score >= 4 else "Tools not used properly"
        return score, feedback

    def _determine_pass_fail(
        self, test_case: TestCase, response: str, tools_used: List[str], score: Optional[int]
    ) -> bool:
        """Determine if test passed based on multiple criteria."""
        # Check tool usage
        if test_case.expected_tools:
            tools_match = all(tool in tools_used for tool in test_case.expected_tools)
            if not tools_match:
                return False

        # Check response patterns
        if test_case.expected_patterns:
            pattern_match = any(pattern.lower() in response.lower() for pattern in test_case.expected_patterns)
            if not pattern_match:
                return False

        # Check LLM judge score
        if score is not None and score < 4:
            return False

        return True

    def generate_report(self, results: EvaluationResults, test_name: str) -> str:
        """Generate detailed text report."""
        report = f"""
=== SONiC Agent Evaluation Report ===
Test Suite: {test_name}
Timestamp: {results.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY:
- Total Tests: {results.total_tests}
- Passed: {results.passed_tests}
- Failed: {results.total_tests - results.passed_tests}
- Pass Rate: {results.pass_rate:.1%}
- Average Response Time: {results.avg_response_time:.2f}s
"""
        avg_score_str = f"{results.avg_score:.1f}/5.0" if results.avg_score is not None else "N/A"
        report += f"""
- Average Score: {avg_score_str}

DETAILED RESULTS:
"""

        for result in results.results:
            status = "PASS" if result.passed else "FAIL"
            report += f"""
[{status}] {result.test_id} ({result.category})
  Query: {result.query}
  Response Time: {result.response_time:.2f}s
  Tools Used: {', '.join(result.tools_used)}
"""
            score_str = f"{result.score}/5.0" if result.score is not None else "N/A"
            report += f"""
  Score: {score_str}
  Expected Tools: {', '.join(result.expected_tools)}
"""

            if not result.passed:
                report += f"  Failure Reason: {result.feedback or 'Criteria not met'}\n"

        return report

    def pytest_assert_results(self, results: EvaluationResults) -> None:
        """Assert all tests passed for pytest integration."""
        failed_tests = [r for r in results.results if not r.passed]

        if failed_tests:
            failure_details = []
            for result in failed_tests:
                failure_details.append(f"  - {result.test_id}: {result.feedback or 'Criteria not met'}")

            failure_msg = f"""
{len(failed_tests)}/{results.total_tests} tests failed:
{chr(10).join(failure_details)}

Pass rate: {results.pass_rate:.1%}
"""
            raise AssertionError(failure_msg.strip())
