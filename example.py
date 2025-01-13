import os
from dotenv import load_dotenv
from schema_extraction import SchemaExtractionWorkflow

def main():
    # Load environment variables
    load_dotenv()
    
    # Sample document
    document = """
    {
        "name": "John Doe",
        "age": 30,
        "address": {
            "street": "123 Main St",
            "city": "Springfield",
            "country": "USA"
        },
        "contacts": [
            {
                "type": "email",
                "value": "john@example.com"
            }
        ]
    }
    """
    
    # Initialize and run workflow
    workflow = SchemaExtractionWorkflow(max_iterations=3)
    
    try:
        schema = workflow.run(document)
        print("Extracted Schema:")
        print(schema)
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 