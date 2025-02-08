from typing import Annotated, Dict, Any
from PyPDF2 import PdfReader
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langchain_core.messages import HumanMessage, AIMessage
from typing import TypedDict, List, Dict, Tuple
import operator
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import json
import os
from dotenv import load_dotenv
load_dotenv()

class AgentState(TypedDict):
    messages: List[str]
    current_pdf: str
    extracted_text: str
    schema: Dict[str, Any]

@tool
def extract_text_from_pdf(pdf_path: Annotated[str, "Path to the PDF file to extract text from"]) -> str:
    """
    Extract text from a PDF file using PyPDF2.
    Args:
        pdf_path: Path to the PDF file
    Returns:
        str: Extracted text from the PDF
    """
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        return f"Error extracting text from PDF: {str(e)}"

@tool
def extract_schema_from_text(text: Annotated[str, "Text to extract schema from"]) -> Dict[str, Any]:
    """
    Extract a JSON schema from the given text using LLM.
    Args:
        text: Text to analyze
    Returns:
        dict: Extracted JSON schema
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Warning: GROQ_API_KEY not found in environment variables")
        return {
            "type": "object",
            "properties": {},
            "error": "GROQ_API_KEY not found in environment variables"
        }
    
    print(f"Using API key: {api_key[:10]}...")  # Only print first 10 chars for security
    
    llm = ChatGroq(
        temperature=0.1,
        model_name="llama-3.3-70b-versatile",
        api_key=api_key
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a schema extraction expert. Analyze the given text and extract a JSON schema that represents the key fields and their types.
        IMPORTANT: Your response must be ONLY the JSON schema, with no additional text or explanations.
        
        Rules:
        1. Focus on identifying key fields that represent important information
        2. Infer appropriate data types (string, number, boolean, array, object)
        3. Use descriptive field names
        4. Include a brief description for each field
        5. The output must be valid JSON
        6. Do not include any text before or after the JSON
        
        Schema format must be exactly like this example:
        {{
            "type": "object",
            "properties": {{
                "fieldName": {{
                    "type": "string",
                    "description": "Description of the field"
                }}
            }},
            "required": ["fieldName"]
        }}"""),
        ("user", "Extract a JSON schema from this text. Remember to output ONLY the JSON schema, no other text:\n\n{text}")
    ])
    
    chain = prompt | llm
    
    try:
        result = chain.invoke({"text": text})
        schema_text = result.content.strip()
        
        # Clean up common issues that might break JSON parsing
        schema_text = schema_text.replace('```json', '').replace('```', '').strip()
        
        # If the response starts with any text before the JSON, find the first {
        if not schema_text.startswith('{'):
            start = schema_text.find('{')
            if start >= 0:
                schema_text = schema_text[start:]
        
        # If there's any text after the JSON, find the last }
        if not schema_text.endswith('}'):
            end = schema_text.rfind('}')
            if end >= 0:
                schema_text = schema_text[:end + 1]
        
        try:
            schema = json.loads(schema_text)
            
            # Validate schema structure
            if not isinstance(schema, dict):
                raise ValueError("Schema must be a dictionary")
            
            if "type" not in schema:
                schema["type"] = "object"
            
            if "properties" not in schema:
                schema["properties"] = {}
            
            return schema
            
        except json.JSONDecodeError as je:
            print(f"JSON Decode Error: {str(je)}")
            print(f"Attempted to parse: {schema_text}")
            return {
                "type": "object",
                "properties": {},
                "error": f"Failed to parse JSON: {str(je)}"
            }
            
    except Exception as e:
        print(f"Schema Extraction Error: {str(e)}")
        return {
            "type": "object",
            "properties": {},
            "error": f"Failed to extract schema: {str(e)}"
        }

def create_agent_workflow() -> StateGraph:
    """
    Create a workflow for the PDF processing and schema extraction agent
    """
    workflow = StateGraph(AgentState)
    
    # Define the processing node
    def process_node(state: AgentState) -> AgentState:
        # Update messages to indicate processing
        return {
            **state,
            "messages": state["messages"] + ["Processing complete"]
        }
    
    # Define the schema extraction node
    def extract_schema_node(state: AgentState) -> AgentState:
        if not state.get("extracted_text"):
            return {
                **state,
                "messages": state["messages"] + ["No text to extract schema from"],
                "schema": {}
            }
        
        schema = extract_schema_from_text(state["extracted_text"])
        return {
            **state,
            "messages": state["messages"] + ["Schema extraction complete"],
            "schema": schema
        }
    
    # Add nodes
    workflow.add_node("process", process_node)
    workflow.add_node("extract_schema", extract_schema_node)
    
    # Add edges
    workflow.add_edge("process", "extract_schema")
    workflow.add_edge("extract_schema", END)
    
    # Set entry point
    workflow.set_entry_point("process")
    
    return workflow

# Example usage
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    workflow = create_agent_workflow()
    # Initialize with an empty state
    initial_state = {
        "messages": [], 
        "current_pdf": "",
        "extracted_text": "",
        "schema": {}
    }
    # Run the workflow
    workflow.run(initial_state)