#!/usr/bin/env python3
"""
Converter: Siddhartha's Intent (Sigil-produced English ebooks)
Generated: 2026-08-12

Source epub: Poison is Medicine — Clarifying the Vajrayana, Dzongsar Jamyang
Khyentse, Siddhartha's Intent. `publisher_slug` = siddharthas-intent.

A clean Sigil export: chapter titles are real `<h3>` tags preceded by a spelled
-out number in `p.chapterTitleHead` ("ONE"), section heads are
`p.chapterSubTitle`, and the body is unclassed `<p>` plus a handful of semantic
classes.

Class / tag -> Markdown
-----------------------
  h1.booktitlefont, h2.sub-booktitlefont -> # / ## (title page)
  p.chapterTitleHead + h3               -> "# ONE. Me and My Gurus" (merged)
  p.chapterSubTitle                     -> ## heading
  p.quote-inline                        -> > blockquote
  p.signature                           -> > — attribution, attached to the
                                           preceding quote
  p.Tibetan                             -> plain (Unicode Tibetan lines)
  p.chapter1stparagraph, p (unclassed)  -> plain text
  li                                    -> "- " list item

Skipped: cover and `nav.xhtml` (the ebook's own contents list). Endnotes are
kept. Images are not extracted.

Inline: <i>/<em> → *italic*, <b>/<strong> → **bold**.
"""

import argparse
import re
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup, NavigableString, Tag
import yaml


SKIP_DOCS = ('cover.xhtml', 'nav.xhtml', 'toc.xhtml')

HEADING_CLASSES = {
    'booktitlefont': 1,
    'sub-booktitlefont': 2,
    'chapterSubTitle': 2,
}

CHAPTER_NUMBER_CLASS = 'chapterTitleHead'
QUOTE_CLASSES = {'quote-inline'}
SIGNATURE_CLASSES = {'signature'}


def inline_text(el):
    out = []
    for child in el.children:
        if isinstance(child, NavigableString):
            out.append(str(child))
        elif isinstance(child, Tag):
            if child.name in ('em', 'i'):
                inner = inline_text(child).strip()
                out.append('*' + inner + '*' if inner else '')
            elif child.name in ('strong', 'b'):
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


NUMBER_CELL = re.compile(r'^[\d]+[.)]?$')


def render_row(tr):
    """Render one table row; used for the bare <tr> rows described in BUG-008."""
    cells = [clean(inline_text(td)).replace('\n', ' ')
             for td in tr.find_all(['td', 'th'])]
    cells = [c for c in cells if c]
    if not cells:
        return ''
    if len(cells) == 2 and NUMBER_CELL.match(cells[0]):
        return cells[0].rstrip('.)') + '. ' + cells[1] + '\n'
    return ' '.join(cells) + '\n'


def render_table(table):
    """
    Sigil renders the book's numbered question lists as two-column tables
    (number | text). Emit those as an ordered list; anything else as a
    Markdown table.
    """
    rows = []
    for tr in table.find_all('tr'):
        cells = [clean(inline_text(td)).replace('\n', ' ')
                 for td in tr.find_all(['td', 'th'])]
        if any(cells):
            rows.append(cells)
    if not rows:
        return ''

    if all(len(r) == 2 and NUMBER_CELL.match(r[0]) for r in rows):
        return '\n'.join(r[0].rstrip('.)') + '. ' + r[1] for r in rows) + '\n'

    width = max(len(r) for r in rows)
    rows = [r + [''] * (width - len(r)) for r in rows]
    out = ['| ' + ' | '.join(rows[0]) + ' |', '|' + '---|' * width]
    out += ['| ' + ' | '.join(r) + ' |' for r in rows[1:]]
    return '\n'.join(out) + '\n'


def dc(book, key):
    raw = book.get_metadata('DC', key)
    return raw[0][0] if raw else None


def extract_metadata(book, epub_path):
    d = {
        'title': dc(book, 'title'),
        'author': dc(book, 'creator'),
        'publisher': dc(book, 'publisher'),
        'date': dc(book, 'date'),
        'language': dc(book, 'language'),
        'source_id': dc(book, 'identifier'),
        'source_file': epub_path.split('/')[-1],
        'source_description': 'Extracted from EPUB source',
    }
    return {k: v for k, v in d.items() if v}


