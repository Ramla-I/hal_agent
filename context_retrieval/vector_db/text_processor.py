"""Text/Markdown processing with preprocessing, chunking, and enriched metadata.

Extends the base TextProcessor with:
- Page number tracking from RM-style page headers
- Register name expansion (e.g., BKP_DRx (x=1..20) -> BKP_DR1..BKP_DR20)
- has_tables and registers_mentioned in chunk metadata
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from context_retrieval.vector_db import config
from context_retrieval.vector_db.chunking import count_tokens, split_text_recursive, add_overlap


class TextProcessor:
    """Process text/markdown files: clean, chunk, and add enriched metadata."""

    # Patterns for STM reference manual headers/footers
    HEADER_PATTERNS = [
        r'^\d+/\d+\s+RM\d+\s+Rev\s+\d+\s*$',  # "612/709 RM0041 Rev 6"
        r'^RM\d+\s+Rev\s+\d+\s+\d+/\d+\s*$',  # "RM0041 Rev 6 612/709"
        r'^RM\d+\s+[A-Za-z].*$',               # "RM0041 Universal synchronous..."
    ]

    # Page header patterns that extract page numbers
    PAGE_NUMBER_PATTERNS = [
        re.compile(r'^(\d+)/\d+\s+RM\d+\s+Rev\s+\d+\s*$', re.MULTILINE),  # "612/709 RM0041 Rev 6"
        re.compile(r'^RM\d+\s+Rev\s+\d+\s+(\d+)/\d+\s*$', re.MULTILINE),  # "RM0041 Rev 6 612/709"
    ]

    def __init__(self):
        self._header_regexes = [re.compile(p, re.MULTILINE) for p in self.HEADER_PATTERNS]

    # -------------------------------------------------------------------------
    # Page number tracking (Step 1)
    # -------------------------------------------------------------------------

    def extract_page_regions(self, text: str) -> List[Tuple[int, int, int]]:
        """Extract page-bounded regions from raw text using RM-style page headers.

        Scans for page headers like "612/709 RM0041 Rev 6" and returns a list
        of (page_number, start_line, end_line) tuples marking each page region.

        Args:
            text: Raw text content with RM-style page headers

        Returns:
            List of (page_number, start_line_index, end_line_index) tuples.
            If no page headers found, returns empty list.
        """
        lines = text.split('\n')
        page_breaks = []  # (line_index, page_number)

        for i, line in enumerate(lines):
            for pattern in self.PAGE_NUMBER_PATTERNS:
                match = pattern.match(line.strip())
                if match:
                    page_num = int(match.group(1))
                    page_breaks.append((i, page_num))
                    break

        if not page_breaks:
            return []

        regions = []
        for idx, (line_idx, page_num) in enumerate(page_breaks):
            start = line_idx
            end = page_breaks[idx + 1][0] if idx + 1 < len(page_breaks) else len(lines)
            regions.append((page_num, start, end))

        return regions

    def build_line_to_page_map(self, text: str) -> Dict[int, int]:
        """Build a mapping from line index to page number.

        Args:
            text: Raw text content with RM-style page headers

        Returns:
            Dict mapping line_index -> page_number.
            Empty dict if no page headers found.
        """
        regions = self.extract_page_regions(text)
        if not regions:
            return {}

        line_to_page = {}
        for page_num, start, end in regions:
            for line_idx in range(start, end):
                line_to_page[line_idx] = page_num

        return line_to_page

    def find_page_for_text(self, snippet: str, raw_text: str, line_to_page: Dict[int, int]) -> int:
        """Find the page number for a text snippet by locating it in the raw text.

        Args:
            snippet: The first ~80 chars of a chunk to search for
            raw_text: The original raw text (before cleaning)
            line_to_page: Mapping from line index to page number

        Returns:
            Page number, or 0 if not found
        """
        if not line_to_page or not snippet:
            return 0

        # Search for the snippet's first line in the raw text
        first_line = snippet.split('\n')[0].strip()
        if not first_line or len(first_line) < 10:
            # Try second line if first is too short
            lines = snippet.split('\n')
            first_line = lines[1].strip() if len(lines) > 1 else first_line

        if not first_line:
            return 0

        raw_lines = raw_text.split('\n')
        for i, line in enumerate(raw_lines):
            if first_line in line:
                return line_to_page.get(i, 0)

        return 0

    # -------------------------------------------------------------------------
    # Register name expansion (Step 2)
    # -------------------------------------------------------------------------

    @staticmethod
    def _parse_range_string(range_str: str) -> List[str]:
        """Parse a range string and return all values.

        Supports formats:
        - Numeric range: '1..4', '1 .. 4', '1..20'
        - Alphabetic range: 'A..G', 'A .. G'
        - Comma list: '1,2,3'
        - Word range: '0 to 3', 'A to G'
        """
        range_str = range_str.strip()

        # Numeric range with '..'
        match = re.match(r'(\d+)\s*\.\.\s*(\d+)', range_str)
        if match:
            return [str(i) for i in range(int(match.group(1)), int(match.group(2)) + 1)]

        # Alphabetic range with '..'
        match = re.match(r'([A-Z])\s*\.\.\s*([A-Z])', range_str)
        if match:
            return [chr(i) for i in range(ord(match.group(1)), ord(match.group(2)) + 1)]

        # Comma-separated list
        if ',' in range_str:
            return [v.strip() for v in range_str.split(',') if v.strip()]

        # Word range with 'to'
        match = re.match(r'(\d+)\s+to\s+(\d+)', range_str, re.IGNORECASE)
        if match:
            return [str(i) for i in range(int(match.group(1)), int(match.group(2)) + 1)]

        match = re.match(r'([A-Z])\s+to\s+([A-Z])', range_str, re.IGNORECASE)
        if match:
            return [chr(i) for i in range(ord(match.group(1).upper()), ord(match.group(2).upper()) + 1)]

        return []

    @staticmethod
    def _expand_parameterized_register(template: str, range_str: str) -> List[str]:
        """Expand a parameterized register template with a range.

        Examples:
            'GPIOx_CRL' with 'A..G' -> ['GPIOA_CRL', ..., 'GPIOG_CRL']
            'ADC_JOFRx' with '1..4' -> ['ADC_JOFR1', ..., 'ADC_JOFR4']
        """
        values = TextProcessor._parse_range_string(range_str)
        if not values:
            return []
        return [template.replace('x', val).replace('X', val) for val in values]

    def extract_registers_expanded(self, text: str) -> List[str]:
        """Extract register names from text with parameterized expansion.

        Handles:
        1. Parenthesized registers: (BKP_DRx) (x = 1..20)
        2. Standard parameterized: ADC_JOFRx (x=1..4), GPIOx_CRL (x=A..G)
        3. Contextual expansion: TIM1 control register (TIMx_CR1)
        4. Concrete patterns: AFIO_EXTICR1

        Returns:
            Sorted list of expanded register names
        """
        registers = set()
        templates_seen = set()

        # Pattern 1: Parenthesized register with range - (BKP_DRx) (x = 1..20)
        for match in re.finditer(r'\(([A-Z][A-Z0-9_]*[xX][A-Z0-9_]*)\)\s*\(\s*[xX]\s*=\s*([^)]+)\)', text):
            template, range_str = match.group(1), match.group(2)
            expanded = self._expand_parameterized_register(template, range_str)
            if expanded:
                registers.update(expanded)
                templates_seen.add(template.lower())

        # Pattern 2: Standard parameterized - ADC_JOFRx (x=1..4)
        for match in re.finditer(r'([A-Z][A-Z0-9_]*[xX][A-Z0-9_]*)\s*\(\s*[xX]\s*=\s*([^)]+)\)', text):
            template, range_str = match.group(1), match.group(2)
            if template.lower() in templates_seen:
                continue
            expanded = self._expand_parameterized_register(template, range_str)
            if expanded:
                registers.update(expanded)
                templates_seen.add(template.lower())

        # Pattern 3: Contextual expansion - "TIM1 control register 1 (TIMx_CR1)"
        for match in re.finditer(r'([A-Z]+\d+|[A-Z]+[A-Z])\s+[^()]*?\(([A-Z]+)[xX](_[A-Z0-9_]+)\)', text):
            context = match.group(1)
            template_prefix = match.group(2)
            template_suffix = match.group(3)
            context_base = context.rstrip('0123456789').rstrip('ABCDEFG')
            if context_base == template_prefix:
                suffix_match = re.match(r'([A-Z]+)(\d+|[A-Z])$', context)
                if suffix_match:
                    val = suffix_match.group(2)
                    template = f"{template_prefix}x{template_suffix}"
                    expanded = template.replace('x', val).replace('X', val)
                    registers.add(expanded)

        # Pattern 4: Concrete register names (no x placeholder)
        for match in re.finditer(r'\b([A-Z][A-Z0-9]*_[A-Z][A-Z0-9_]*)\b', text):
            reg_name = match.group(1)
            if 'x' in reg_name or 'X' in reg_name:
                # Keep templates too
                registers.add(reg_name)
            else:
                registers.add(reg_name)

        return sorted(registers)

    # -------------------------------------------------------------------------
    # Original TextProcessor methods (from vector_db)
    # -------------------------------------------------------------------------

    def clean_text(self, text: str) -> str:
        """Clean text by removing headers/footers and normalizing whitespace."""
        for regex in self._header_regexes:
            text = regex.sub('', text)

        # Normalize multiple blank lines to double newline
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove trailing whitespace from lines
        text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)

        text = text.strip()
        return text

    def clean_text_with_page_map(self, text: str, raw_line_to_page: Dict[int, int]) -> Tuple[str, Dict[int, int]]:
        """Clean text and build a mapping from cleaned-text line indices to page numbers.

        Works by processing raw lines one at a time:
        1. For each raw line, check if it would be removed by header patterns
        2. Track which raw lines survive cleaning and map them to cleaned line indices
        3. Propagate page numbers from raw lines to cleaned lines

        Args:
            text: Raw text to clean
            raw_line_to_page: Mapping from raw line index to page number

        Returns:
            Tuple of (cleaned_text, cleaned_line_to_page)
        """
        raw_lines = text.split('\n')
        surviving_lines = []  # (raw_line_idx, cleaned_line_text)

        for raw_idx, line in enumerate(raw_lines):
            stripped = line.rstrip()
            # Check if this line matches any header pattern
            is_header = False
            for regex in self._header_regexes:
                if regex.match(stripped):
                    is_header = True
                    break
            if not is_header:
                surviving_lines.append((raw_idx, stripped))

        # Rebuild text from surviving lines and normalize blank lines
        cleaned_lines = []
        cleaned_line_to_page = {}
        blank_count = 0

        for raw_idx, line in surviving_lines:
            if not line:
                blank_count += 1
                if blank_count <= 2:
                    page = raw_line_to_page.get(raw_idx, 0)
                    cleaned_line_to_page[len(cleaned_lines)] = page
                    cleaned_lines.append(line)
            else:
                blank_count = 0
                page = raw_line_to_page.get(raw_idx, 0)
                cleaned_line_to_page[len(cleaned_lines)] = page
                cleaned_lines.append(line)

        # Strip leading/trailing empty lines
        while cleaned_lines and not cleaned_lines[0]:
            cleaned_lines.pop(0)
            # Rebuild the mapping with shifted indices
            cleaned_line_to_page = {k-1: v for k, v in cleaned_line_to_page.items() if k > 0}

        while cleaned_lines and not cleaned_lines[-1]:
            last_idx = len(cleaned_lines) - 1
            cleaned_lines.pop()
            cleaned_line_to_page.pop(last_idx, None)

        cleaned_text = '\n'.join(cleaned_lines)
        return cleaned_text, cleaned_line_to_page

    def split_by_sections(self, text: str, cleaned_line_to_page: Optional[Dict[int, int]] = None) -> List[Dict[str, Any]]:
        """Split markdown by headers, preserving section context.

        Args:
            text: Cleaned text to split
            cleaned_line_to_page: Optional mapping from cleaned line indices to page numbers.
        """
        section_pattern = r'^(#{1,4})\s+(.+)$'
        lines = text.split('\n')

        sections = []
        current_section = {
            'header': '',
            'level': 0,
            'content': [],
            'content_line_indices': [],  # Track line indices for per-line page lookup
            'start_line': 0,
        }

        for line_idx, line in enumerate(lines):
            match = re.match(section_pattern, line)
            if match:
                if current_section['content']:
                    sections.append(current_section)
                level = len(match.group(1))
                header = match.group(2).strip()
                current_section = {
                    'header': header,
                    'level': level,
                    'content': [],
                    'content_line_indices': [],
                    'start_line': line_idx,
                }
            else:
                current_section['content'].append(line)
                current_section['content_line_indices'].append(line_idx)

        if current_section['content']:
            sections.append(current_section)

        # Assign page numbers to sections from the cleaned line mapping
        if cleaned_line_to_page:
            for section in sections:
                page = cleaned_line_to_page.get(section['start_line'], 0)
                if page == 0:
                    for offset in range(1, 20):
                        page = cleaned_line_to_page.get(section['start_line'] + offset, 0)
                        if page > 0:
                            break
                section['page_number'] = page
        else:
            for section in sections:
                section['page_number'] = 0

        return sections

    def has_markdown_table(self, text: str) -> bool:
        """Check if text contains a markdown table."""
        table_sep_pattern = r'^\|[\s\-:]+\|[\s\-:|]+$'
        return bool(re.search(table_sep_pattern, text, re.MULTILINE))

    def extract_key_terms(self, text: str, header: str) -> str:
        """Extract key terms from chunk to improve reranking."""
        terms = []
        register_title = ""

        has_table = self.has_markdown_table(text)
        if has_table:
            terms.append("TABLE:register_bitfields")

        register_pattern = r'\b([A-Z]{2,}[x]?_[A-Z0-9_]+)\b'
        registers = re.findall(register_pattern, text)
        if registers:
            unique_regs = list(dict.fromkeys(registers))[:5]

            if has_table and 'Address offset:' in text:
                register_title = f"REGISTER DEFINITION: {unique_regs[0]} - Complete bit field specification\n"
                terms.extend(unique_regs)
            elif len(unique_regs) >= 4:
                terms.append("OVERVIEW:register_list")
            else:
                terms.extend(unique_regs)

        offset_match = re.search(r'Address offset:\s*(0x[0-9A-Fa-f]+)', text)
        if offset_match:
            terms.append(f"offset:{offset_match.group(1)}")

        reset_match = re.search(r'Reset value:\s*(0x[0-9A-Fa-f]+)', text)
        if reset_match:
            terms.append(f"reset:{reset_match.group(1)}")

        field_pattern = r'Bits?\s+\d+(?::\d+)?\s+([A-Z][A-Z0-9_\[\]]+):'
        fields = re.findall(field_pattern, text)
        if fields:
            unique_fields = list(dict.fromkeys(fields))[:8]
            terms.append(f"fields:{','.join(unique_fields)}")

        if terms:
            return f"{register_title}[KEY: {' | '.join(terms)}]\n\n"
        return ""

    def chunk_section(self, section: Dict[str, Any]) -> List[str]:
        """Chunk a section's content while preserving the header context."""
        header = section['header']
        content = '\n'.join(section['content']).strip()

        if not content:
            return []

        # Skip TOC entries
        content_without_numbers = re.sub(r'^\d+\s*$', '', content, flags=re.MULTILINE).strip()
        content_without_toc = re.sub(r'\.[\s.]+\d+\s*$', '', content, flags=re.MULTILINE).strip()
        if len(content_without_numbers) < 50 or len(content_without_toc) < 50:
            return []

        full_text = f"# {header}\n\n{content}" if header else content
        key_terms = self.extract_key_terms(full_text, header)
        full_text_with_keys = key_terms + full_text

        if count_tokens(full_text_with_keys) <= config.CHUNK_SIZE:
            return [full_text_with_keys] if full_text_with_keys.strip() else []

        chunks = split_text_recursive(content)

        result = []
        for chunk in chunks:
            if header:
                chunk_with_header = f"# {header}\n\n{chunk}"
            else:
                chunk_with_header = chunk

            chunk_key_terms = self.extract_key_terms(chunk_with_header, header)
            final_chunk = chunk_key_terms + chunk_with_header

            if final_chunk.strip():
                result.append(final_chunk)

        return result

    # -------------------------------------------------------------------------
    # Main processing with enriched metadata
    # -------------------------------------------------------------------------

    def process_file(
        self, file_path: Path, extra_metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Process a text/markdown file and return chunks with enriched metadata.

        Metadata includes:
        - source: filename
        - section: section header
        - chunk_index: global chunk index
        - page_number: page from RM-style headers (0 if not found)
        - has_tables: whether chunk contains markdown tables
        - registers_mentioned: list of expanded register names (ChromaDB list metadata for $contains)
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read raw text
        raw_text = file_path.read_text(encoding='utf-8')

        # Build line-to-page mapping BEFORE cleaning (page headers get removed)
        raw_line_to_page = self.build_line_to_page_map(raw_text)

        # Clean text and build cleaned-line-to-page mapping
        if raw_line_to_page:
            text, cleaned_line_to_page = self.clean_text_with_page_map(raw_text, raw_line_to_page)
        else:
            text = self.clean_text(raw_text)
            cleaned_line_to_page = {}

        # Split by sections and chunk each section (with page numbers)
        sections = self.split_by_sections(text, cleaned_line_to_page or None)

        all_chunks = []
        chunk_index = 0

        for section in sections:
            section_chunks = self.chunk_section(section)
            section_chunks = add_overlap(section_chunks)

            # Build per-content-line page lookup for this section
            content_lines = section['content']
            content_line_indices = section.get('content_line_indices', [])
            content_line_pages = []
            if cleaned_line_to_page and content_line_indices:
                for cli in content_line_indices:
                    page = cleaned_line_to_page.get(cli, 0)
                    content_line_pages.append(page)

            # For each chunk, find which content line it starts on to get its page
            section_content = '\n'.join(content_lines)

            for chunk_text in section_chunks:
                # Determine page number for this specific chunk
                page_number = section.get('page_number', 0)
                if content_line_pages:
                    # Find the chunk's content in the section to get its starting line
                    # Strip KEY terms and header that were prepended by chunk_section
                    chunk_content = chunk_text
                    # Remove [KEY: ...] prefix
                    key_end = chunk_content.find(']\n\n')
                    if key_end >= 0 and chunk_content.startswith(('[KEY:', 'REGISTER DEFINITION:')):
                        chunk_content = chunk_content[key_end + 3:]
                    # Remove header
                    if chunk_content.startswith('# '):
                        nl = chunk_content.find('\n\n')
                        if nl >= 0:
                            chunk_content = chunk_content[nl + 2:]
                    # Remove overlap prefix
                    if chunk_content.startswith('[...] '):
                        nl = chunk_content.find('\n\n')
                        if nl >= 0:
                            chunk_content = chunk_content[nl + 2:]
                    # Find first significant line
                    first_line = ''
                    for cl in chunk_content.split('\n'):
                        cl = cl.strip()
                        if cl and len(cl) > 5:
                            first_line = cl
                            break
                    if first_line:
                        for ci_idx, content_line in enumerate(content_lines):
                            if first_line in content_line:
                                if ci_idx < len(content_line_pages) and content_line_pages[ci_idx] > 0:
                                    page_number = content_line_pages[ci_idx]
                                break

                # Detect tables
                has_tables = self.has_markdown_table(chunk_text)

                # Extract and expand register names
                expanded_registers = self.extract_registers_expanded(chunk_text)

                metadata = {
                    "source": file_path.name,
                    "section": section['header'][:100] if section['header'] else "",
                    "chunk_index": chunk_index,
                    "page_number": page_number,
                    "has_tables": has_tables,
                    "registers_mentioned": expanded_registers if expanded_registers else [],
                }
                if extra_metadata:
                    metadata.update(extra_metadata)

                all_chunks.append({"text": chunk_text, "metadata": metadata})
                chunk_index += 1

        return all_chunks
