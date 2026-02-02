from typing import TypedDict, Optional, Dict, Any, List, Annotated
import operator

class TestingState(TypedDict):
    project_path: Optional[str] # Now optional
    target_url: Optional[str]   # New field for Blackbox
    project_type: Optional[str]
    
    # Results from steps
    bootstrap_result: Optional[Dict[str, Any]]
    code_summary: Optional[Dict[str, Any]]
    prd: Optional[Dict[str, Any]]
    
    # Plans
    frontend_plan: Optional[Dict[str, Any]]
    backend_plan: Optional[Dict[str, Any]]
    
    # Execution
    test_results: Optional[Dict[str, Any]]
    report_path: Optional[str]
    
    # Metadata
    error_log: Annotated[List[str], operator.add]
    steps_completed: Annotated[List[str], operator.add]

    # Retry Tracking
    retries: int
    max_retries: int
