"""
Unified abstraction for saving agent results to files.

This module provides a ResultSaver class that handles:
- CSV file writing with automatic header management
- JSON file writing
- Text file writing (append or overwrite)
- Usage statistics tracking
- Reasoning text tracking
"""

import os
import json
import csv
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, asdict

try:
    from pydantic import BaseModel
except ImportError:
    BaseModel = None  # Pydantic not available


@dataclass
class UsageStats:
    """Standardized usage statistics from LLM API responses."""
    model_name: str
    input_tokens: int
    cached_tokens: int
    output_tokens: int
    reasoning_tokens: int
    total_tokens: int
    
    @classmethod
    def from_response_usage(cls, model_name: str, usage) -> "UsageStats":
        """Create UsageStats from API response usage object."""
        return cls(
            model_name=model_name,
            input_tokens=usage.input_tokens,
            cached_tokens=usage.input_tokens_details.cached_tokens if hasattr(usage.input_tokens_details, 'cached_tokens') else 0,
            output_tokens=usage.output_tokens,
            reasoning_tokens=usage.output_tokens_details.reasoning_tokens if hasattr(usage.output_tokens_details, 'reasoning_tokens') else 0,
            total_tokens=usage.total_tokens
        )


class ResultSaver:
    """
    Unified abstraction for saving agent results to files.
    
    Handles CSV, JSON, and text file operations with automatic directory creation
    and header management.
    """
    
    def __init__(self, output_dir: str):
        """
        Initialize ResultSaver with an output directory.
        
        Args:
            output_dir: Base directory for all output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._csv_headers_written = {}  # Track which CSV files have headers
    
    def save_json(
        self, 
        data: Union[Dict, BaseModel, Any], 
        filename: str,
        indent: int = 2
    ) -> Path:
        """
        Save data to a JSON file.
        
        Args:
            data: Data to save (dict, Pydantic model, or any JSON-serializable object)
            filename: Name of the JSON file (with or without .json extension)
            indent: JSON indentation level
            
        Returns:
            Path to the saved file
        """
        filepath = self.output_dir / filename
        # if not filepath.suffix:
        #     filepath = filepath.with_suffix('.json')
        
        # Handle Pydantic models
        if BaseModel is not None and isinstance(data, BaseModel):
            json_str = data.model_dump_json(indent=indent)
        else:
            json_str = json.dumps(data, indent=indent, ensure_ascii=False)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(json_str)
        
        return filepath
    
    def save_text(
        self, 
        content: str, 
        filename: str,
        mode: str = 'w'
    ) -> Path:
        """
        Save text content to a file.
        
        Args:
            content: Text content to save
            filename: Name of the text file
            mode: File mode ('w' for overwrite, 'a' for append)
            
        Returns:
            Path to the saved file
        """
        filepath = self.output_dir / filename
        
        with open(filepath, mode, encoding='utf-8') as f:
            f.write(content)
        
        return filepath
    
    def append_text(
        self, 
        content: str, 
        filename: str
    ) -> Path:
        """
        Append text content to a file.
        
        Args:
            content: Text content to append
            filename: Name of the text file
            
        Returns:
            Path to the file
        """
        return self.save_text(content, filename, mode='a')
    
    def save_csv_row(
        self,
        row: Dict[str, Any],
        filename: str,
        fieldnames: Optional[List[str]] = None
    ) -> Path:
        """
        Save a single row to a CSV file. Automatically writes header if file doesn't exist.
        
        Args:
            row: Dictionary with row data
            filename: Name of the CSV file (with or without .csv extension)
            fieldnames: Optional list of field names for header. If None, uses row keys.
            
        Returns:
            Path to the CSV file
        """
        filepath = self.output_dir / filename
        if not filepath.suffix:
            filepath = filepath.with_suffix('.csv')
        
        filepath_str = str(filepath)
        write_header = filepath_str not in self._csv_headers_written or not filepath.exists()
        
        if fieldnames is None:
            fieldnames = list(row.keys())
        
        mode = 'w' if write_header else 'a'
        
        with open(filepath, mode, newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
                self._csv_headers_written[filepath_str] = True
        
        # Append the row
        with open(filepath, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerow(row)
        
        return filepath
    
    def save_csv_rows(
        self,
        rows: List[Dict[str, Any]],
        filename: str,
        fieldnames: Optional[List[str]] = None
    ) -> Path:
        """
        Save multiple rows to a CSV file. Automatically writes header if file doesn't exist.
        
        Args:
            rows: List of dictionaries with row data
            filename: Name of the CSV file (with or without .csv extension)
            fieldnames: Optional list of field names for header. If None, uses keys from first row.
            
        Returns:
            Path to the CSV file
        """
        if not rows:
            raise ValueError("Cannot save empty list of rows")
        
        filepath = self.output_dir / filename
        if not filepath.suffix:
            filepath = filepath.with_suffix('.csv')
        
        filepath_str = str(filepath)
        write_header = filepath_str not in self._csv_headers_written or not filepath.exists()
        
        if fieldnames is None:
            fieldnames = list(rows[0].keys())
        
        mode = 'w' if write_header else 'a'
        
        with open(filepath, mode, newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
                self._csv_headers_written[filepath_str] = True
            
            writer.writerows(rows)
        
        return filepath
    
    def save_usage_stats(
        self,
        usage: UsageStats,
        filename: str = "usage.csv",
        additional_fields: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Save usage statistics to a CSV file.
        
        Args:
            usage: UsageStats object
            filename: Name of the CSV file (default: "usage.csv")
            additional_fields: Optional dictionary of additional fields to include in the row
            
        Returns:
            Path to the CSV file
        """
        row = {
            'model_name': usage.model_name,
            'input_tokens': usage.input_tokens,
            'cached_tokens': usage.cached_tokens,
            'output_tokens': usage.output_tokens,
            'reasoning_tokens': usage.reasoning_tokens,
            'total_tokens': usage.total_tokens
        }
        
        if additional_fields:
            row.update(additional_fields)
        
        fieldnames = list(row.keys())
        
        return self.save_csv_row(row, filename, fieldnames=fieldnames)
    
    def save_reasoning(
        self,
        reasoning: str,
        filename: str = "reasoning.txt",
        prefix: Optional[str] = None
    ) -> Path:
        """
        Save or append reasoning text to a file.
        
        Args:
            reasoning: Reasoning text to save
            filename: Name of the text file (default: "reasoning.txt")
            prefix: Optional prefix to add before the reasoning (e.g., "---peripheral_register---")
            
        Returns:
            Path to the file
        """
        content = ""
        if prefix:
            content += f"{prefix}\n"
        content += f"{reasoning}\n\n"
        
        return self.append_text(content, filename)
    
    def get_path(self, filename: str) -> Path:
        """
        Get the full path for a filename in the output directory.
        
        Args:
            filename: Name of the file
            
        Returns:
            Full Path object
        """
        return self.output_dir / filename
    
    def exists(self, filename: str) -> bool:
        """
        Check if a file exists in the output directory.
        
        Args:
            filename: Name of the file
            
        Returns:
            True if file exists, False otherwise
        """
        return self.get_path(filename).exists()

