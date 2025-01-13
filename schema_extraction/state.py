from typing import Optional, Dict, Any
from dataclasses import dataclass, field

@dataclass
class SchemaExtractionState:
    """State container for the schema extraction workflow."""
    
    # Input document to process
    document: str
    
    # Current schema attempt (JSON format)
    current_schema: Optional[Dict[str, Any]] = None
    
    # Validation feedback from the last attempt
    feedback: Optional[str] = None
    
    # Number of refinement attempts made
    iteration_count: int = 0
    
    # Maximum number of allowed iterations
    max_iterations: int = field(default=3)
    
    # Final validated schema
    final_schema: Optional[Dict[str, Any]] = None
    
    # Workflow status
    is_complete: bool = False
    
    def should_continue(self) -> bool:
        """Determine if the workflow should continue iterating."""
        return (
            not self.is_complete 
            and self.iteration_count < self.max_iterations
        ) 