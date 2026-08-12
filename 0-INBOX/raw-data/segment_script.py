import re
import os

input_path = "/home/whitetiger/dharmaduta/སེམས་ཉིད་ངལ་གསོ/དོན་ཁྲིད་བྱང་ཆུབ་ལམ་བཟང་.txt"
output_path = "/home/whitetiger/dharmaduta/སེམས་ཉིད་ངལ་གསོ/དོན་ཁྲིད་བྱང་ཆུབ་ལམ་བཟང་_khrid_rkang.txt"

def segment_by_khrid_rkang(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove existing newlines and carriage returns
    content = content.replace('\n', '').replace('\r', '')
    
    # Collapse multiple spaces (but keep single spaces as they might be between shads)
    content = re.sub(r'[ \t]+', ' ', content)

    # Pattern to match the end of a khrid rkang section.
    # It starts with ཁྲིད་རྐང་, followed by any characters that are NOT a shad,
    # then one or more shads (possibly with spaces between them).
    # We want to match the whole marker including the trailing shads.
    pattern = r"(ཁྲིད་རྐང་[^།]+?།[\s།]*)"
    
    # Replace the pattern with itself plus a newline
    segmented_content = re.sub(pattern, r"\1\n", content)
    
    # Clean up: remove trailing whitespace on each line
    lines = [line.strip() for line in segmented_content.split('\n')]
    final_content = '\n'.join(filter(None, lines))
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_content)

    return len(final_content.split('\n'))

num_paragraphs = segment_by_khrid_rkang(input_path)
print(f"Segmented into {num_paragraphs} paragraphs based on ཁྲིད་རྐང་.")
