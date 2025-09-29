#!/usr/bin/env python3
"""
Simplified SONiC Root Cause Analysis using Strands Agents

Extracts the 5-step workflow from rca-1.yaml into a simple sequential pattern
while preserving all the detailed system prompts and anti-hallucination guards.
"""

from strands import Agent


def create_sonic_rca_agents():
    """Create specialized agents for SONiC root cause analysis."""

    # Step 1: Problem Clarification Agent
    problem_clarifier = Agent(
        system_prompt="""You are a SONiC network expert tasked with clarifying problem statements for effective analysis.
      
Given the user's problem description, your job is to:
1. Analyze the problem statement for clarity and specificity
2. Identify the likely area of investigation (routing, interfaces, system, services, etc.)
3. Rewrite the problem statement to be more specific and actionable for technical analysis
4. Suggest what types of evidence would be most relevant

Provide a clear, technical problem statement that will guide the subsequent analysis steps.
Focus on being specific about what symptoms to look for and which SONiC subsystems to examine.""",
        callback_handler=None,
    )

    # Step 2: Tech Support Extraction and Survey Agent
    tech_extractor = Agent(
        system_prompt="""You are a SONiC tech support analysis specialist.

CRITICAL: You MUST ONLY use these MCP tools - DO NOT use any other tools:
- extract_tech_support_file
- list_tech_support_files_tool
- read_tech_support_file

FORBIDDEN: Do NOT use bash, invoke, str_replace_editor, or any non-MCP tools.

Steps to complete:
1. Extract the provided SONiC tech support file using extract_tech_support_file
2. List all files in the extracted archive using list_tech_support_files_tool
3. Based on the problem statement, identify which files are most relevant for analysis

Provide a structured overview of available files, prioritized by relevance to the problem.
> ENSURE TO PROVIDE THE PATH TO THE EXTRACTED TECH SUPPORT FILES FOR USE IN LATER TASKS.""",
        callback_handler=None,
    )

    # Step 3: Targeted Data Collection Agent
    data_collector = Agent(
        system_prompt="""You are a SONiC data analysis expert.

CRITICAL EVIDENCE RULES:
- ONLY quote actual content you read from files using read_tech_support_file
- If you haven't read a file, say "I have not examined [filename]"
- Never make up file paths, content, passwords, or configuration details
- Quote exact lines from files and state which file each quote came from

CRITICAL: You MUST ONLY use these MCP tools - DO NOT use any other tools:
- read_tech_support_file (to examine file contents)

FORBIDDEN:
- Using bash, invoke, str_replace_editor, get_tech_support_file_content_tool, or any non-MCP tools
- Making up passwords, configurations, or log entries
- Inventing file paths or content
- Providing confident answers without file evidence

Based on the previous survey and problem clarification:
1. Use read_tech_support_file to examine the most relevant files for this problem
2. Extract key configuration settings, system state, and error patterns
3. Look for timeline information and sequence of events
4. Focus your data collection on files that directly relate to the identified problem area

MANDATORY: Before making any technical claims, read the actual files and quote exact content.""",
        callback_handler=None,
    )

    # Step 4: Evidence Correlation Agent
    evidence_analyst = Agent(
        system_prompt="""You are a SONiC forensic analyst.

CRITICAL EVIDENCE RULES:
- ONLY use evidence that was actually collected in the targeted_data_collection task
- If data was not collected, explicitly state "This information was not available"
- Never make up passwords, IP addresses, timestamps, or technical details
- Only reference file content that was actually quoted from real files

CRITICAL: You MUST NOT use any tools in this task - this is analysis only.
FORBIDDEN:
- Do NOT use bash, invoke, str_replace_editor, MCP tools, or any tools
- Do NOT fabricate log entries, configuration details, or system states
- Do NOT invent file paths or content that wasn't actually read

Your job is to correlate evidence from multiple sources:
1. Cross-reference configuration data with system state and logs from previous tasks
2. Establish a timeline of events leading to the problem
3. Identify patterns and anomalies across different data sources  
4. Look for cause-and-effect relationships in the collected evidence
5. Eliminate red herrings and focus on genuine contributing factors

Base your analysis ONLY on evidence that was actually collected and quoted from real files.""",
        callback_handler=None,
    )

    # Step 5: Root Cause Determination Agent
    root_cause_determiner = Agent(
        system_prompt="""You are a senior SONiC network engineer providing definitive root cause analysis.

CRITICAL EVIDENCE RULES:
- ONLY use actual evidence collected in previous workflow tasks
- Never fabricate passwords, configurations, log entries, or technical details
- If evidence is missing, state "Evidence not available" rather than guessing
- Only quote content that was actually read from real files in previous tasks

CRITICAL: You MUST NOT use any tools in this task - this is final analysis only.
FORBIDDEN:
- Do NOT use bash, invoke, str_replace_editor, MCP tools, or any tools
- Do NOT make up file paths, passwords, IP addresses, or system states
- Do NOT fabricate supporting evidence or quotes
- Do NOT provide confident answers without actual file evidence from previous tasks

Based on all previous analysis, provide:
1. **Root Cause Statement**: One clear, definitive statement of what caused the problem
2. **Supporting Evidence**: Specific file paths and content excerpts that prove this cause
3. **Timeline**: Sequence of events that led to the failure
4. **Contributing Factors**: Any secondary issues that made the problem worse
5. **Confidence Level**: How confident you are in this diagnosis (High/Medium/Low)

MANDATORY: Base conclusions ONLY on evidence that was actually collected from real files.
If evidence is insufficient, state limitations rather than fabricating details.""",
        callback_handler=None,
    )

    return {
        "problem_clarifier": problem_clarifier,
        "tech_extractor": tech_extractor,
        "data_collector": data_collector,
        "evidence_analyst": evidence_analyst,
        "root_cause_determiner": root_cause_determiner,
    }


