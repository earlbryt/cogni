from typing import Dict, Any
from langgraph.graph import StateGraph, END
from schema_extraction.state import SchemaExtractionState
from schema_extraction.nodes import extract_schema, validate_schema

class SchemaExtractionWorkflow:
    """Orchestrates the schema extraction workflow using LangGraph."""
    
    def __init__(self, max_iterations: int = 3):
        self.max_iterations = max_iterations
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Construct the workflow graph."""
        # Initialize the graph with our state type
        workflow = StateGraph(SchemaExtractionState)
        
        # Add nodes
        workflow.add_node("extract_schema", extract_schema)
        workflow.add_node("validate_schema", validate_schema)
        
        # Define edges
        workflow.add_edge("extract_schema", "validate_schema")
        workflow.add_conditional_edges(
            "validate_schema",
            self._get_next_node,
            {
                "extract_schema": "extract_schema",
                "end": END
            }
        )
        
        # Set entry point
        workflow.set_entry_point("extract_schema")
        
        return workflow.compile()
    
    @staticmethod
    def _get_next_node(state: SchemaExtractionState) -> str:
        """Determine the next node based on state."""
        if state.is_complete or not state.should_continue():
            return "end"
        return "extract_schema"
    
    def run(self, document: str) -> Dict[str, Any]:
        """Execute the schema extraction workflow."""
        initial_state = SchemaExtractionState(
            document=document,
            max_iterations=self.max_iterations
        )
        
        final_state = self.graph.invoke(initial_state)
        
        if not final_state.final_schema:
            raise ValueError(
                f"Schema extraction failed after {final_state.iteration_count} attempts. "
                f"Last feedback: {final_state.feedback}"
            )
        
        return final_state.final_schema 