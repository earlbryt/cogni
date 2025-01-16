from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Dict, Any, Tuple
import json

VALIDATE_AND_FILL_PROMPT = """First validate this schema against the document, then fill it with values from the document.

Document:
{document}

Schema:
{schema}

Instructions:
1. First validate that the schema captures all important information
2. Then fill the schema with actual values from the document
3. Return a JSON object with two fields:
   - "validation": Your validation feedback (just "APPROVED" if perfect)
   - "filled_schema": The schema filled with actual values

Example response format:
{{
    "validation": "APPROVED",
    "filled_schema": {{
        "name": "John Doe",
        "contact": {{
            "email": "john@example.com"
        }},
        ...
    }}
}}"""

class ValidatorAgent:
    def __init__(self):
        self.llm = ChatGroq(model_name="llama3-8b-8192")
    
    def validate(self, document: str, schema: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Validate schema and fill with values from document."""
        messages = [
            SystemMessage(content="You are a data validation expert. Validate the schema and fill it with values."),
            HumanMessage(content=VALIDATE_AND_FILL_PROMPT.format(
                document=document,
                schema=json.dumps(schema, indent=2)
            ))
        ]
        
        print("\n=== Validator Response ===")
        response = self.llm.invoke(messages)
        print(response.content)
        print("=" * 50)
        
        try:
            # Clean the response
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            elif "{" in content:
                content = content[content.index("{"):content.rindex("}") + 1]
            
            content = content.strip()
            result = json.loads(content)
            
            # Return both validation feedback and filled schema
            return result["validation"], result["filled_schema"]
            
        except Exception as e:
            print(f"Error processing validator response: {str(e)}")
            return "Error in validation", {} 