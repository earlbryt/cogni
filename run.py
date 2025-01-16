from schema_extraction.schema_agent import SchemaAgent
from langchain_groq import ChatGroq
import json

def main():
    llm = ChatGroq(model_name="llama3-8b-8192")
    
    document = """William Ofosu Parwar - Academic CV..."""  # Your CV text here
    
    agent = SchemaAgent(llm)
    result = agent.run(document)
    
    print("\n=== Schema Structure ===")
    print(json.dumps(result["schema"], indent=2))
    
    print("\n=== Filled Schema ===")
    print(json.dumps(result["filled_schema"], indent=2))
    
    print("\n=== Validation Feedback ===")
    print(result["feedback"])

if __name__ == "__main__":
    main()



  
