#!/usr/bin/env python3
"""
Converter: Shambhala Publications trade ebooks (English)
Generated: 2026-08-12

Publisher: "Shambhala" (present in the OPF, so `publisher_slug` = shambhala).
Unlike the Tibetan InDesign exports in this folder, these are commercial
English ebooks: no colour-coded semantic classes, no sa bcad labels, no root
markers. Structure comes from heading tags and paragraph classes instead.

Two production templates ship under this one slug; `detect_template()` picks
between them by looking for real heading tags:

  'epub3'  — Finding Rest in the Nature of the Mind (2017). Real <h1>/<h2>
             with classes part4 / chapter4 / section / subchapter4 / section1;
             verse set as p.hanging0 / p.hanging4.
  'legacy' — A Guide to the Words of My Perfect Teacher (2004). No heading
             tags at all; headings are p.part-number + p.part-title,
             p.chapter-number + p.chapter-title, p.subhead, p.H1_1 … p.H4;
             verse set as p.body-text_block* / p.body-text_poem*.

A *-number paragraph is merged with the *-title paragraph that follows it, so
"CHAPTER FOUR" + "Actions: The Principle of Cause and Effect" becomes one
heading.

What is skipped
---------------
Cover, the ebook's own contents list, the index (its page references do not
survive as text), and Shambhala marketing / sign-up pages. Everything else —
forewords, introductions, main text, verse, endnotes, footnotes, glossary,
bibliography, appendices, copyright page — is kept. Set `keep_index=True` /
`keep_marketing=True` to retain them.

Images are not extracted; their captions are.

Inline: <em>/<i> → *italic*, <strong>/<b> → **bold**. Note reference numbers
in <sup> are kept inline as plain digits rather than converted to Markdown
footnote syntax — the endnote numbering is already in the notes section, and
inventing anchors risks mismatches.
"""

import argparse
import re
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup, NavigableString, Tag
import yaml


# ---------------------------------------------------------------------------
# Document-level filtering
# ---------------------------------------------------------------------------

SKIP_DOC_TOKENS = {'cvi', 'cover', 'toc', 'ind', 'index', 'marketing',
                   'advertisement'}

MARKETING_PATTERNS = (
    'sign up to receive news',
    'visit us online to sign up',
)


def doc_tokens(filename):
    stem = filename.rsplit('/', 1)[-1].rsplit('.', 1)[0]
    return set(re.split(r'[_\-]', stem.lower()))


def skip_document(filename, text, keep_index=False, keep_marketing=False):
    tokens = doc_tokens(filename)
    skip = set(SKIP_DOC_TOKENS)
    if keep_index:
        skip -= {'ind', 'index'}
    if keep_marketing:
        skip -= {'marketing', 'advertisement'}
    if tokens & skip:
        return True
    if not keep_marketing:
        low = text.lower()
        if any(pat in low for pat in MARKETING_PATTERNS) and len(text) < 400:
            return True
    return False


def is_body_document(filename):
    """Body chapters, prologue, conclusion, part pages — where verse lives."""
    tokens = doc_tokens(filename)
    if tokens & {'prl', 'con', 'conclusion'}:
        return True
    return any(re.fullmatch(r'(c|p)\d+', t) or 'chapter' in t or 'part' in t
               for t in tokens)


# ---------------------------------------------------------------------------
# Template detection and class maps
# ---------------------------------------------------------------------------

def detect_template(book):
    for item_id, _linear in book.spine:
        item = book.get_item_with_id(item_id)
        if not item or item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        soup = BeautifulSoup(item.get_content(), 'html.parser')
        if soup.find(['h1', 'h2', 'h3']):
            return 'epub3'
    return 'legacy'


# (tag, class) -> heading level, for the epub3 template
EPUB3_HEADINGS = {
    'part4': 1,
    'part1': 2,
    'part2': 3,
    'chapter4': 2,
    'chapter9': 2,
    'section': 3,
    'section1': 3,
    'subchapter4': 3,
}

EPUB3_VERSE_CLASSES = {'hanging0', 'hanging4'}
EPUB3_SKIP_CLASSES = {'conversion_code_partner', 'conversion_code_spec'}