def rca_workflow(problem_statement: str, tech_support_file: str) -> str:
    """
    Analyze a SONiC network issue using the 5-step RCA workflow.

    Args:
        problem_statement: Description of the network issue
        tech_support_file: Path to the SONiC tech support bundle

    Returns:
        Final root cause analysis report
    """
    # Create all the specialized agents
    agents = create_sonic_rca_agents()

    print(f"🔍 Starting SONiC RCA analysis for: {problem_statement}")
    print(f"📁 Tech support file: {tech_support_file}")
    print("-" * 60)

    # Step 1: Problem Clarification
    print("Step 1: Problem Clarification")
    clarified_problem = agents["problem_clarifier"](f"Clarify this SONiC network issue: {problem_statement}")
    print("✅ Problem clarified")
    print()

    # Step 2: Extract and Survey Tech Support Files
    print("Step 2: Extract and Survey Tech Support Files")
    file_survey = agents["tech_extractor"](
        f"Original problem: {problem_statement}\n"
        f"Tech support file: {tech_support_file}\n\n"
        f"Problem focus: {clarified_problem}"
    )
    print("✅ Files extracted and surveyed")
    print()

    # Step 3: Targeted Data Collection
    print("Step 3: Targeted Data Collection")
    collected_data = agents["data_collector"](
        f"Original problem: {problem_statement}\n"
        f"Tech support file: {tech_support_file}\n\n"
        f"Previous context: {file_survey}\n"
        f"Problem focus: {clarified_problem}"
    )
    print("✅ Data collected from relevant files")
    print()

    # Step 4: Evidence Correlation
    print("Step 4: Evidence Correlation")
    correlation = agents["evidence_analyst"](
        f"Original problem: {problem_statement}\n"
        f"Tech support file: {tech_support_file}\n\n"
        f"Available evidence: {collected_data}\n"
        f"Problem context: {clarified_problem}\n"
        f"File survey: {file_survey}"
    )
    print("✅ Evidence correlated across sources")
    print()

    # Step 5: Root Cause Determination
    print("Step 5: Root Cause Determination")
    root_cause_analysis = agents["root_cause_determiner"](
        f"Original problem: {problem_statement}\n"
        f"Tech support file: {tech_support_file}\n\n"
        f"Previous analysis context: {correlation}\n"
        f"Problem clarification: {clarified_problem}\n"
        f"File survey: {file_survey}\n"
        f"Collected data: {collected_data}"
    )
    print("✅ Root cause analysis completed")
    print("=" * 60)

    return root_cause_analysis


def main():
    """Example usage of the SONiC RCA workflow."""
    import sys

    if len(sys.argv) != 3:
        print("Usage: python sonic_rca_workflow.py <problem_statement> <tech_support_file>")
        print("\nExample:")
        print("  python sonic_rca_workflow.py 'BGP sessions are down' '/path/to/techsupport.tar.gz'")
        sys.exit(1)

    problem = sys.argv[1]
    tech_file = sys.argv[2]

    try:
        result = rca_workflow(problem, tech_file)
        print("\n🎯 FINAL ROOT CAUSE ANALYSIS:")
        print(result)
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
