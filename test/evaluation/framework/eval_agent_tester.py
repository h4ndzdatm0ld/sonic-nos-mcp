"""SONiC Agent Evaluation Framework.

Dataclass-based evaluation framework for testing SONiC analysis agents with LLM judge evaluation.
"""

import json
import datetime
import logging
import re
import csv
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

import pytest
from strands import Agent

logger = logging.getLogger(__name__)


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
class HistoricalMetrics:
    """Historical aggregation of evaluation results across multiple runs."""

    test_id: str
    total_runs: int
    avg_score: float
    score_trend: List[float]  # Last 10 runs
    avg_response_time: float
    success_rate: float  # % of runs that passed
    score_std_dev: float
    last_run_date: datetime.datetime
    improvement_trend: str  # "improving", "stable", "declining"
    run_number: int  # Current run number for this test


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

        logger.info(f"Starting evaluation of {agent_name} at {start_time}")
        logger.info(f"Tech support file: {self.tech_support_file.name}")
        logger.info(f"Test cases: {len(self.test_cases)}")
        print(f"🔍 Starting evaluation of {agent_name} at {start_time}")
        print(f"📁 Tech support file: {self.tech_support_file.name}")
        print(f"🧪 Test cases: {len(self.test_cases)}")

        for case in self.test_cases:
            case_start = datetime.datetime.now()

            logger.debug(f"Executing agent query for case {case.id} with tech support file context")
            full_query = f"{case.query}\n\nTech support file: {self.tech_support_file}"
            response = self.agent(full_query)
            case_duration = (datetime.datetime.now() - case_start).total_seconds()

            logger.debug(f"Extracting tool usage from response for case {case.id}")
            used_tools = self._extract_used_tools(response)

            logger.debug(f"Running LLM judge evaluation for case {case.id} with tools: {used_tools}")
            judge_score, judge_feedback = self._llm_judge_evaluate(case, response, used_tools)

            logger.debug(f"Determining pass/fail status for case {case.id}: score={judge_score}, tools={used_tools}")
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

            logger.info(
                f"Case {case.id} completed: passed={passed}, score={judge_score}/5, duration={case_duration:.1f}s"
            )
            status_icon = "✅" if passed else "❌"
            print(f"{status_icon} {case.id}: Score {judge_score}/5 ({case_duration:.1f}s)")

        total_duration = (datetime.datetime.now() - start_time).total_seconds()
        logger.info(f"Evaluation completed in {total_duration:.1f} seconds")
        print(f"🏁 Evaluation completed in {total_duration:.1f} seconds")

        logger.info(f"Saving evaluation results for {agent_name}")
        self._save_results(results, agent_name)

        return results

    def _extract_used_tools(self, response) -> List[str]:
        """Extract tools used from real Strands agent response metrics."""
        used_tools = []

        logger.debug("Extracting tools from Strands agent response metrics")
        tool_metrics = response.metrics.tool_metrics

        for tool_name, tool_metric in tool_metrics.items():
            if tool_metric.call_count > 0:
                used_tools.append(tool_name)
                logger.debug(f"Found tool usage: {tool_name} (calls: {tool_metric.call_count})")

        logger.debug(f"Extracted {len(used_tools)} tools: {used_tools}")
        return used_tools

    def _llm_judge_evaluate(
        self, case: EvaluationCase, response, used_tools: Optional[List[str]] = None
    ) -> Tuple[int, str]:
        """Use real LLM judge agent to evaluate response quality for SONiC analysis."""
        logger.debug(f"Starting LLM judge evaluation for case {case.id}")
        if used_tools is None:
            logger.debug("Tool usage not provided, extracting from response")
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
            logger.debug("Parsing LLM judge response for score and feedback")
            score_match = re.search(r"SCORE:\s*(\d+)", evaluation_text)
            score = int(score_match.group(1)) if score_match else 3
            logger.debug(f"Extracted score: {score}")

            feedback_match = re.search(r"FEEDBACK:\s*(.+)", evaluation_text, re.DOTALL)
            feedback = feedback_match.group(1).strip() if feedback_match else evaluation_text

            logger.debug("Ensuring score is within valid range (1-5)")
            score = max(1, min(5, score))

            logger.debug(f"Final parsed result: score={score}, feedback_length={len(feedback)}")
            return score, feedback

        except Exception as e:
            logger.error(f"Error parsing judge response: {e}")
            print(f"⚠️  Error parsing judge response: {e}")
            return 3, f"Error parsing evaluation: {evaluation_text}"

    def _determine_pass_fail(self, case: EvaluationCase, judge_score: int, used_tools: List[str]) -> bool:
        """Determine if evaluation case passes based on score and tool usage."""
        logger.debug(f"Determining pass/fail for case {case.id}: score={judge_score}, tools={used_tools}")
        score_pass = judge_score >= 4
        logger.debug(f"Score pass threshold (>=4): {score_pass}")

        tool_pass = True
        if case.expected_tools:
            expected_tools_used = all(tool in used_tools for tool in case.expected_tools)
            tool_pass = expected_tools_used
            logger.debug(f"Tool validation - expected: {case.expected_tools}, used: {used_tools}, pass: {tool_pass}")

            missing_tools = [tool for tool in case.expected_tools if tool not in used_tools]
            if missing_tools:
                logger.warning(f"Missing required tools for case {case.id}: {missing_tools}")
                print(f"⚠️  Missing required tools: {missing_tools}")

        final_result = score_pass and tool_pass
        logger.debug(
            f"Final pass/fail result for case {case.id}: {final_result} (score_pass={score_pass}, tool_pass={tool_pass})"
        )
        return final_result

    def _save_results(self, results: List[EvaluationResult], agent_name: str):
        """Save evaluation results to JSON and CSV files."""
        import csv

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        logger.info(f"Saving detailed results as JSON for {len(results)} test cases")
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
        logger.debug(f"JSON results saved to: {json_path}")

        logger.info("Saving summary as CSV using built-in csv module")
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
        logger.debug(f"CSV summary saved to: {csv_path}")

        logger.info("Evaluation results saving completed successfully")
        print("📊 Results saved:")
        print(f"  JSON: {json_path}")
        print(f"  CSV:  {csv_path}")

    def calculate_metrics(self, results: List[EvaluationResult]) -> EvaluationMetrics:
        """Calculate aggregated metrics from evaluation results using basic Python."""
        logger.debug(f"Calculating metrics for {len(results)} evaluation results")

        if not results:
            logger.warning("No results provided, returning empty metrics")
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
        logger.debug(f"Pass/fail breakdown: {passed_tests} passed, {failed_tests} failed")

        logger.debug("Calculating response time metrics")
        response_times = [r.response_time for r in results]
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)

        logger.debug("Calculating LLM score metrics")
        llm_scores = [r.llm_judge_score for r in results]
        avg_llm_score = sum(llm_scores) / len(llm_scores)
        min_llm_score = min(llm_scores)
        max_llm_score = max(llm_scores)

        logger.debug("Calculating category distribution")
        categories: Dict[str, int] = {}
        for r in results:
            categories[r.category] = categories.get(r.category, 0) + 1

        logger.debug("Calculating tool usage accuracy")
        tool_cases = [r for r in results if r.used_tools]
        tool_accuracy = len(tool_cases) / len(results) if results else 0.0

        logger.debug(
            f"Metrics calculation completed: {passed_tests}/{len(results)} passed, avg_score={avg_llm_score:.1f}"
        )
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
        logger.info(f"Generating comprehensive evaluation report for {agent_name}")
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

        logger.debug("Adding failed tests details to report")
        failed_tests = [r for r in results if not r.passed]
        if failed_tests:
            logger.debug(f"Found {len(failed_tests)} failed tests to include in report")
            report += "\n## ❌ Failed Tests\n"
            for result in failed_tests:
                report += f"- **{result.test_id}**: Score {result.llm_judge_score}/5 - {result.llm_judge_feedback}\n"

        logger.debug(f"Report generation completed, report length: {len(report)} characters")
        return report

    def pytest_assert_results(self, results: List[EvaluationResult]):
        """Convert evaluation results to pytest assertions."""
        logger.info(f"Converting evaluation results to pytest assertions for {len(results)} test cases")
        metrics = self.calculate_metrics(results)
        failed_cases = [r for r in results if not r.passed]

        logger.info(f"Printing test summary: {metrics.passed_tests}/{metrics.total_tests} passed")
        print("\n📊 Evaluation Summary:")
        print(
            f"   Passed: {metrics.passed_tests}/{metrics.total_tests} ({metrics.passed_tests / metrics.total_tests * 100:.1f}%)"
        )
        print(f"   Avg Score: {metrics.avg_llm_score:.1f}/5")
        print(f"   Avg Response: {metrics.avg_response_time:.1f}s")

        if failed_cases:
            logger.error(f"Found {len(failed_cases)} failed test cases, preparing pytest failure")
            failure_details = []
            for case in failed_cases:
                tools_info = f"Tools: {case.used_tools}" if case.used_tools else "No tools used"
                failure_details.append(
                    f"❌ {case.test_id} ({case.category}): Score {case.llm_judge_score}/5 - {tools_info}"
                )

            failure_summary = "\n".join(failure_details)
            logger.error(f"Failing pytest with summary of {len(failed_cases)} failed cases")
            pytest.fail(f"\n🚨 Evaluation failed for {len(failed_cases)} test cases:\n\n{failure_summary}")

        logger.info(f"All {len(results)} evaluation cases passed successfully")
        print(f"✅ All {len(results)} evaluation cases passed!")

    def load_historical_results(self, agent_name: str, max_runs: int = 50) -> Dict[str, List[Dict[str, Any]]]:
        """Load historical CSV files and group by test_id."""
        logger.info(f"Loading historical results for {agent_name} (max {max_runs} runs)")

        # Scan results directory for matching CSV files
        pattern = f"{agent_name}_*_summary.csv"
        csv_files = list(self.output_dir.glob(pattern))

        # Sort by timestamp in filename (most recent first)
        csv_files.sort(key=lambda x: x.name, reverse=True)
        csv_files = csv_files[:max_runs]  # Limit to max_runs

        logger.debug(f"Found {len(csv_files)} historical CSV files")

        # Parse and aggregate by test_id
        historical_data: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for csv_file in csv_files:
            try:
                timestamp = self._extract_timestamp_from_filename(csv_file.name)
                logger.debug(f"Processing historical file: {csv_file.name} (timestamp: {timestamp})")

                with open(csv_file, "r") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        test_id = row["test_id"]
                        historical_data[test_id].append(
                            {
                                "timestamp": timestamp,
                                "score": float(row["llm_score"]),
                                "passed": row["passed"].lower() == "true",
                                "response_time": float(row["response_time"]),
                                "tools_used": int(row["tools_used"]),
                            }
                        )
            except Exception as e:
                logger.warning(f"Error processing historical file {csv_file}: {e}")
                continue

        # Sort each test's runs by timestamp (oldest first for trend analysis)
        for test_id in historical_data:
            historical_data[test_id].sort(key=lambda x: x["timestamp"])

        logger.info(f"Loaded historical data for {len(historical_data)} test cases")
        return dict(historical_data)

    def _extract_timestamp_from_filename(self, filename: str) -> datetime.datetime:
        """Extract timestamp from filename like 'agent_20250930_121335_summary.csv'."""
        try:
            # Extract timestamp part (YYYYMMDD_HHMMSS)
            parts = filename.split("_")
            if len(parts) >= 3:
                date_str = parts[-3]  # 20250930
                time_str = parts[-2]  # 121335
                timestamp_str = f"{date_str}_{time_str}"
                return datetime.datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
        except Exception as e:
            logger.warning(f"Could not extract timestamp from {filename}: {e}")

        # Fallback to file modification time
        return datetime.datetime.fromtimestamp(Path(filename).stat().st_mtime)

    def calculate_historical_metrics(self, historical_data: Dict[str, List[Dict[str, Any]]]) -> List[HistoricalMetrics]:
        """Calculate trends and averages across historical runs."""
        logger.info(f"Calculating historical metrics for {len(historical_data)} test cases")

        metrics = []
        for test_id, runs in historical_data.items():
            if len(runs) < 1:  # Need at least 1 run
                continue

            scores = [run["score"] for run in runs]
            response_times = [run["response_time"] for run in runs]
            passed_count = sum(1 for run in runs if run["passed"])

            # Calculate trend direction
            trend = self._calculate_trend_direction(scores)

            # Calculate standard deviation
            score_mean = sum(scores) / len(scores)
            score_variance = sum((score - score_mean) ** 2 for score in scores) / len(scores)
            score_std_dev = score_variance**0.5

            metric = HistoricalMetrics(
                test_id=test_id,
                total_runs=len(runs),
                avg_score=score_mean,
                score_trend=scores[-10:],  # Last 10 runs
                avg_response_time=sum(response_times) / len(response_times),
                success_rate=passed_count / len(runs),
                score_std_dev=score_std_dev,
                last_run_date=max(run["timestamp"] for run in runs),
                improvement_trend=trend,
                run_number=len(runs),
            )
            metrics.append(metric)

            logger.debug(f"Calculated metrics for {test_id}: avg_score={metric.avg_score:.1f}, trend={trend}")

        logger.info(f"Calculated historical metrics for {len(metrics)} test cases")
        return metrics

    def _calculate_trend_direction(self, scores: List[float]) -> str:
        """Calculate trend direction based on score progression."""
        if len(scores) < 3:
            return "stable"

        # Compare recent half vs older half
        mid_point = len(scores) // 2
        recent_avg = sum(scores[mid_point:]) / len(scores[mid_point:])
        older_avg = sum(scores[:mid_point]) / len(scores[:mid_point])

        diff = recent_avg - older_avg

        if diff > 0.3:  # Significant improvement
            return "improving"
        elif diff < -0.3:  # Significant decline
            return "declining"
        else:
            return "stable"

    def detect_regressions(self, current_results: List[EvaluationResult], agent_name: str) -> List[str]:
        """Detect performance regressions compared to historical averages."""
        logger.info(f"Detecting regressions for {len(current_results)} current results")

        historical_data = self.load_historical_results(agent_name)
        regressions = []

        for result in current_results:
            if result.test_id in historical_data:
                hist_runs = historical_data[result.test_id]
                if len(hist_runs) >= 3:  # Need sufficient history
                    hist_scores = [run["score"] for run in hist_runs]
                    hist_avg = sum(hist_scores) / len(hist_scores)

                    # Alert if current score is significantly below historical average
                    if result.llm_judge_score < hist_avg - 1.0:  # 1 point threshold
                        regressions.append(
                            f"⚠️ Regression detected in {result.test_id}: "
                            f"Current {result.llm_judge_score}/5 vs Historical {hist_avg:.1f}/5 "
                            f"(based on {len(hist_runs)} runs)"
                        )
                        logger.warning(
                            f"Regression detected: {result.test_id} current={result.llm_judge_score} vs hist={hist_avg:.1f}"
                        )

        logger.info(f"Found {len(regressions)} potential regressions")
        return regressions

    def generate_historical_report(self, current_results: List[EvaluationResult], agent_name: str) -> str:
        """Generate report including historical trends."""
        logger.info(f"Generating historical report for {agent_name}")

        # Get current run report
        current_report = self.generate_report(current_results, agent_name)

        # Load and analyze historical data
        historical_data = self.load_historical_results(agent_name)
        if not historical_data:
            logger.info("No historical data available, returning current report only")
            return current_report

        historical_metrics = self.calculate_historical_metrics(historical_data)

        trend_report = f"""

## 📈 Historical Trends (Last {sum(len(runs) for runs in historical_data.values())} total runs)

### Test Performance Over Time
"""

        for metric in sorted(historical_metrics, key=lambda x: x.avg_score, reverse=True):
            trend_emoji = {"improving": "📈", "stable": "➡️", "declining": "📉"}[metric.improvement_trend]

            trend_report += f"""
**{metric.test_id}** {trend_emoji}
- Average Score: {metric.avg_score:.1f}/5 ({metric.total_runs} runs)
- Success Rate: {metric.success_rate:.1%}
- Avg Response: {metric.avg_response_time:.1f}s
- Stability: σ={metric.score_std_dev:.1f}
- Trend: {metric.improvement_trend}
- Last Run: {metric.last_run_date.strftime("%Y-%m-%d %H:%M")}
"""

        # Add regression analysis
        regressions = self.detect_regressions(current_results, agent_name)
        if regressions:
            trend_report += "\n## 🚨 Potential Regressions\n"
            for regression in regressions:
                trend_report += f"- {regression}\n"

        logger.debug(f"Historical report generated with {len(historical_metrics)} metrics")
        return current_report + trend_report

    def pytest_assert_results_with_history(self, results: List[EvaluationResult], agent_name: str):
        """Enhanced pytest assertions with historical context."""
        logger.info(f"Running enhanced pytest assertions with historical context for {agent_name}")

        # Run standard assertions first
        self.pytest_assert_results(results)

        # Add historical analysis
        regressions = self.detect_regressions(results, agent_name)
        if regressions:
            print("\n🔍 Performance Analysis:")
            for regression in regressions:
                print(f"   {regression}")

        # Generate and print enhanced report
        enhanced_report = self.generate_historical_report(results, agent_name)
        print(f"\n{enhanced_report}")

        logger.info("Enhanced pytest assertions completed successfully")