# class -> heading level, for the legacy template
LEGACY_HEADINGS = {
    'part-number': 1,
    'part-title': 1,
    'foreword-title': 1,
    'chapter-number': 2,
    'chapter-title': 2,
    'subhead': 3,
    'H1_1': 3,
    'subhead1': 4,
    'H2_1': 4,
    'Block1a': 4,
    'H3a': 5,
    'H4': 5,
}

LEGACY_NUMBER_CLASSES = {'part-number', 'chapter-number'}
LEGACY_TITLE_AFTER_NUMBER = {'part-number': 'part-title',
                             'chapter-number': 'chapter-title'}
LEGACY_SKIP_PREFIXES = ('index-body', 'toc')


def classes(el):
    return [c for c in el.get('class', [])]


# ---------------------------------------------------------------------------
# Inline formatting
# ---------------------------------------------------------------------------

def inline_text(el):
    """Render an element's contents with *italic* / **bold** preserved."""
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
            elif child.name in ('img',):
                continue
            else:
                out.append(inline_text(child))
    return ''.join(out)


def heading_text(el):
    """
    Heading text without inline emphasis: these ebooks bold or italicise whole
    headings for print styling, which would otherwise land as ** inside the
    Markdown heading.
    """
    return clean(' '.join(el.get_text().split()))


def escape_leading_number(text):
    """
    Escape a verse number at the start of a line ("1. So now you have…") so
    Markdown does not turn the verse into an ordered list. Only the dot is
    escaped; the visible text is unchanged.
    """
    return re.sub(r'^(\d+)\.(\s)', r'\1\\.\2', text)


def clean(text):
    text = text.replace(' ', ' ')
    lines = [' '.join(line.split()) for line in text.split('\n')]
    return '\n'.join(line for line in lines).strip()


# ---------------------------------------------------------------------------
# Per-template paragraph handling
# ---------------------------------------------------------------------------

def render_epub3(el, in_body_doc):
    cls = set(classes(el))
    if cls & EPUB3_SKIP_CLASSES:
        return None, ''

    if el.name in ('h1', 'h2', 'h3', 'h4'):
        level = None
        for c in classes(el):
            if c in EPUB3_HEADINGS:
                level = EPUB3_HEADINGS[c]
                break
        if level is None:
            level = int(el.name[1])
        text = heading_text(el)
        return ('heading', '#' * level + ' ' + text) if text else (None, '')

    if el.name == 'blockquote':
        text = clean(el.get_text())
        if not text:
            return None, ''
        quoted = '\n'.join('> ' + line for line in text.split('\n') if line)
        return 'quote', quoted

    text = clean(inline_text(el))
    if not text:
        return None, ''
    if in_body_doc and (cls & EPUB3_VERSE_CLASSES):
        return 'verse', escape_leading_number(text)
    return 'plain', text


def render_legacy(el, in_body_doc, pending):
    cls = classes(el)
    for c in cls:
        if any(c.startswith(p) for p in LEGACY_SKIP_PREFIXES):
            return None, ''

    text = clean(inline_text(el))
    if not text:
        return None, ''

    # "CHAPTER FOUR" held until its title paragraph arrives
    for c in cls:
        if c in LEGACY_NUMBER_CLASSES:
            pending['number'] = text
            pending['expects'] = LEGACY_TITLE_AFTER_NUMBER[c]
            pending['level'] = LEGACY_HEADINGS[c]
            return None, ''

    if pending.get('expects') and pending['expects'] in cls:
        level = pending['level']
        combined = re.sub(r'\*+', '', pending['number'] + ': ' + text)
        pending.clear()
        return 'heading', '#' * level + ' ' + combined

    if pending.get('number'):
        level = pending['level']
        held = pending['number']
        pending.clear()
        return 'heading', '#' * level + ' ' + held

    for c in cls:
        if c in LEGACY_HEADINGS:
            return 'heading', ('#' * LEGACY_HEADINGS[c] + ' '
                               + re.sub(r'\*+', '', text))

    if in_body_doc and any(c.startswith(('body-text_block', 'body-text_poem'))
                           for c in cls):
        return 'verse', escape_leading_number(text)

    return 'plain', text


