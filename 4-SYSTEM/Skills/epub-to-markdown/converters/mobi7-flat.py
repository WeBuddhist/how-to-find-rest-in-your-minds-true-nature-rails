#!/usr/bin/env python3
"""
Converter: MOBI7 (.mobi) flattened HTML — publisher-agnostic
Generated: 2026-08-12

First used for: Not for Happiness — A Guide to the So-Called Preliminary
Practises, Dzongsar Jamyang Khyentse (Shambhala 2012), supplied as .mobi.

Why a separate converter
------------------------
A .mobi is not an epub: ebooklib cannot open it, and an old MOBI6/MOBI7 file
has no KF8 part to fall back on. Unpacking yields a single `book.html` with
**no CSS classes at all** — structure survives only as `<font size>` and `<b>`
formatting, plus `toc.ncx`, whose navPoints carry `filepos` byte offsets that
match `<a id="filepos…">` anchors in the HTML.

So the structure comes from the NCX, not the markup:

  1. `extract(mobi_path)` unpacks with the `mobi` package (pip install mobi).
  2. `toc.ncx` gives (label, anchor, depth) in reading order.
  3. The HTML is sliced at each anchor; each slice becomes a section under a
     heading built from the navPoint label (depth 0 → #, depth 1 → ##).
  4. Inside a slice, `<font size>` drives sub-headings: size ≥ 6 is the
     chapter title the NCX already gave us (suppressed when it repeats the
     label), size 5 → ###, size 4 → ####.

Encoding
--------
MOBI7 files are usually windows-1252, and the declared charset in the HTML
`<meta>` says so. Decoding as UTF-8 with errors='ignore' silently deletes
every curly quote and accented character — "Jamgön Kongtrül Lodrö Tayé"
becomes "Jamgn Kongtrul Lodr Tay". `read_html()` honours the declared charset
and falls back to cp1252. See BUG-009.

Skipped: the ebook's own "Contents" / "Table of Contents" section (the NCX
already provides the outline) and the cover. Images are not extracted.
"""

import argparse
import os
import re
import yaml
from bs4 import BeautifulSoup, NavigableString, Tag


SKIP_LABELS = {'contents', 'table of contents', 'cover', 'toc'}


# ---------------------------------------------------------------------------
# Unpacking and decoding
# ---------------------------------------------------------------------------

def extract(mobi_path):
    """Unpack a .mobi and return (html_path, opf_path, ncx_path)."""
    import mobi
    tmpdir, _main = mobi.extract(mobi_path)
    root = os.path.join(tmpdir, 'mobi7')
    if not os.path.isdir(root):
        root = tmpdir
    return (os.path.join(root, 'book.html'),
            os.path.join(root, 'content.opf'),
            os.path.join(root, 'toc.ncx'))


def read_html(path):
    """Decode the unpacked HTML using its declared charset (usually cp1252)."""
    raw = open(path, 'rb').read()
    match = re.search(br'charset=([\w\-]+)', raw[:2000], re.I)
    declared = match.group(1).decode('ascii', 'ignore').lower() if match else ''
    for enc in [declared, 'utf-8', 'cp1252', 'latin-1']:
        if not enc:
            continue
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode('latin-1')


def read_toc(ncx_path):
    """Return [(label, anchor, depth), …] in reading order."""
    soup = BeautifulSoup(open(ncx_path, encoding='utf-8').read(), 'xml')
    entries = []

    def walk(np, depth):
        label = np.find('navLabel').get_text().strip()
        src = np.find('content')['src']
        anchor = src.split('#')[-1] if '#' in src else None
        entries.append((label, anchor, depth))
        for child in np.find_all('navPoint', recursive=False):
            walk(child, depth + 1)

    nav_map = soup.find('navMap')
    if nav_map:
        for np in nav_map.find_all('navPoint', recursive=False):
            walk(np, 0)
    return entries


def read_opf_metadata(opf_path, mobi_path):
    soup = BeautifulSoup(open(opf_path, encoding='utf-8').read(), 'xml')

    def get(tag):
        el = soup.find(tag)
        return el.get_text().strip() if el else None

    d = {
        'title': get('title'),
        'author': get('creator'),
        'publisher': get('publisher'),
        'date': (get('date') or '')[:10] or None,
        'language': get('language'),
        'rights': get('rights'),
        'source_file': mobi_path.split('/')[-1],
        'source_description': 'Extracted from MOBI source',
    }
    return {k: v for k, v in d.items() if v}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def inline_text(el):
    out = []
    for child in el.children:
        if isinstance(child, NavigableString):
            out.append(str(child))
        elif isinstance(child, Tag):
            if child.name in ('i', 'em'):
                inner = inline_text(child).strip()
                out.append('*' + inner + '*' if inner else '')
            elif child.name in ('b', 'strong'):
                inner = inline_text(child).strip()
                out.append('**' + inner + '**' if inner else '')
            elif child.name == 'br':
                out.append('\n')
            elif child.name == 'img':
                continue
            else:
                out.append(inline_text(child))
    return ''.join(out)