def convert_epub_to_markdown(epub_path, output_path, frontmatter=None):
    book = epub.read_epub(epub_path)

    md = ''
    pending_number = None
    prev_kind = None

    for item_id, _linear in book.spine:
        item = book.get_item_with_id(item_id)
        if not item or item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        if item.get_name().split('/')[-1] in SKIP_DOCS:
            continue

        soup = BeautifulSoup(item.get_content(), 'html.parser')
        for t in soup(['script', 'style']):
            t.decompose()
        body = soup.find('body')
        if not body:
            continue

        for el in body.find_all(['table', 'tr', 'h1', 'h2', 'h3', 'h4', 'p',
                                 'blockquote', 'li', 'b', 'strong']):
            # Orphan <b> subheadings sitting directly in a <div> (BUG-008)
            if el.name in ('b', 'strong'):
                if any(p.name in ('p', 'h1', 'h2', 'h3', 'h4', 'li',
                                  'blockquote', 'tr') for p in el.parents):
                    continue
                text = clean(inline_text(el))
                if text:
                    md += '### ' + text + '\n\n'
                    prev_kind = 'heading'
                continue

            if el.name == 'tr':
                if el.find_parent('table'):
                    continue
                rendered = render_row(el)
                if rendered:
                    if prev_kind != 'row':
                        md = md.rstrip('\n') + '\n\n'
                    md += rendered
                    prev_kind = 'row'
                continue
            if el.find_parent('tr'):
                continue
            if prev_kind == 'row':
                md += '\n'
                prev_kind = None
            if el.name == 'table':
                rendered = render_table(el)
                if rendered:
                    md += rendered + '\n'
                    prev_kind = 'table'
                continue
            if el.find_parent('table'):
                continue
            if el.find_parent('li') or el.find_parent('blockquote'):
                continue

            cls = set(el.get('class', []))
            text = clean(inline_text(el))
            if not text:
                continue

            if el.name == 'li':
                md += '- ' + text + '\n'
                prev_kind = 'list'
                continue
            if prev_kind == 'list':
                md += '\n'

            # "ONE" waits for the <h3> chapter title that follows it
            if CHAPTER_NUMBER_CLASS in cls:
                pending_number = text
                continue

            if el.name in ('h1', 'h2', 'h3', 'h4'):
                level = 1 if el.name in ('h1', 'h3') else 2
                for c in cls:
                    if c in HEADING_CLASSES:
                        level = HEADING_CLASSES[c]
                if pending_number:
                    text = pending_number + '. ' + text
                    pending_number = None
                md += '#' * level + ' ' + text + '\n\n'
                prev_kind = 'heading'
                continue

            if cls & HEADING_CLASSES.keys():
                level = min(HEADING_CLASSES[c] for c in cls
                            if c in HEADING_CLASSES)
                md += '#' * level + ' ' + text + '\n\n'
                prev_kind = 'heading'
                continue

            if cls & SIGNATURE_CLASSES and prev_kind == 'quote':
                md = md.rstrip('\n') + '\n> — ' + text + '\n\n'
                prev_kind = 'quote'
                continue

            if (cls & QUOTE_CLASSES) or el.name == 'blockquote':
                quoted = '\n'.join('> ' + line for line in text.split('\n'))
                if prev_kind == 'quote':
                    md = md.rstrip('\n') + '\n' + quoted + '\n\n'
                else:
                    md += quoted + '\n\n'
                prev_kind = 'quote'
                continue

            md += text + '\n\n'
            prev_kind = 'plain'

        if pending_number:
            md += '# ' + pending_number + '\n\n'
            pending_number = None

    meta = frontmatter if frontmatter is not None else extract_metadata(book, epub_path)
    fm = '---\n' + yaml.dump(meta, allow_unicode=True, sort_keys=False) + '---\n\n'

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(fm + md)

    print('Successfully extracted to ' + output_path)
    print('Headings: %d' % len(re.findall(r'(?m)^#{1,6} ', md)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="EPUB to Markdown — Siddhartha's Intent")
    parser.add_argument('epub_path')
    parser.add_argument('output_path')
    args = parser.parse_args()
    convert_epub_to_markdown(args.epub_path, args.output_path)
