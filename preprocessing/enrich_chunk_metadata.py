#!/usr/bin/env python3
"""
Enrich chunk metadata for vector store uploads.

This script analyzes existing chunks and extracts rich metadata including:
- Section hierarchy
- Peripheral and register mentions
- Content type classification
- Keywords and topics
- Importance scoring
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
import tiktoken

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI
from config import client_openai
from utils.utils import setup_logger

logger = setup_logger(__name__)

@dataclass
class ChunkMetadata:
    """Rich metadata for a single chunk"""
    chunk_id: str
    page: int
    chunk_number: int  # chunk number on that page

    # Hierarchical context
    chapter: Optional[str] = None
    section: Optional[str] = None
    subsection: Optional[str] = None

    # Content classification
    peripheral: Optional[str] = None
    registers_mentioned: List[str] = None
    fields_mentioned: List[str] = None

    # Content type
    chunk_type: str = "general"  # general, register_description, register_table, overview, example
    has_tables: bool = False
    has_code_examples: bool = False
    has_diagrams: bool = False

    # Semantic information
    keywords: List[str] = None
    topics: List[str] = None
    description: Optional[str] = None  # One-sentence summary

    # Quality metrics
    importance: str = "medium"  # low, medium, high, critical
    completeness: str = "complete"  # complete, partial, fragment

    # Token counts
    token_count: int = 0

    def __post_init__(self):
        if self.registers_mentioned is None:
            self.registers_mentioned = []
        if self.fields_mentioned is None:
            self.fields_mentioned = []
        if self.keywords is None:
            self.keywords = []
        if self.topics is None:
            self.topics = []

def parse_chunk_id(filename: str) -> tuple[str, int, int]:
    """
    Parse chunk filename to extract document, page, and chunk number.

    Example: rm0041_p187_c01.txt -> (rm0041, 187, 1)
    """
    match = re.match(r'(\w+)_p(\d+)_c(\d+)', filename)
    if match:
        doc_id = match.group(1)
        page = int(match.group(2))
        chunk_num = int(match.group(3))
        return doc_id, page, chunk_num
    return filename, 0, 0

def extract_section_hierarchy(content: str) -> Dict[str, Optional[str]]:
    """
    Extract chapter/section/subsection from markdown headers.

    Assumes structure like:
    # Chapter Title
    ## Section Title
    ### Subsection Title
    """
    lines = content.split('\n')

    chapter = None
    section = None
    subsection = None

    for line in lines:
        line = line.strip()
        if line.startswith('# ') and not line.startswith('## '):
            chapter = line.lstrip('#').strip()
        elif line.startswith('## ') and not line.startswith('### '):
            section = line.lstrip('#').strip()
        elif line.startswith('### '):
            subsection = line.lstrip('#').strip()

    return {
        'chapter': chapter,
        'section': section,
        'subsection': subsection
    }

def extract_register_mentions(content: str) -> tuple[List[str], List[str]]:
    """
    Extract register names and field names mentioned in content.

    Looks for patterns like:
    - AFIO_EXTICR1, GPIO_CRL, TIM2_CR1
    - EXTI0, SWJ_CFG, CNT[15:0]
    """
    registers = set()
    fields = set()

    # Register pattern: PERIPHERAL_REGISTERNAME
    register_pattern = r'\b([A-Z][A-Z0-9]*_[A-Z][A-Z0-9_]*)\b'
    for match in re.finditer(register_pattern, content):
        reg_name = match.group(1)
        # Filter out common false positives
        if reg_name not in ['GPIO_Pin', 'HAL_OK', 'HAL_ERROR']:
            registers.add(reg_name)

    # Field pattern: fieldname or fieldname[bits]
    field_pattern = r'\b([A-Z][A-Z0-9_]{2,})(?:\[\d+:\d+\]|\[\d+\])?\b'
    for match in re.finditer(field_pattern, content):
        field_name = match.group(1)
        # Only add if not already captured as register and is reasonably short
        if field_name not in registers and len(field_name) <= 20:
            # Filter common abbreviations that aren't fields
            if field_name not in ['GPIO', 'AFIO', 'TIM', 'USART', 'SPI', 'I2C', 'ADC', 'DMA']:
                fields.add(field_name)

    return sorted(list(registers)), sorted(list(fields))

def detect_content_features(content: str) -> Dict[str, bool]:
    """Detect presence of tables, code examples, diagrams."""
    has_tables = bool(re.search(r'\|.*\|.*\|', content))  # Markdown table
    has_code = bool(re.search(r'```', content))  # Code block
    has_diagram_ref = bool(re.search(r'(Figure|Diagram|Fig\.)\s+\d+', content, re.IGNORECASE))

    return {
        'has_tables': has_tables,
        'has_code_examples': has_code,
        'has_diagrams': has_diagram_ref
    }

def classify_chunk_type(content: str, section: Optional[str], has_tables: bool) -> str:
    """
    Classify chunk into one of several types.

    Types:
    - register_table: Contains register bit field table
    - register_description: Describes a specific register
    - overview: High-level peripheral overview
    - example: Contains code examples
    - general: Other content
    """
    content_lower = content.lower()

    # Check for code examples
    if '```' in content or 'example' in content_lower:
        return 'example'

    # Check for register tables (has table + mentions bits/fields)
    if has_tables and any(word in content_lower for word in ['bit', 'field', 'offset', 'reset value']):
        return 'register_table'

    # Check for register descriptions
    if any(word in content_lower for word in ['register', 'bit field', 'configuration']):
        if section and 'register' in section.lower():
            return 'register_description'

    # Check for overview sections
    if any(word in content_lower for word in ['overview', 'introduction', 'functional description']):
        return 'overview'

    return 'general'

def extract_keywords(content: str, max_keywords: int = 10) -> List[str]:
    """
    Extract important keywords from content.
    Simple frequency-based approach for now.
    """
    # Remove common words
    stopwords = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
        'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
        'that', 'these', 'those', 'it', 'its', 'which', 'what', 'where'
    }

    # Extract words (alphanumeric + underscores)
    words = re.findall(r'\b[a-z_][a-z0-9_]{2,}\b', content.lower())

    # Count frequencies
    word_freq = {}
    for word in words:
        if word not in stopwords and len(word) >= 3:
            word_freq[word] = word_freq.get(word, 0) + 1

    # Get top N
    top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in top_words[:max_keywords]]

def assess_importance(content: str, chunk_type: str, num_registers: int) -> str:
    """
    Assess importance of chunk.

    Factors:
    - Chunk type (register_table > register_description > overview > general)
    - Number of registers mentioned
    - Content length
    - Presence of critical keywords
    """
    score = 0

    # Type-based scoring
    type_scores = {
        'register_table': 3,
        'register_description': 2,
        'example': 2,
        'overview': 1,
        'general': 0
    }
    score += type_scores.get(chunk_type, 0)

    # Register count
    if num_registers >= 3:
        score += 2
    elif num_registers >= 1:
        score += 1

    # Critical keywords
    critical_words = ['reset value', 'address offset', 'configuration', 'control', 'status']
    if any(word in content.lower() for word in critical_words):
        score += 1

    # Map score to importance
    if score >= 5:
        return 'critical'
    elif score >= 3:
        return 'high'
    elif score >= 1:
        return 'medium'
    else:
        return 'low'

def count_tokens(content: str) -> int:
    """Count tokens using tiktoken."""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(content))
    except Exception as e:
        logger.warning(f"Could not count tokens: {e}")
        return 0

def generate_description(content: str, chunk_type: str) -> str:
    """
    Generate a one-sentence description of the chunk.
    Uses simple heuristics for now.
    """
    # Get first meaningful sentence
    sentences = re.split(r'[.!?]\s+', content)

    for sentence in sentences:
        sentence = sentence.strip()
        # Skip headers and very short sentences
        if len(sentence) > 30 and not sentence.startswith('#'):
            # Truncate if too long
            if len(sentence) > 150:
                sentence = sentence[:147] + '...'
            return sentence

    # Fallback
    return f"{chunk_type.replace('_', ' ').title()} content"

def enrich_single_chunk(
    chunk_path: Path,
    chunk_content: str,
    use_llm: bool = False
) -> ChunkMetadata:
    """
    Analyze a single chunk and generate rich metadata.

    Args:
        chunk_path: Path to chunk file
        chunk_content: Content of the chunk
        use_llm: If True, use LLM for more accurate extraction (slower)
    """
    filename = chunk_path.stem  # Without extension
    doc_id, page, chunk_num = parse_chunk_id(filename)

    # Basic extraction
    hierarchy = extract_section_hierarchy(chunk_content)
    registers, fields = extract_register_mentions(chunk_content)
    features = detect_content_features(chunk_content)
    chunk_type = classify_chunk_type(
        chunk_content,
        hierarchy['section'],
        features['has_tables']
    )
    keywords = extract_keywords(chunk_content)
    importance = assess_importance(chunk_content, chunk_type, len(registers))
    description = generate_description(chunk_content, chunk_type)
    token_count = count_tokens(chunk_content)

    # Detect peripheral from section or registers
    peripheral = None
    if hierarchy['section']:
        # Extract peripheral name from section like "9.4 AFIO Registers"
        match = re.search(r'\b([A-Z]{3,})\b', hierarchy['section'])
        if match:
            peripheral = match.group(1)

    if not peripheral and registers:
        # Extract from first register name (e.g., AFIO_EXTICR1 -> AFIO)
        first_reg = registers[0]
        if '_' in first_reg:
            peripheral = first_reg.split('_')[0]

    # Assess completeness
    completeness = 'complete'
    if token_count < 200:
        completeness = 'fragment'
    elif not hierarchy['section'] and not registers:
        completeness = 'partial'

    metadata = ChunkMetadata(
        chunk_id=filename,
        page=page,
        chunk_number=chunk_num,
        chapter=hierarchy['chapter'],
        section=hierarchy['section'],
        subsection=hierarchy['subsection'],
        peripheral=peripheral,
        registers_mentioned=registers,
        fields_mentioned=fields[:20],  # Limit field list
        chunk_type=chunk_type,
        has_tables=features['has_tables'],
        has_code_examples=features['has_code_examples'],
        has_diagrams=features['has_diagrams'],
        keywords=keywords,
        topics=[],  # Could be filled by LLM
        description=description,
        importance=importance,
        completeness=completeness,
        token_count=token_count
    )

    return metadata

def enrich_chunk_directory(
    chunks_dir: Path,
    output_dir: Path,
    use_llm: bool = False,
    file_extension: str = '.txt'
) -> Dict[str, ChunkMetadata]:
    """
    Process all chunks in a directory and generate metadata.

    Args:
        chunks_dir: Directory containing chunk files
        output_dir: Directory to save metadata files
        use_llm: Whether to use LLM for enhanced extraction
        file_extension: Extension of chunk files (.txt or .md)

    Returns:
        Dictionary mapping chunk_id to ChunkMetadata
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    chunk_files = sorted(chunks_dir.glob(f'*{file_extension}'))
    logger.info(f"Found {len(chunk_files)} chunk files in {chunks_dir}")

    all_metadata = {}

    for i, chunk_path in enumerate(chunk_files, 1):
        logger.info(f"Processing {i}/{len(chunk_files)}: {chunk_path.name}")

        try:
            # Read chunk content
            with open(chunk_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Generate metadata
            metadata = enrich_single_chunk(chunk_path, content, use_llm)
            all_metadata[metadata.chunk_id] = metadata

            # Save individual metadata file
            metadata_file = output_dir / f"{metadata.chunk_id}_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(metadata), f, indent=2)

        except Exception as e:
            logger.error(f"Error processing {chunk_path.name}: {e}")
            continue

    # Save combined metadata file
    combined_file = output_dir / "all_metadata.json"
    with open(combined_file, 'w', encoding='utf-8') as f:
        json.dump(
            {k: asdict(v) for k, v in all_metadata.items()},
            f,
            indent=2
        )

    logger.info(f"Processed {len(all_metadata)} chunks")
    logger.info(f"Metadata saved to {output_dir}")

    return all_metadata

def generate_metadata_summary(metadata_dict: Dict[str, ChunkMetadata]) -> Dict:
    """Generate summary statistics about the metadata."""
    summary = {
        'total_chunks': len(metadata_dict),
        'by_type': {},
        'by_importance': {},
        'by_peripheral': {},
        'total_registers': 0,
        'unique_registers': set(),
        'avg_tokens': 0,
        'chunks_with_tables': 0,
        'chunks_with_code': 0,
    }

    for metadata in metadata_dict.values():
        # Count by type
        summary['by_type'][metadata.chunk_type] = \
            summary['by_type'].get(metadata.chunk_type, 0) + 1

        # Count by importance
        summary['by_importance'][metadata.importance] = \
            summary['by_importance'].get(metadata.importance, 0) + 1

        # Count by peripheral
        if metadata.peripheral:
            summary['by_peripheral'][metadata.peripheral] = \
                summary['by_peripheral'].get(metadata.peripheral, 0) + 1

        # Register stats
        summary['total_registers'] += len(metadata.registers_mentioned)
        summary['unique_registers'].update(metadata.registers_mentioned)

        # Feature counts
        if metadata.has_tables:
            summary['chunks_with_tables'] += 1
        if metadata.has_code_examples:
            summary['chunks_with_code'] += 1

        # Token average
        summary['avg_tokens'] += metadata.token_count

    summary['avg_tokens'] = summary['avg_tokens'] // len(metadata_dict) if metadata_dict else 0
    summary['unique_registers'] = len(summary['unique_registers'])

    return summary

def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Enrich chunk metadata')
    parser.add_argument('chunks_dir', type=str, help='Directory containing chunks')
    parser.add_argument('--output-dir', type=str, help='Output directory for metadata')
    parser.add_argument('--extension', type=str, default='.txt', help='Chunk file extension')
    parser.add_argument('--use-llm', action='store_true', help='Use LLM for enhanced extraction')

    args = parser.parse_args()

    chunks_dir = Path(args.chunks_dir)
    output_dir = Path(args.output_dir) if args.output_dir else chunks_dir / 'metadata'

    if not chunks_dir.exists():
        logger.error(f"Chunks directory not found: {chunks_dir}")
        return 1

    logger.info("Starting chunk metadata enrichment")
    logger.info(f"Chunks directory: {chunks_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"File extension: {args.extension}")
    logger.info(f"Use LLM: {args.use_llm}")

    # Process chunks
    metadata_dict = enrich_chunk_directory(
        chunks_dir,
        output_dir,
        use_llm=args.use_llm,
        file_extension=args.extension
    )

    # Generate and save summary
    summary = generate_metadata_summary(metadata_dict)

    # Convert set to count for JSON serialization
    summary_serializable = {k: (v if not isinstance(v, set) else len(v))
                           for k, v in summary.items()}

    summary_file = output_dir / "metadata_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary_serializable, f, indent=2)

    # Print summary
    print("\n" + "="*80)
    print("METADATA ENRICHMENT SUMMARY")
    print("="*80)
    print(f"\nTotal chunks processed: {summary['total_chunks']}")
    print(f"\nBy chunk type:")
    for chunk_type, count in sorted(summary['by_type'].items()):
        print(f"  {chunk_type:20s}: {count:4d}")

    print(f"\nBy importance:")
    for importance, count in sorted(summary['by_importance'].items()):
        print(f"  {importance:20s}: {count:4d}")

    print(f"\nBy peripheral:")
    for peripheral, count in sorted(summary['by_peripheral'].items()):
        print(f"  {peripheral:20s}: {count:4d}")

    print(f"\nContent features:")
    print(f"  Chunks with tables: {summary['chunks_with_tables']}")
    print(f"  Chunks with code: {summary['chunks_with_code']}")

    print(f"\nRegister mentions:")
    print(f"  Total mentions: {summary['total_registers']}")
    print(f"  Unique registers: {summary['unique_registers']}")

    print(f"\nToken statistics:")
    print(f"  Average tokens per chunk: {summary['avg_tokens']}")

    print(f"\nMetadata saved to: {output_dir}")
    print("="*80)

    return 0

if __name__ == "__main__":
    sys.exit(main())