def clean(text):
    lines = [' '.join(line.split()) for line in text.split('\n')]
    return '\n'.join(lines).strip()


def font_size(el):
    """Largest <font size> applied to this element's content, if any."""
    sizes = []
    for font in el.find_all('font'):
        size = font.get('size')
        if size and size.lstrip('+-').isdigit():
            sizes.append(int(size))
    return max(sizes) if sizes else None


def is_all_bold(el):
    text = clean(el.get_text())
    bold = ''.join(clean(b.get_text()) for b in el.find_all(['b', 'strong']))
    return bool(text) and bold.replace(' ', '') == text.replace(' ', '')


def render_section(html, label, depth, seen_labels):
    """Render one NCX section (already sliced out of the flat HTML)."""
    soup = BeautifulSoup(html, 'html.parser')
    md = '#' * (depth + 1) + ' ' + label + '\n\n'
    prev = None

    for el in soup.find_all(['p', 'blockquote', 'li']):
        if el.find_parent(['blockquote', 'li']):
            continue
        # MOBI7 nests <blockquote>/<ul> inside <p>; render the inner block
        # only, or its text is emitted twice (BUG-010).
        if el.name == 'p' and el.find(['blockquote', 'li', 'ul', 'ol']):
            continue

        text = clean(inline_text(el))
        if not text:
            continue

        if el.name == 'li':
            md += '- ' + text + '\n'
            prev = 'list'
            continue
        if prev == 'list':
            md += '\n'

        if el.name == 'blockquote':
            md += '\n'.join('> ' + line for line in text.split('\n')) + '\n\n'
            prev = 'quote'
            continue

        size = font_size(el)
        if size and size >= 6 and is_all_bold(el):
            # The NCX label already carries this chapter title
            plain = re.sub(r'[*]', '', text)
            if plain.lower() in label.lower() or label.lower() in plain.lower():
                continue
            md += '#' * (depth + 2) + ' ' + plain + '\n\n'
            prev = 'heading'
            continue
        if size == 5 and is_all_bold(el):
            md += '#' * (depth + 2) + ' ' + re.sub(r'[*]', '', text) + '\n\n'
            prev = 'heading'
            continue
        if size == 4 and is_all_bold(el):
            md += '#' * (depth + 3) + ' ' + re.sub(r'[*]', '', text) + '\n\n'
            prev = 'heading'
            continue

        md += text + '\n\n'
        prev = 'plain'

    seen_labels.append(label)
    return md


def convert_mobi_to_markdown(mobi_path, output_path, frontmatter=None):
    html_path, opf_path, ncx_path = extract(mobi_path)
    html = read_html(html_path)
    toc = read_toc(ncx_path)

    # Locate each anchor in the raw HTML so sections can be sliced apart
    positions = []
    for label, anchor, depth in toc:
        if not anchor:
            continue
        idx = html.find('id="%s"' % anchor)
        if idx == -1:
            idx = html.find("id='%s'" % anchor)
        if idx == -1:
            print('  [warn] anchor not found in HTML: %s (%s)' % (anchor, label))
            continue
        positions.append((idx, label, depth))
    positions.sort()

    body_md = ''
    seen = []
    for n, (start, label, depth) in enumerate(positions):
        end = positions[n + 1][0] if n + 1 < len(positions) else len(html)
        if label.strip().lower() in SKIP_LABELS:
            continue
        body_md += render_section(html[start:end], label, depth, seen)

    meta = (frontmatter if frontmatter is not None
            else read_opf_metadata(opf_path, mobi_path))
    fm = '---\n' + yaml.dump(meta, allow_unicode=True, sort_keys=False) + '---\n\n'

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(fm + body_md)

    print('Successfully extracted to ' + output_path)
    print('Sections: %d of %d NCX entries' % (len(seen), len(toc)))
    print('Headings: %d' % len(re.findall(r'(?m)^#{1,6} ', body_md)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='MOBI to Markdown — flattened MOBI7 HTML + NCX')
    parser.add_argument('mobi_path')
    parser.add_argument('output_path')
    args = parser.parse_args()
    convert_mobi_to_markdown(args.mobi_path, args.output_path)
