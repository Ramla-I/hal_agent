def find_paragraphs_with_keyword(xml_path: str, keyword: str) -> list[str]:
    """
    Given a path to an XML file and a keyword, finds all paragraphs (<p> elements) containing the keyword.

    Args:
        xml_path (str): Path to the XML file (e.g., rm0041_ddm.xml)
        keyword (str): Keyword to search for (case-insensitive)

    Returns:
        list[str]: List of paragraph texts containing the keyword
    """
    import xml.etree.ElementTree as ET

    paragraphs_with_keyword = []
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        # Find all <paragraph> elements in the document
        for p in root.iter('paragraph'):
            text = ''.join(p.itertext()).strip()
            if keyword.lower() in text.lower():
                paragraphs_with_keyword.append(text)
    except Exception as e:
        # Optionally, handle or log the error
        pass
    return paragraphs_with_keyword


def main():
    import sys
    if len(sys.argv) != 3:
        print("Usage: python find_sections_in_ddm.py <xml_path> <keyword>")
        sys.exit(1)
    xml_path = sys.argv[1]
    keyword = sys.argv[2]
    results = find_paragraphs_with_keyword(xml_path, keyword)
    print(f"Found {len(results)} paragraphs containing '{keyword}':")
    for i, para in enumerate(results, 1):
        print(f"\n--- Paragraph {i} ---\n{para}")

if __name__ == "__main__":
    main()
