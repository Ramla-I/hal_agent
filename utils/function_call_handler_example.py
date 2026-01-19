"""
Example usage of the FunctionCallHandler abstraction.

This demonstrates how to:
1. Register functions with parameter schemas
2. Process function calls from agent responses
3. Handle results and errors
"""

from function_call_handler import FunctionCallHandler, ParameterSchema


# Example 1: Simple function
def add_numbers(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


# Example 2: Function with validation
def divide_numbers(numerator: float, denominator: float) -> float:
    """Divide two numbers."""
    if denominator == 0:
        raise ValueError("Cannot divide by zero")
    return numerator / denominator


# Example 3: Using calculate_address_offset
def setup_calculate_address_offset_handler():
    """Set up handler with calculate_address_offset function."""
    from agent_tools.tools import calculate_address_offset
    from function_call_handler import create_default_handler
    
    # Option 1: Use the convenience function
    handler = create_default_handler()
    return handler
    
    # Option 2: Register manually
    # handler = FunctionCallHandler()
    # handler.register_function(
    #     name="calculate_address_offset",
    #     function=calculate_address_offset,
    #     parameters=[
    #         ParameterSchema("base_address_in_hex", str, required=True),
    #         ParameterSchema("start_register_number", int, required=True),
    #         ParameterSchema("register_number", int, required=True),
    #         ParameterSchema("register_size_in_bytes", int, required=True),
    #     ]
    # )
    # return handler


# Example 4: Custom handler with multiple functions
def create_custom_handler():
    """Create a handler with multiple registered functions."""
    handler = FunctionCallHandler()
    
    # Register add_numbers
    handler.register_function(
        name="add_numbers",
        function=add_numbers,
        parameters=[
            ParameterSchema("a", int, required=True),
            ParameterSchema("b", int, required=True),
        ]
    )
    
    # Register divide_numbers with custom validator
    def validate_denominator(value: float) -> bool:
        return value != 0
    
    handler.register_function(
        name="divide_numbers",
        function=divide_numbers,
        parameters=[
            ParameterSchema("numerator", float, required=True),
            ParameterSchema("denominator", float, required=True, validator=validate_denominator),
        ]
    )
    
    return handler


# Example 5: Processing function calls
def example_usage():
    """Example of how to use the handler in your agent loop."""
    handler = create_custom_handler()
    
    # Simulate agent response with function calls
    response_text = """
    I need to perform some calculations.
    
    ```function_call
    {
        "function_calls": [
            {
                "name": "add_numbers",
                "parameters": {
                    "a": 5,
                    "b": 3
                }
            },
            {
                "name": "divide_numbers",
                "parameters": {
                    "numerator": 10,
                    "denominator": 2
                }
            }
        ]
    }
    ```
    """
    
    # Process function calls
    results = handler.process_function_calls(response_text)
    
    # Handle results
    for result in results:
        if result.success:
            print(f"✓ {result.function_name} succeeded: {result.result}")
            print(f"  Message: {result.message}")
        else:
            print(f"✗ {result.function_name} failed: {result.error_message}")
            print(f"  Message: {result.message}")
    
    return results


if __name__ == "__main__":
    example_usage()

