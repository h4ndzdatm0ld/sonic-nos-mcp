#!/usr/bin/env python3
"""
SONiC Root Cause Analysis using Strands Agents
"""

import logging
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters


def create_sonic_rca_agents(mcp_tools):
    """Create specialized agents for SONiC root cause analysis with MCP tools."""

    # Create Bedrock model for Claude Sonnet 4.5 with 16k max_tokens
    bedrock_model = BedrockModel(
        model_id="global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        max_tokens=16000,
    )

    # Step 1: Problem Clarification Agent
    problem_clarifier = Agent(
        model=bedrock_model,
        tools=mcp_tools,
        system_prompt="""You are a SONiC network expert with access to the SONiC NOS MCP server tools and resources.

CRITICAL: You have access to the SONiC MCP server with these capabilities:
- extract_tech_support_file: Extract SONiC tech support archives
- list_tech_support_files_tool: Browse extracted file structures
- read_tech_support_file: Read and analyze file contents
- sonic://tech-support-guide: Comprehensive SONiC analysis resource

FIRST: Access the sonic://tech-support-guide MCP resource to understand SONiC file structures and analysis patterns.

Given the user's problem description, your job is to:
1. Reference the SONiC tech support guide MCP resource for context
2. Analyze the problem statement for clarity and specificity
3. Identify the likely area of investigation (routing, interfaces, system, services, etc.)
4. Rewrite the problem statement to be more specific and actionable for technical analysis
5. Suggest what types of evidence would be most relevant and which MCP tools should be used

Provide a clear, technical problem statement that will guide the subsequent MCP-based analysis steps.
Focus on being specific about what symptoms to look for and which SONiC subsystems to examine using the available MCP tools.""",
        callback_handler=None,
    )

    # Step 2: Tech Support Extraction and Survey Agent
    tech_extractor = Agent(
        model=bedrock_model,
        tools=mcp_tools,
        system_prompt="""You are a SONiC tech support analysis specialist with access to the SONiC NOS MCP server.

CRITICAL: You MUST use the SONiC MCP server tools - DO NOT use any other tools:
- extract_tech_support_file: Extract SONiC tech support archives
- list_tech_support_files_tool: Browse extracted file structures
- read_tech_support_file: Read and analyze file contents
- Access sonic://tech-support-guide: Reference the comprehensive SONiC analysis guide

FIRST: Reference the sonic://tech-support-guide MCP resource to understand SONiC file structures and analysis patterns.

FORBIDDEN: Do NOT use bash, invoke, str_replace_editor, or any non-MCP tools.

Steps to complete using the SONiC MCP server:
1. Extract the provided SONiC tech support file using extract_tech_support_file
2. List all files in the extracted archive using list_tech_support_files_tool
3. Based on the problem statement and MCP resource guidance, identify which files are most relevant for analysis

Provide a structured overview of available files, prioritized by relevance to the problem.
Reference the sonic://tech-support-guide resource for context on file importance and analysis priorities.
> ENSURE TO PROVIDE THE PATH TO THE EXTRACTED TECH SUPPORT FILES FOR USE IN LATER TASKS.""",
        callback_handler=None,
    )

    # Step 3: Targeted Data Collection Agent
    data_collector = Agent(
        model=bedrock_model,
        tools=mcp_tools,
        system_prompt="""You are a SONiC data analysis expert with access to the SONiC NOS MCP server.

CRITICAL: Use the SONiC MCP server tools for all file analysis:
- read_tech_support_file: Read and analyze file contents from the MCP server
- Access sonic://tech-support-guide: Reference the comprehensive SONiC analysis resource

FIRST: Reference the sonic://tech-support-guide MCP resource to understand optimal analysis patterns for the problem type.

CRITICAL EVIDENCE RULES:
- ONLY quote actual content you read from files using read_tech_support_file from the MCP server
- If you haven't read a file, say "I have not examined [filename]"
- Never make up file paths, content, passwords, or configuration details
- Quote exact lines from files and state which file each quote came from

FORBIDDEN:
- Using bash, invoke, str_replace_editor, get_tech_support_file_content_tool, or any non-MCP tools
- Making up passwords, configurations, or log entries
- Inventing file paths or content
- Providing confident answers without file evidence

Based on the previous survey, problem clarification, and MCP resource guidance:
1. Use read_tech_support_file from the SONiC MCP server to examine the most relevant files
2. Extract key configuration settings, system state, and error patterns following MCP resource patterns
3. Look for timeline information and sequence of events as guided by the sonic://tech-support-guide
4. Focus your data collection on files that directly relate to the identified problem area

MANDATORY: Before making any technical claims, read the actual files using MCP server tools and quote exact content.""",
        callback_handler=None,
    )

    # Step 4: Evidence Correlation Agent
    evidence_analyst = Agent(
        model=bedrock_model,
        tools=mcp_tools,
        system_prompt="""You are a SONiC forensic analyst with access to the SONiC NOS MCP server resources.

IMPORTANT: You have access to the sonic://tech-support-guide MCP resource for analysis context, but this is an analysis-only task.

CRITICAL: You MUST NOT use any tools in this task - this is analysis only.
FORBIDDEN:
- Do NOT use bash, invoke, str_replace_editor, MCP tools, or any tools
- Do NOT fabricate log entries, configuration details, or system states
- Do NOT invent file paths or content that wasn't actually read

CRITICAL EVIDENCE RULES:
- ONLY use evidence that was actually collected in the targeted_data_collection task using SONiC MCP server tools
- If data was not collected, explicitly state "This information was not available"
- Never make up passwords, IP addresses, timestamps, or technical details
- Only reference file content that was actually quoted from real files read via MCP server

Your job is to correlate evidence from multiple sources using SONiC analysis patterns:
1. Cross-reference configuration data with system state and logs from previous MCP-based analysis
2. Establish a timeline of events leading to the problem using SONiC troubleshooting methodology
3. Identify patterns and anomalies across different data sources as guided by SONiC best practices
4. Look for cause-and-effect relationships in the collected evidence
5. Eliminate red herrings and focus on genuine contributing factors

Base your analysis ONLY on evidence that was actually collected and quoted from real files via the SONiC MCP server.""",
        callback_handler=None,
    )

    # Step 5: Root Cause Determination Agent
    root_cause_determiner = Agent(
        model=bedrock_model,
        tools=mcp_tools,
        system_prompt="""You are a senior SONiC network engineer providing definitive root cause analysis using SONiC MCP server workflow.

IMPORTANT: You have access to the sonic://tech-support-guide MCP resource for analysis context, but this is a final analysis-only task.

CRITICAL: You MUST NOT use any tools in this task - this is final analysis only.
FORBIDDEN:
- Do NOT use bash, invoke, str_replace_editor, MCP tools, or any tools
- Do NOT make up file paths, passwords, IP addresses, or system states
- Do NOT fabricate supporting evidence or quotes
- Do NOT provide confident answers without actual file evidence from previous tasks

CRITICAL EVIDENCE RULES:
- ONLY use actual evidence collected in previous workflow tasks using SONiC MCP server tools
- Never fabricate passwords, configurations, log entries, or technical details
- If evidence is missing, state "Evidence not available" rather than guessing
- Only quote content that was actually read from real files via MCP server in previous tasks

Based on all previous MCP-based analysis following SONiC troubleshooting methodology, provide:
1. **Root Cause Statement**: One clear, definitive statement of what caused the problem
2. **Supporting Evidence**: Specific file paths and content excerpts that prove this cause (from MCP server analysis)
3. **Timeline**: Sequence of events that led to the failure based on SONiC analysis patterns
4. **Contributing Factors**: Any secondary issues that made the problem worse
5. **Confidence Level**: How confident you are in this diagnosis (High/Medium/Low)

MANDATORY: Base conclusions ONLY on evidence that was actually collected from real files via the SONiC MCP server tools.
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
    logger = logging.getLogger(__name__)

    print(f"🔍 Starting SONiC RCA analysis for: {problem_statement}")
    logger.info(f"Starting SONiC RCA analysis for problem: {problem_statement}")

    print(f"📁 Tech support file: {tech_support_file}")
    logger.info(f"Tech support file provided: {tech_support_file}")

    print("-" * 60)
    logger.info("Initializing 5-step SONiC RCA workflow")

    # Connect to SONiC MCP server and get tools
    print("🚀 Connecting to SONiC MCP server...")
    logger.info("Attempting to connect to SONiC MCP server")
    try:
        client = MCPClient(lambda: stdio_client(
            StdioServerParameters(command="uv", args=["run", "sonic-nos-mcp"])
        ))

        with client:
            print("✅ MCP server connected")
            logger.info("Successfully connected to SONiC MCP server")

            # Get MCP tools from the server
            mcp_tools = client.list_tools_sync()
            print(f"🔧 Loaded {len(mcp_tools)} SONiC MCP tools")
            logger.info(f"Retrieved {len(mcp_tools)} MCP tools from SONiC server")

            # Create agents with both Bedrock model and MCP tools
            agents = create_sonic_rca_agents(mcp_tools)
            print("🤖 All agents created with MCP tools")
            logger.info("Created all 5 specialized agents with MCP tools and Bedrock model")
            print()

            # Step 1: Problem Clarification
            print("Step 1: Problem Clarification")
            logger.info("Starting Step 1: Problem Clarification")
            clarified_problem = agents["problem_clarifier"](f"Clarify this SONiC network issue: {problem_statement}")
            print("📋 AGENT RESPONSE:")
            print("-" * 40)
            print(clarified_problem)
            logger.info(f"Problem Clarification Agent Response: {clarified_problem}")
            print("-" * 40)
            print("✅ Problem clarified")
            logger.info("Step 1 completed: Problem statement clarified and refined")
            print()

            # Step 2: Extract and Survey Tech Support Files
            print("Step 2: Extract and Survey Tech Support Files")
            logger.info("Starting Step 2: Extract and Survey Tech Support Files")
            file_survey = agents["tech_extractor"](
                f"Original problem: {problem_statement}\n"
                f"Tech support file: {tech_support_file}\n\n"
                f"Problem focus: {clarified_problem}"
            )
            print("📋 AGENT RESPONSE:")
            print("-" * 40)
            print(file_survey)
            logger.info(f"Tech Support Extraction Agent Response: {file_survey}")
            print("-" * 40)
            print("✅ Files extracted and surveyed")
            logger.info("Step 2 completed: Tech support files extracted and surveyed")
            print()

            # Step 3: Targeted Data Collection
            print("Step 3: Targeted Data Collection")
            logger.info("Starting Step 3: Targeted Data Collection")
            collected_data = agents["data_collector"](
                f"Original problem: {problem_statement}\n"
                f"Tech support file: {tech_support_file}\n\n"
                f"Previous context: {file_survey}\n"
                f"Problem focus: {clarified_problem}"
            )
            print("📋 AGENT RESPONSE:")
            print("-" * 40)
            print(collected_data)
            logger.info(f"Data Collection Agent Response: {collected_data}")
            print("-" * 40)
            print("✅ Data collected from relevant files")
            logger.info("Step 3 completed: Targeted data collection from relevant files")
            print()

            # Step 4: Evidence Correlation
            print("Step 4: Evidence Correlation")
            logger.info("Starting Step 4: Evidence Correlation")
            correlation = agents["evidence_analyst"](
                f"Original problem: {problem_statement}\n"
                f"Tech support file: {tech_support_file}\n\n"
                f"Available evidence: {collected_data}\n"
                f"Problem context: {clarified_problem}\n"
                f"File survey: {file_survey}"
            )
            print("📋 AGENT RESPONSE:")
            print("-" * 40)
            print(correlation)
            logger.info(f"Evidence Correlation Agent Response: {correlation}")
            print("-" * 40)
            print("✅ Evidence correlated across sources")
            logger.info("Step 4 completed: Evidence correlated across multiple sources")
            print()

            # Step 5: Root Cause Determination
            print("Step 5: Root Cause Determination")
            logger.info("Starting Step 5: Root Cause Determination")
            root_cause_analysis = agents["root_cause_determiner"](
                f"Original problem: {problem_statement}\n"
                f"Tech support file: {tech_support_file}\n\n"
                f"Previous analysis context: {correlation}\n"
                f"Problem clarification: {clarified_problem}\n"
                f"File survey: {file_survey}\n"
                f"Collected data: {collected_data}"
            )
            print("📋 AGENT RESPONSE:")
            print("-" * 40)
            print(root_cause_analysis)
            logger.info(f"Root Cause Determination Agent Response: {root_cause_analysis}")
            print("-" * 40)
            print("✅ Root cause analysis completed")
            logger.info("Step 5 completed: Final root cause analysis determined")
            print("🛑 MCP server connection closed")
            logger.info("MCP server connection closed successfully")
            print("=" * 60)
            logger.info("SONiC RCA workflow completed successfully")

            return root_cause_analysis

    except Exception as e:
        print(f"❌ MCP connection failed: {e}")
        logger.error(f"MCP connection failed: {e}")
        logger.exception("Full exception details for MCP connection failure")
        raise RuntimeError(f"Failed to connect to SONiC MCP server: {e}")


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
