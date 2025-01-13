import json
from typing import Tuple
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from schema_extraction.state import SchemaExtractionState
from dotenv import load_dotenv
import os

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize Groq LLM
llm = ChatGroq(model_name="llama3-8b-8192",)

EXTRACT_PROMPT = PromptTemplate.from_template("""
Analyze the following document and extract a JSON schema that represents its structure.
If feedback is provided, use it to improve the schema.

Document:
{document}

Previous Feedback (if any):
{feedback}

Output the schema in valid JSON format.
""")

VALIDATE_PROMPT = PromptTemplate.from_template("""
Review the following schema and provide specific feedback for improvement.
If the schema is valid and complete, respond with "APPROVED".

Schema:
{schema}

Provide your assessment:
""")

def extract_schema(state: SchemaExtractionState) -> Tuple[SchemaExtractionState, str]:
    """Extract or refine schema based on document and feedback."""
    try:
        prompt = EXTRACT_PROMPT.format(
            document=state.document,
            feedback=state.feedback or "No previous feedback"
        )
        
        response = llm.invoke(prompt)
        
        # Extract JSON from response
        schema_str = response.content
        schema = json.loads(schema_str)
        
        state.current_schema = schema
        state.iteration_count += 1
        
        return state, "validate_schema"
    except Exception as e:
        state.feedback = f"Error in extraction: {str(e)}"
        return state, "end"

def validate_schema(state: SchemaExtractionState) -> Tuple[SchemaExtractionState, str]:
    """Validate the current schema and provide feedback."""
    try:
        prompt = VALIDATE_PROMPT.format(
            schema=json.dumps(state.current_schema, indent=2)
        )
        
        response = llm.invoke(prompt)
        feedback = response.content.strip()
        
        if feedback == "APPROVED":
            state.final_schema = state.current_schema
            state.is_complete = True
            return state, "end"
        
        state.feedback = feedback
        return state, "extract_schema" if state.should_continue() else "end"
    
    except Exception as e:
        state.feedback = f"Error in validation: {str(e)}"
        return state, "end" 