def render_table(table):
    """Render an HTML table as a Markdown table (abbreviation lists etc.)."""
    rows = []
    for tr in table.find_all('tr'):
        cells = [clean(inline_text(td)).replace('\n', ' ')
                 for td in tr.find_all(['td', 'th'])]
        if any(cells):
            rows.append(cells)
    if not rows:
        return ''
    width = max(len(r) for r in rows)
    rows = [r + [''] * (width - len(r)) for r in rows]
    out = ['| ' + ' | '.join(rows[0]) + ' |',
           '|' + '---|' * width]
    for r in rows[1:]:
        out.append('| ' + ' | '.join(r) + ' |')
    return '\n'.join(out) + '\n'


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

def dc(book, key):
    raw = book.get_metadata('DC', key)
    return raw[0][0] if raw else None


def extract_metadata(book, epub_path):
    contributors = [v for v, _ in (book.get_metadata('DC', 'contributor') or [])]
    d = {
        'title': dc(book, 'title'),
        'author': dc(book, 'creator'),
        'publisher': dc(book, 'publisher'),
        'date': dc(book, 'date'),
        'language': dc(book, 'language'),
        'isbn': dc(book, 'identifier'),
        'contributors': contributors or None,
        'source_file': epub_path.split('/')[-1],
        'source_description': 'Extracted from EPUB source',
    }
    return {k: v for k, v in d.items() if v}


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------

def convert_epub_to_markdown(epub_path, output_path, frontmatter=None,
                             keep_index=False, keep_marketing=False):
    book = epub.read_epub(epub_path)
    template = detect_template(book)

    body_md = ''
    skipped = []
    prev_kind = None
    pending = {}

    for item_id, _linear in book.spine:
        item = book.get_item_with_id(item_id)
        if not item or item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue

        name = item.get_name()
        soup = BeautifulSoup(item.get_content(), 'html.parser')
        for t in soup(['script', 'style']):
            t.decompose()
        body = soup.find('body')
        if not body:
            continue

        text = ' '.join(body.get_text().split())
        if not text:
            continue
        if skip_document(name, text, keep_index, keep_marketing):
            skipped.append((name.rsplit('/', 1)[-1], len(text)))
            continue

        in_body_doc = is_body_document(name)
        pending.clear()

        elements = body.find_all(['table', 'p', 'h1', 'h2', 'h3', 'h4',
                                  'blockquote', 'li'])
        for el in elements:
            if el.name == 'table':
                rendered = render_table(el)
                if rendered:
                    body_md += rendered + '\n'
                    prev_kind = 'table'
                continue

            # cells are emitted by render_table, not individually
            if el.find_parent('table'):
                continue

            # <li> inside a list we already rendered via its parent text
            if el.name == 'li':
                text_li = clean(inline_text(el))
                if text_li:
                    body_md += '- ' + text_li + '\n'
                    prev_kind = 'list'
                continue

            if el.find_parent('li'):
                continue
            if el.name == 'p' and el.find_parent('blockquote'):
                continue

            if template == 'epub3':
                kind, rendered = render_epub3(el, in_body_doc)
            else:
                kind, rendered = render_legacy(el, in_body_doc, pending)

            if not kind:
                continue

            if prev_kind == 'list' and kind != 'list':
                body_md += '\n'

            if kind == 'verse' and prev_kind == 'verse':
                # keep consecutive verse lines in one block
                body_md = body_md.rstrip('\n') + '\n' + rendered + '\n\n'
            else:
                body_md += rendered + '\n\n'
            prev_kind = kind

    meta = frontmatter if frontmatter is not None else extract_metadata(book, epub_path)
    fm = '---\n' + yaml.dump(meta, allow_unicode=True, sort_keys=False) + '---\n\n'

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(fm + body_md)

    print('Successfully extracted to ' + output_path)
    print('Template: ' + template)
    print('Headings: %d' % len(re.findall(r'(?m)^#{1,6} ', body_md)))
    if skipped:
        print('Skipped documents (%d):' % len(skipped))
        for name, size in skipped:
            print('  %-44s %7d chars' % (name, size))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='EPUB to Markdown — Shambhala trade ebooks')
    parser.add_argument('epub_path')
    parser.add_argument('output_path')
    parser.add_argument('--keep-index', action='store_true')
    parser.add_argument('--keep-marketing', action='store_true')
    args = parser.parse_args()
    convert_epub_to_markdown(args.epub_path, args.output_path,
                             keep_index=args.keep_index,
                             keep_marketing=args.keep_marketing)
