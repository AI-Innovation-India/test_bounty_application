from langgraph.graph import StateGraph, START, END
from src.agents.state import TestingState
from src.agents.nodes import (
    bootstrap_node,
    analyze_code_node,
    generate_prd_node,
    frontend_plan_node,
    backend_plan_node,
    security_plan_node,
    execute_tests_node,
    report_node,
    fix_tests_node
)

def build_graph():
    """
    Construct the TestSprite Agent Workflow Graph.
    """
    workflow = StateGraph(TestingState)

    # Add Nodes
    workflow.add_node("bootstrap", bootstrap_node)
    workflow.add_node("analyze", analyze_code_node)
    workflow.add_node("prd", generate_prd_node)
    workflow.add_node("frontend_plan", frontend_plan_node)
    workflow.add_node("backend_plan", backend_plan_node)
    workflow.add_node("security_plan", security_plan_node)
    workflow.add_node("execute", execute_tests_node)
    workflow.add_node("report", report_node)

    # Add Edges
    # Sequence: Start -> Bootstrap -> Analyze -> PRD
    workflow.add_edge(START, "bootstrap")
    workflow.add_edge("bootstrap", "analyze")
    workflow.add_edge("analyze", "prd")

    # Parallel: PRD -> Frontend & Backend & Security Plans
    workflow.add_edge("prd", "frontend_plan")
    workflow.add_edge("prd", "backend_plan")
    workflow.add_edge("prd", "security_plan")

    # Sync/Join: All plans -> Execute
    workflow.add_node("join_plans", lambda x: x) # Pass-through
    workflow.add_edge("frontend_plan", "join_plans")
    workflow.add_edge("backend_plan", "join_plans")
    workflow.add_edge("security_plan", "join_plans")
    workflow.add_edge("join_plans", "execute")

    # Fixer Loop Logic
    workflow.add_node("fix_tests", fix_tests_node)

    def should_fix(state: TestingState):
        """
        Determine if we should fix tests or move to reporting.
        """
        results = state.get("test_results", {})
        exit_code = results.get("exit_code", 0)
        retries = state.get("retries", 0)
        max_retries = state.get("max_retries", 3)
        
        if exit_code != 0 and retries < max_retries:
            return "fix_tests"
        return "report"

    # Conditional Edge: Execute -> [Fix or Report]
    workflow.add_conditional_edges(
        "execute",
        should_fix,
        {
            "fix_tests": "fix_tests",
            "report": "report"
        }
    )
    
    # Loop back: Fix -> Execute
    workflow.add_edge("fix_tests", "execute")

    # Sequence: Report -> End
    workflow.add_edge("report", END)

    return workflow.compile()

# Global app instance
app = build_graph()
