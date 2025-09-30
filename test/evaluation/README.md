# SONiC Agent Evaluation Framework

Pytest-based evaluation framework for SONiC network analysis agents using Strands Agents and LLM judge evaluation.

## Overview

This framework replaces the previous FastAPI container-based approach with a direct pytest implementation that provides:

- **Dataclass-based architecture** for clean, type-safe evaluation
- **Environment-gated execution** via `EXECUTE_EVALUATIONS` variable
- **YAML-driven test cases** for easy maintenance and extension
- **LLM judge evaluation** using Claude Sonnet 4 v1:0
- **Comprehensive metrics collection** with JSON/CSV export
- **Pytest integration** with detailed assertions and reporting

## Architecture

```
test/evaluation/
├── __init__.py                           # Evaluation module
├── conftest.py                          # Pytest fixtures with environment gating
├── models.py                            # Pydantic data models
├── workflow_models.py                   # YAML workflow utilities
├── test_sonic_evaluation.py             # Main evaluation tests
├── framework/                           # Core evaluation framework
│   ├── __init__.py
│   └── eval_agent_tester.py            # EvalAgentTester dataclass framework
├── test_cases/                          # YAML test case definitions
│   ├── basic_analysis.yaml
│   └── network_troubleshooting.yaml
├── fixtures/                            # Additional test fixtures
├── results/                            # Evaluation results (JSON/CSV)
└── data/                               # Tech support test files
```

## Usage

### Environment Gating

All evaluation tests are automatically skipped unless the environment variable is set:

```bash
# Tests are skipped by default
pytest test/evaluation/
# → All tests SKIPPED

# Enable evaluation tests
EXECUTE_EVALUATIONS=true pytest test/evaluation/
# → Tests run with full Strands agent evaluation
```

### Running Evaluation Tests

```bash
# Run basic analysis evaluation
EXECUTE_EVALUATIONS=true pytest test/evaluation/ -v -k basic

# Run network troubleshooting evaluation  
EXECUTE_EVALUATIONS=true pytest test/evaluation/ -v -k network

# Run all evaluation tests with detailed output
EXECUTE_EVALUATIONS=true pytest test/evaluation/ -v -s
```

### Test Structure

Each evaluation test uses the `EvalAgentTester` dataclass framework:

```python
@pytest.mark.evaluation
def test_basic_sonic_analysis(eval_agent_tester_basic):
    """Test basic SONiC analysis capabilities."""
    results = eval_agent_tester_basic.evaluate_agent("sonic-basic-analysis")
    
    # Generate detailed report
    report = eval_agent_tester_basic.generate_report(results, "sonic-basic-analysis")
    print(f"\n{report}")
    
    # Assert all tests pass (fails with detailed info if not)
    eval_agent_tester_basic.pytest_assert_results(results)
```

## YAML Test Cases

Test cases are defined in YAML files with structured metadata:

```yaml
# test_cases/basic_analysis.yaml
test_cases:
  - id: "sonic-basic-001"
    category: "system_health"
    query: "Extract and analyze the SONiC tech support file for system health overview"
    expected: "System status summary with file extraction confirmation"
    expected_tools: ["extract_tech_support_file", "list_tech_support_files_tool"]
    expected_patterns: ["extracted", "files found", "directory structure"]
    context:
      analysis_type: "basic"
      focus_areas: ["extraction", "file_listing"]
```

## LLM Judge Evaluation

The framework uses Claude Sonnet 4 v1:0 as both the evaluation agent and the LLM judge:

- **Evaluation Agent**: Performs SONiC analysis with MCP tools
- **LLM Judge**: Scores responses 1-5 based on accuracy, relevance, completeness, and tool usage
- **Automatic Pass/Fail**: Score ≥4 + proper tool usage = Pass

## Results and Metrics

Evaluation results are automatically saved in multiple formats:

- **JSON**: Detailed results with timestamps and feedback
- **CSV**: Summary metrics for analysis
- **Console**: Real-time progress and final report
- **Pytest**: Integration with pytest reporting and assertions

## Key Benefits

1. **Simplified Development**: No container orchestration required
2. **Fast Iteration**: Direct pytest execution, easy debugging
3. **Environment Safety**: Tests only run when explicitly enabled
4. **Comprehensive Reporting**: Detailed metrics and LLM judge feedback
5. **Extensible**: Easy to add new test cases via YAML
6. **CI Integration**: Standard pytest workflow, no special infrastructure

## Adding New Test Cases

1. Create/modify YAML files in `test_cases/`
2. Add new test categories as needed
3. Update fixtures in `conftest.py` if required
4. Tests automatically discover and run new cases

This approach provides enterprise-grade evaluation capabilities while maintaining the simplicity and speed of direct pytest execution.
