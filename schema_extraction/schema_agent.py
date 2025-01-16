from langgraph.graph import END, START, StateGraph
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from typing import TypedDict, Annotated, List, Dict, Any
import operator
from dotenv import load_dotenv
import os
import json
from .validator_agent import ValidatorAgent

load_dotenv()

# Define the state
class State(TypedDict):
    messages: Annotated[List[HumanMessage], operator.add]
    document: str
    current_schema: Dict[str, Any]
    feedback: str
    iteration: int
    max_iterations: int
    iteration_schemas: List[Dict[str, Any]]
    iteration_feedbacks: List[str]

# System prompt and LLM setup
SYSTEM_PROMPT = """You are a schema extraction expert. Your task is to create a detailed JSON schema from documents.
Follow these rules:
1. Extract all important fields and their types
2. Maintain proper JSON structure
3. Include all relevant sections and subsections
4. Use descriptive field names
5. If feedback is provided, incorporate it to improve the schema

Current feedback to address:
{feedback}
"""

EXTRACT_PROMPT = """Extract a detailed JSON schema from this document. Include all important information, nested structures, and proper data types.

Document:
{document}

IMPORTANT: 
1. Respond ONLY with valid JSON
2. Do not include any explanatory text
3. The response must start with {{ and end with }}
4. Include all necessary fields and their types
5. Use proper JSON syntax

Example format:
{{
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {{
        "name": {{"type": "string"}},
        ...
    }}
}}"""

# Add llm initialization back
llm = ChatGroq(model_name="llama3-8b-8192")

class SchemaAgent:
    def __init__(self, llm, max_iterations: int = 3):
        self.llm = llm
        self.validator = ValidatorAgent()
        self.max_iterations = max_iterations
        
        workflow = StateGraph(State)
        workflow.add_node("extract_schema", self.extract_schema)
        workflow.add_node("validate_schema", self.validate_schema)
        
        workflow.add_edge("extract_schema", "validate_schema")
        workflow.add_conditional_edges(
            "validate_schema",
            self._get_next_node,
            {
                "extract_schema": "extract_schema",
                "end": END
            }
        )
        
        workflow.set_entry_point("extract_schema")
        self.app = workflow.compile()
    
    def extract_schema(self, state: State) -> State:
        """Extract or refine schema based on document and feedback."""
        messages = [
            SystemMessage(content=SYSTEM_PROMPT.format(feedback=state["feedback"])),
            HumanMessage(content=EXTRACT_PROMPT.format(document=state["document"]))
        ]
        
        print("\n=== Raw LLM Response ===")
        response = self.llm.invoke(messages)
        print(response.content)
        print("=" * 50)
        
        try:
            # Clean the response to ensure it's valid JSON
            content = response.content.strip()
            
            # Remove any prefixed text before the JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            elif "{" in content:
                # Extract content between first { and last }
                content = content[content.index("{"):content.rindex("}") + 1]
            
            content = content.strip()
            
            # Validate JSON structure
            if not (content.startswith("{") and content.endswith("}")):
                raise json.JSONDecodeError("Invalid JSON structure", content, 0)
            
            state["current_schema"] = json.loads(content)
            print("\nSuccessfully parsed schema")
            
        except json.JSONDecodeError as e:
            print(f"\nJSON Decode Error: {str(e)}")
            print(f"Content that failed to parse: {content}")
            state["feedback"] = f"Error: Invalid JSON schema produced - {str(e)}"
            state["current_schema"] = {}
        except Exception as e:
            print(f"\nError: {str(e)}")
            state["feedback"] = f"Error: {str(e)}"
            state["current_schema"] = {}
            
        state["iteration"] += 1
        state["iteration_schemas"].append(state["current_schema"].copy())
        return state
    
    def validate_schema(self, state: State) -> State:
        """Validate current schema against original document."""
        if not state["current_schema"]:
            state["feedback"] = "Error: No valid schema was produced"
            state["filled_schema"] = {}
            return state
            
        feedback, filled_schema = self.validator.validate(
            document=state["document"],
            schema=state["current_schema"]
        )
        
        state["feedback"] = feedback
        state["filled_schema"] = filled_schema
        state["iteration_feedbacks"].append(state["feedback"])
        return state
    
    def _get_next_node(self, state: State) -> str:
        """Determine next node based on validation feedback and iteration count."""
        if state["feedback"] == "APPROVED":
            return "end"
        if state["iteration"] >= state["max_iterations"]:
            return "end"
        return "extract_schema"
    
    def run(self, document: str) -> Dict[str, Any]:
        """Execute the schema extraction workflow."""
        initial_state = {
            "messages": [],
            "document": document,
            "current_schema": {},
            "feedback": "",
            "filled_schema": {},
            "iteration": 0,
            "max_iterations": self.max_iterations,
            "iteration_schemas": [],
            "iteration_feedbacks": []
        }
        
        final_state = self.app.invoke(initial_state)
        
        return {
            "schema": final_state["current_schema"],
            "filled_schema": final_state.get("filled_schema", {}),
            "feedback": final_state["feedback"],
            "iterations": final_state["iteration"],
            "iteration_schemas": final_state["iteration_schemas"],
            "iteration_feedbacks": final_state["iteration_feedbacks"]
        } 