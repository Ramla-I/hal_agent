"""
Function call abstraction for parsing, validating, and executing agent function calls.
"""
import json
from typing import Callable, Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import os
import sys

# HACK, remove this once we have a proper package structure
# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)
from utils.parse_output import get_function_calls_from_response


@dataclass
class FunctionCallResult:
    """Result of executing a function call."""
    success: bool
    function_name: str
    result: Any = None
    error_message: str = ""
    message: str = ""


@dataclass
class ParameterSchema:
    """Schema definition for a function parameter."""
    name: str
    param_type: type
    required: bool = True
    validator: Optional[Callable[[Any], bool]] = None


class FunctionCallHandler:
    """
    Abstraction for handling function calls from agent responses.
    
    Usage:
        handler = FunctionCallHandler()
        
        # Register a function
        handler.register_function(
            name="calculate_address_offset",
            function=calculate_address_offset,
            parameters=[
                ParameterSchema("base_address_in_hex", str, required=True),
                ParameterSchema("start_register_number", int, required=True),
                ParameterSchema("register_number", int, required=True),
                ParameterSchema("register_size_in_bytes", int, required=True),
            ]
        )
        
        # Process function calls from response
        results = handler.process_function_calls(response_text)
        for result in results:
            if result.success:
                print(f"Result: {result.result}")
            else:
                print(f"Error: {result.error_message}")
    """
    
    def __init__(self):
        self._functions: Dict[str, Callable] = {}
        self._schemas: Dict[str, List[ParameterSchema]] = {}
    
    def register_function(
        self,
        name: str,
        function: Callable,
        parameters: List[ParameterSchema]
    ):
        """
        Register a function with its parameter schema.
        
        Args:
            name: The name of the function (must match what the agent calls)
            function: The actual Python function to execute
            parameters: List of ParameterSchema objects defining the parameters
        """
        self._functions[name] = function
        self._schemas[name] = parameters
    
    def validate_parameters(
        self,
        function_name: str,
        arguments: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that the provided arguments match the function's schema.
        
        Args:
            function_name: Name of the function
            arguments: Dictionary of argument name -> value
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if function_name not in self._schemas:
            return False, f"Function '{function_name}' is not registered"
        
        schema = self._schemas[function_name]
        
        # Check required parameters
        for param in schema:
            if param.required and param.name not in arguments:
                return False, f"Missing required parameter: {param.name}"
        
        # Check parameter types and validators
        for param in schema:
            if param.name in arguments:
                value = arguments[param.name]
                
                # Type checking
                if not isinstance(value, param.param_type):
                    # Try to convert if possible
                    try:
                        if param.param_type == int:
                            arguments[param.name] = int(value)
                        elif param.param_type == float:
                            arguments[param.name] = float(value)
                        elif param.param_type == str:
                            arguments[param.name] = str(value)
                        else:
                            return False, f"Parameter '{param.name}' has wrong type. Expected {param.param_type.__name__}, got {type(value).__name__}"
                    except (ValueError, TypeError):
                        return False, f"Parameter '{param.name}' cannot be converted to {param.param_type.__name__}"
                
                # Normalize string parameters (e.g., remove spaces from hex strings)
                if param.param_type == str and isinstance(arguments[param.name], str):
                    # Remove spaces from hex-like strings for consistency
                    if "hex" in param.name.lower() or arguments[param.name].strip().startswith("0x"):
                        arguments[param.name] = arguments[param.name].replace(" ", "")
                
                # Custom validator
                if param.validator and not param.validator(arguments[param.name]):
                    return False, f"Parameter '{param.name}' failed validation"
        
        return True, None
    
    def execute_function(
        self,
        function_name: str,
        arguments: Dict[str, Any]
    ) -> FunctionCallResult:
        """
        Execute a function call with validated arguments.
        
        Args:
            function_name: Name of the function to execute
            arguments: Dictionary of argument name -> value
            
        Returns:
            FunctionCallResult with success status and result or error message
        """
        if function_name not in self._functions:
            return FunctionCallResult(
                success=False,
                function_name=function_name,
                error_message=f"Function '{function_name}' is not registered",
                message=f"The function call {function_name} is not registered. Please check the function name."
            )
        
        # Validate parameters
        is_valid, error_msg = self.validate_parameters(function_name, arguments)
        if not is_valid:
            return FunctionCallResult(
                success=False,
                function_name=function_name,
                error_message=error_msg or "Parameter validation failed",
                message=f"The function call {function_name} with parameters {arguments} is not valid. {error_msg}. Please check the parameters. Return whatever information you can for the register without this function call."
            )
        
        # Execute the function
        try:
            func = self._functions[function_name]
            result = func(**arguments)
            
            return FunctionCallResult(
                success=True,
                function_name=function_name,
                result=result,
                message=f"The result of the function call {function_name} with parameters {arguments} is {result}"
            )
        except Exception as e:
            return FunctionCallResult(
                success=False,
                function_name=function_name,
                error_message=str(e),
                message=f"Error executing function call {function_name} with parameters {arguments}: {str(e)}. Return whatever information you can for the register without this function call."
            )
    
    def process_function_calls(
        self,
        response_text: str
    ) -> List[FunctionCallResult]:
        """
        Parse function calls from response text and execute them.
        
        Args:
            response_text: The agent's response text containing function calls
            
        Returns:
            List of FunctionCallResult objects, one for each function call
        """
        function_calls_text = get_function_calls_from_response(response_text)
        if not function_calls_text:
            return []
        
        try:
            function_calls_data = json.loads(function_calls_text)
        except json.JSONDecodeError as e:
            return [FunctionCallResult(
                success=False,
                function_name="unknown",
                error_message=f"Failed to parse function calls JSON: {str(e)}",
                message=f"Failed to parse function calls from response: {str(e)}"
            )]
        
        # Handle both single function call and list of function calls
        if "function_calls" in function_calls_data:
            function_calls = function_calls_data["function_calls"]
        elif isinstance(function_calls_data, list):
            function_calls = function_calls_data
        elif isinstance(function_calls_data, dict) and "name" in function_calls_data:
            function_calls = [function_calls_data]
        else:
            return [FunctionCallResult(
                success=False,
                function_name="unknown",
                error_message="Invalid function call format",
                message="Invalid function call format in response"
            )]
        
        results = []
        for function_call in function_calls:
            if not isinstance(function_call, dict):
                results.append(FunctionCallResult(
                    success=False,
                    function_name="unknown",
                    error_message="Function call must be a dictionary",
                    message="Invalid function call format: expected dictionary"
                ))
                continue
            
            function_name = function_call.get("name")
            parameters = function_call.get("parameters", {})
            
            if not function_name:
                results.append(FunctionCallResult(
                    success=False,
                    function_name="unknown",
                    error_message="Function call missing 'name' field",
                    message="Function call missing 'name' field"
                ))
                continue
            
            result = self.execute_function(function_name, parameters)
            results.append(result)
        
        return results


def create_default_handler() -> FunctionCallHandler:
    """
    Create a FunctionCallHandler with calculate_address_offset registered.
    This is a convenience function for common use cases.
    """
    from agent_tools.tools import calculate_address_offset
    
    handler = FunctionCallHandler()
    handler.register_function(
        name="calculate_address_offset",
        function=calculate_address_offset,
        parameters=[
            ParameterSchema("base_address_in_hex", str, required=True),
            ParameterSchema("start_register_number", int, required=True),
            ParameterSchema("register_number", int, required=True),
            ParameterSchema("register_size_in_bytes", int, required=True),
        ]
    )
    return handler
