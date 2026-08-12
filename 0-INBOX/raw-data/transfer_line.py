from fast_antx.core import transfer
from pathlib import Path


if __name__ == "__main__":
    tsawa = Path('./root.txt').read_text(encoding='utf-8')
    tsawa = tsawa.replace('\n', '')
    segmented_tsawa = Path('./segmented_tsawa.txt').read_text(encoding='utf-8')
    patterns = [['linebreak', r'(\n)']]
    transferred_tsawa = transfer(segmented_tsawa, patterns, tsawa)
    Path('./transferred_tsawa.txt').write_text(transferred_tsawa, encoding='utf-8')