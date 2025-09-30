"""SONiC Agent Evaluation Framework.

Dataclass-based evaluation framework for testing SONiC analysis agents with LLM judge evaluation.
"""

import json
import datetime
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

import pytest

try:
    from strands import Agent

    STRANDS_AVAILABLE = True
except ImportError:
    Agent = None
    STRANDS_AVAILABLE = False


@dataclass
class EvaluationCase:
    """Single evaluation test case from YAML definition."""

    id: str
    query: str
    category: str
    expected: Optional[str] = None
    expected_tools: List[str] = field(default_factory=list)
    expected_patterns: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationResult:
    """Result of single evaluation with LLM judge scoring."""

    test_id: str
    category: str
    query: str
    expected: str
    actual: str
    response_time: float
    used_tools: List[str]
    llm_judge_score: int
    llm_judge_feedback: str
    passed: bool
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)


@dataclass
class EvaluationMetrics:
    """Aggregated metrics from evaluation run."""

    total_tests: int
    passed_tests: int
    failed_tests: int
    avg_response_time: float
    max_response_time: float
    avg_llm_score: float
    min_llm_score: int
    max_llm_score: int
    categories: Dict[str, int]
    tool_usage_accuracy: float


@dataclass
class EvalAgentTester:
    """SONiC Agent Evaluation Framework with real LLM agents."""

    agent: Agent
    evaluator_agent: Agent
    test_cases: List[EvaluationCase]
    tech_support_file: Path
    output_dir: Path = field(default_factory=lambda: Path("test/evaluation/results"))

    def __post_init__(self):
        """Initialize output directory."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def evaluate_agent(self, agent_name: str) -> List[EvaluationResult]:
        """Run full evaluation suite with LLM judge and metrics collection."""
        results = []
        start_time = datetime.datetime.now()

        print(f"🔍 Starting evaluation of {agent_name} at {start_time}")
        print(f"📁 Tech support file: {self.tech_support_file.name}")
        print(f"🧪 Test cases: {len(self.test_cases)}")

        for case in self.test_cases:
            case_start = datetime.datetime.now()

            # Execute agent query with tech support file context
            full_query = f"{case.query}\n\nTech support file: {self.tech_support_file}"
            response = self.agent(full_query)
            case_duration = (datetime.datetime.now() - case_start).total_seconds()

            # Extract tool usage from response
            used_tools = self._extract_used_tools(response)

            # LLM Judge evaluation with tool usage information
            judge_score, judge_feedback = self._llm_judge_evaluate(case, response, used_tools)

            # Determine pass/fail based on LLM score and tool usage
            passed = self._determine_pass_fail(case, judge_score, used_tools)

            result = EvaluationResult(
                test_id=case.id,
                category=case.category,
                query=case.query,
                expected=case.expected or "",
                actual=str(response),
                response_time=case_duration,
                used_tools=used_tools,
                llm_judge_score=judge_score,
                llm_judge_feedback=judge_feedback,
                passed=passed,
            )

            results.append(result)

            # Progress indicator
            status_icon = "✅" if passed else "❌"
            print(f"{status_icon} {case.id}: Score {judge_score}/5 ({case_duration:.1f}s)")

        total_duration = (datetime.datetime.now() - start_time).total_seconds()
        print(f"🏁 Evaluation completed in {total_duration:.1f} seconds")

        # Save results
        self._save_results(results, agent_name)

        return results

    def _extract_used_tools(self, response) -> List[str]:
        """Extract tools used from real Strands agent response metrics."""
        used_tools = []

        # Strands AgentResult has metrics with tool_metrics dictionary
        if hasattr(response, "metrics") and hasattr(response.metrics, "tool_metrics"):
            for tool_name, tool_metric in response.metrics.tool_metrics.items():
                if hasattr(tool_metric, "call_count") and tool_metric.call_count > 0:
                    used_tools.append(tool_name)

        return used_tools

    def _llm_judge_evaluate(
        self, case: EvaluationCase, response, used_tools: Optional[List[str]] = None
    ) -> Tuple[int, str]:
        """Use real LLM judge agent to evaluate response quality for SONiC analysis."""
        # Extract tool usage if not provided
        if used_tools is None:
            used_tools = self._extract_used_tools(response)

        eval_prompt = f"""
        You are evaluating a SONiC network analysis agent response.

        Query: {case.query}
        Expected: {case.expected or "Not specified"}
        Expected Tools: {case.expected_tools}
        Expected Patterns: {case.expected_patterns}

        ACTUAL TOOLS USED: {used_tools}

        Agent Response:
        {response}

        CRITICAL EVALUATION RULES:
        1. ONLY evaluate what was explicitly requested in the Query
        2. DO NOT penalize for missing information that was NOT requested
        3. DO NOT penalize for lack of descriptions, organization, or details if NOT requested
        4. If query says "Do not show me anything else", respect this constraint
        5. DO NOT suggest improvements for things that were NOT requested
        6. DO NOT penalize for using additional necessary tools (e.g., extract before list)

        Evaluate based on:
        1. Accuracy - factual correctness for what was requested
        2. Relevance - addresses ONLY the specific query, nothing more/less
        3. Completeness - complete for what was requested (not what could be added)
        4. Tool Usage - appropriate use of MCP tools (ACTUAL TOOLS USED: {used_tools})

        Important:
        - The agent DID use the tools listed above. Do not claim "no tool usage".
        - If the query has constraints like "Do not show me anything else", the response should be scored highly for respecting those constraints.
        - Do not suggest adding descriptions, organization, or details if they weren't requested.

        Provide a score from 1-5 (where 5 is excellent) and brief feedback.

        Format your response as:
        SCORE: X
        FEEDBACK: Your detailed explanation here
        """

        evaluation = self.evaluator_agent(eval_prompt)
        return self._parse_judge_response(str(evaluation))

    def _parse_judge_response(self, evaluation_text: str) -> Tuple[int, str]:
        """Parse LLM judge response to extract score and feedback."""
        try:
            # Extract score using regex
            score_match = re.search(r"SCORE:\s*(\d+)", evaluation_text)
            score = int(score_match.group(1)) if score_match else 3

            # Extract feedback
            feedback_match = re.search(r"FEEDBACK:\s*(.+)", evaluation_text, re.DOTALL)
            feedback = feedback_match.group(1).strip() if feedback_match else evaluation_text

            # Ensure score is within valid range
            score = max(1, min(5, score))

            return score, feedback

        except Exception as e:
            print(f"⚠️  Error parsing judge response: {e}")
            return 3, f"Error parsing evaluation: {evaluation_text}"

    def _determine_pass_fail(self, case: EvaluationCase, judge_score: int, used_tools: List[str]) -> bool:
        """Determine if evaluation case passes based on score and tool usage."""
        # Base pass threshold on LLM judge score
        score_pass = judge_score >= 4  # Score of 4 or 5 is considered passing

        # Check tool usage if expected tools are specified
        tool_pass = True
        if case.expected_tools:
            # ALL expected tools must be used (strict requirement)
            expected_tools_used = all(tool in used_tools for tool in case.expected_tools)
            tool_pass = expected_tools_used

            # Debug output for tool validation
            missing_tools = [tool for tool in case.expected_tools if tool not in used_tools]
            if missing_tools:
                print(f"⚠️  Missing required tools: {missing_tools}")

        return score_pass and tool_pass

    def _save_results(self, results: List[EvaluationResult], agent_name: str):
        """Save evaluation results to JSON and CSV files."""
        import csv

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save detailed results as JSON
        json_path = self.output_dir / f"{agent_name}_{timestamp}.json"
        results_data = [
            {
                "test_id": r.test_id,
                "category": r.category,
                "query": r.query,
                "expected": r.expected,
                "actual": r.actual,
                "response_time": r.response_time,
                "used_tools": r.used_tools,
                "llm_judge_score": r.llm_judge_score,
                "llm_judge_feedback": r.llm_judge_feedback,
                "passed": r.passed,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in results
        ]

        with open(json_path, "w") as f:
            json.dump(results_data, f, indent=2)

        # Save summary as CSV using built-in csv module
        csv_path = self.output_dir / f"{agent_name}_{timestamp}_summary.csv"
        csv_data = [
            {
                "test_id": r.test_id,
                "category": r.category,
                "passed": r.passed,
                "llm_score": r.llm_judge_score,
                "response_time": r.response_time,
                "tools_used": len(r.used_tools),
            }
            for r in results
        ]

        with open(csv_path, "w", newline="") as csvfile:
            if csv_data:
                fieldnames = csv_data[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_data)

        print("📊 Results saved:")
        print(f"  JSON: {json_path}")
        print(f"  CSV:  {csv_path}")

    def calculate_metrics(self, results: List[EvaluationResult]) -> EvaluationMetrics:
        """Calculate aggregated metrics from evaluation results using basic Python."""
        if not results:
            # Return empty metrics if no results
            return EvaluationMetrics(
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                avg_response_time=0.0,
                max_response_time=0.0,
                avg_llm_score=0.0,
                min_llm_score=0,
                max_llm_score=0,
                categories={},
                tool_usage_accuracy=0.0,
            )

        passed_tests = sum(1 for r in results if r.passed)
        failed_tests = len(results) - passed_tests

        # Calculate response time metrics
        response_times = [r.response_time for r in results]
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)

        # Calculate LLM score metrics
        llm_scores = [r.llm_judge_score for r in results]
        avg_llm_score = sum(llm_scores) / len(llm_scores)
        min_llm_score = min(llm_scores)
        max_llm_score = max(llm_scores)

        # Calculate categories
        categories = {}
        for r in results:
            categories[r.category] = categories.get(r.category, 0) + 1

        # Calculate tool usage accuracy
        tool_cases = [r for r in results if r.used_tools]
        tool_accuracy = len(tool_cases) / len(results) if results else 0.0

        return EvaluationMetrics(
            total_tests=len(results),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            avg_response_time=avg_response_time,
            max_response_time=max_response_time,
            avg_llm_score=avg_llm_score,
            min_llm_score=min_llm_score,
            max_llm_score=max_llm_score,
            categories=categories,
            tool_usage_accuracy=tool_accuracy,
        )

    def generate_report(self, results: List[EvaluationResult], agent_name: str) -> str:
        """Generate comprehensive evaluation report."""
        metrics = self.calculate_metrics(results)

        report = f"""
# SONiC Agent Evaluation Report: {agent_name}

## 📊 Summary
- **Total Tests**: {metrics.total_tests}
- **Passed**: {metrics.passed_tests} ({metrics.passed_tests / metrics.total_tests * 100:.1f}%)
- **Failed**: {metrics.failed_tests} ({metrics.failed_tests / metrics.total_tests * 100:.1f}%)

## ⏱️ Performance
- **Average Response Time**: {metrics.avg_response_time:.2f}s
- **Max Response Time**: {metrics.max_response_time:.2f}s

## 🎯 Quality Scores (LLM Judge)
- **Average Score**: {metrics.avg_llm_score:.1f}/5
- **Score Range**: {metrics.min_llm_score}-{metrics.max_llm_score}

## 🛠️ Tool Usage
- **Tool Usage Rate**: {metrics.tool_usage_accuracy:.1%}

## 📂 Test Categories
"""
        for category, count in metrics.categories.items():
            category_results = [r for r in results if r.category == category]
            category_passed = sum(1 for r in category_results if r.passed)
            report += f"- **{category}**: {category_passed}/{count} passed ({category_passed / count * 100:.1f}%)\n"

        # Failed tests details
        failed_tests = [r for r in results if not r.passed]
        if failed_tests:
            report += "\n## ❌ Failed Tests\n"
            for result in failed_tests:
                report += f"- **{result.test_id}**: Score {result.llm_judge_score}/5 - {result.llm_judge_feedback}\n"

        return report

    def pytest_assert_results(self, results: List[EvaluationResult]):
        """Convert evaluation results to pytest assertions."""
        metrics = self.calculate_metrics(results)
        failed_cases = [r for r in results if not r.passed]

        # Print summary for test output
        print("\n📊 Evaluation Summary:")
        print(
            f"   Passed: {metrics.passed_tests}/{metrics.total_tests} ({metrics.passed_tests / metrics.total_tests * 100:.1f}%)"
        )
        print(f"   Avg Score: {metrics.avg_llm_score:.1f}/5")
        print(f"   Avg Response: {metrics.avg_response_time:.1f}s")

        if failed_cases:
            failure_details = []
            for case in failed_cases:
                tools_info = f"Tools: {case.used_tools}" if case.used_tools else "No tools used"
                failure_details.append(
                    f"❌ {case.test_id} ({case.category}): Score {case.llm_judge_score}/5 - {tools_info}"
                )

            failure_summary = "\n".join(failure_details)
            pytest.fail(f"\n🚨 Evaluation failed for {len(failed_cases)} test cases:\n\n{failure_summary}")

        print(f"✅ All {len(results)} evaluation cases passed!")
