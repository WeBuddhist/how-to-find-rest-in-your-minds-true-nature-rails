#!/usr/bin/env python3
"""
Converter: RDI-SS series (Rigpe Dorje Institute, "SS" Tibetan source-text series)
Generated: 2026-08-12

Source epubs: RDI-SS-42-1 / RDI-SS-42-2 — Dza Patrul Rinpoche,
ཀུན་བཟང་བླ་མའི་ཞལ་ལུང་། (The Words of My Perfect Teacher), parts 1 and 2.

Publisher: absent from OPF metadata. The series is identified by the spine
document naming scheme (RDI-SS-<n>-<part>[-<doc>].xhtml). The InDesign CSS
template is the same family as the LEK-PHI series (see lekphi.py), with
several additional classes.

CSS class -> wiki markup mapping
--------------------------------
  Tibetan-Sabche                              (blue  #005e7f) -> [[toc|text]]
  Tibetan-External-Citations                  (gold  #897335) -> [[quote|text]]
  Tibetan-Citations-in-Verse_*                (gold  #897335) -> [[quote|…]] per stanza
  Tibetan-Commentary-in-Verse_*               (gold  #897335) -> [[verse|…]] per stanza
  Tibetan-Root-Text / Tibetan-Root-Text_*     (red   #8b1409) -> [[root|…]] per stanza
  Long-Root-Text-Middile-Line-                (red   #8b1409) -> [[root|…]]
  Tibetan-Chapter / Tibetan-Chapter-          (dark  #343233) -> # heading
  Tibetan-Heading                             (dark  #343233) -> ## heading
  Tibetan-karchak / Tibetan-Karchak           (dark)          -> ## heading
  Karchak-Indented[-lastline]                 (dark)          -> "- " list item
  Tibetan-Commentary[-Non-Indent|-Small] /
  Tibetan-Regular-Indented / Justification-Body                -> plain text
  Credits-Page_* / Front-* / Name-of-Author /
  Tibetan-Book-Title                                           -> skipped

Verse grouping
--------------
Verse families (citations, commentary-in-verse, root text) are split into
stanzas: a new callout starts on every *-First-Line paragraph and absorbs the
following Middle/Last lines. Grouping only on "same family" would merge the
whole homage section into a single block.

Karchak (དཀར་ཆག)
-----------------
The books carry their own printed table of contents. Its entries are kept as a
Markdown list in place (they carry the printed numbering, which the body sabche
labels do not). The generated TOC at the top of the file is still built from the
body sabche labels per the skill convention; inline sabche spans inside karchak
paragraphs are NOT collected into it, to avoid duplicate entries.

Markers
-------
No ༷ (U+0F37) root-text markers are present in these epubs. Part 1 contains 4
occurrences of ༵ (U+0F35, TIBETAN MARK NGAS BZUNG NYI ZLA) in the homage verse,
which mark a hidden proper name (མཁྱེན་བརྩེའི་འོད་ཟེར), not root text. They are
preserved verbatim rather than converted to bold.
"""

import argparse
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup, NavigableString, Tag
import yaml


# ---------------------------------------------------------------------------
# Semantic class resolution
# ---------------------------------------------------------------------------

def is_utility(cls):
    """Utility/override classes carry no semantic meaning."""
    return (
        cls.startswith('_id')
        or cls.startswith('ParaOverride')
        or cls.startswith('CharOverride')
    )


SABCHE_CLASSES = {
    'Tibetan-Sabche',
    'Tibetan-Sabche-After-Title-Chapter',
}

PROSE_CITATION_CLASSES = {'Tibetan-External-Citations'}

VERSE_CITATION_CLASSES = {
    'Tibetan-Citations-in-Verse_Tibetan-Citations-First-Line',
    'Tibetan-Citations-in-Verse_Tibetan-Citations-Middle-Lines',
    'Tibetan-Citations-in-Verse_Tibetan-Citations-Last-Line',
}

COMMENTARY_VERSE_CLASSES = {
    'Tibetan-Commentary-in-Verse_Tibetan-Commentary--First-Line',
    'Tibetan-Commentary-in-Verse_Tibetan-Commentary-First-Line',
    'Tibetan-Commentary-in-Verse_Tibetan-Commentary-Middle-Lines',
    'Tibetan-Commentary-in-Verse_Tibetan-Commentary-Last-Line',
}

ROOT_TEXT_CLASSES = {
    'Tibetan-Root-Text',
    'Tibetan-Root-Text_Tibetan-Root-Text-First-Line',
    'Tibetan-Root-Text_Tibetan-Root-Text-MIddle-Lines',
    'Tibetan-Root-Text_Tibetan-Root-Text-Middle-Lines',
    'Tibetan-Root-Text_Tibetan-Root-Text-Last-Line',
    'Long-Root-Text-Middile-Line-',
}

CHAPTER_CLASSES = {'Tibetan-Chapter', 'Tibetan-Chapter-'}
HEADING_CLASSES = {'Tibetan-Heading', 'Tibetan-karchak', 'Tibetan-Karchak'}
KARCHAK_CLASSES = {'Karchak-Indented', 'Karchak-Indented-lastline'}

SKIP_CLASSES = {
    'Credits-Page_Front-Page---Book-Number',
    'Credits-Page_Front-Title',
    'Credits-Page_Name-of-Author',
    'Front-page---Book-Number',
    'Front-Page---Text-Author',
    'Front-Page---Text-Titles',
    'Front-Title',
    'Name-of-Author',
    'Partners-Line',
    'Tibetan-Book-Title',
}

# Families whose consecutive paragraphs form one callout per stanza.
VERSE_FAMILIES = {
    'quote-verse': VERSE_CITATION_CLASSES,
    'verse': COMMENTARY_VERSE_CLASSES,
    'root': ROOT_TEXT_CLASSES,
}

# Spine documents that hold only cover art or credits.
FRONT_MATTER_SUFFIXES = ('cover.xhtml',)

# Reader-navigation boilerplate emitted by the epub exporter, not book content.
NAV_TEXTS = {'return to the table of contents', 'contents', 'landmarks'}


def semantic_classes(element):
    """Return meaningful CSS classes, stripping utility-only classes."""
    return {c for c in element.get('class', []) if not is_utility(c)}


def resolve_role(cls_set):
    """
    Map a set of CSS classes to a semantic role.
    Returns 'skip', 'chapter', 'heading', 'karchak', 'toc', 'lung',
    'quote-verse', 'verse', 'root', 'plain', or None (no opinion — inherit).
    """
    if not cls_set:
        return None
    if cls_set & SKIP_CLASSES:
        return 'skip'
    if cls_set & CHAPTER_CLASSES:
        return 'chapter'
    if cls_set & HEADING_CLASSES:
        return 'heading'
    if cls_set & KARCHAK_CLASSES:
        return 'karchak'
    if cls_set & SABCHE_CLASSES:
        return 'toc'
    if cls_set & ROOT_TEXT_CLASSES:
        return 'root'
    if cls_set & VERSE_CITATION_CLASSES:
        return 'quote-verse'
    if cls_set & COMMENTARY_VERSE_CLASSES:
        return 'verse'
    if cls_set & PROSE_CITATION_CLASSES:
        return 'lung'
    return 'plain'


def is_first_line(cls_set):
    """True if the paragraph class marks the opening line of a stanza."""
    return any('First-Line' in c or 'First-line' in c for c in cls_set)


# ---------------------------------------------------------------------------
# Run extraction (mixed inline spans)
# ---------------------------------------------------------------------------

def extract_runs(p_element):
    """
    Walk a <p>'s direct children and return [(role, text), …].
    Consecutive content with the same effective role is merged into one run.
    Role priority: span's own classes > paragraph's classes.
    """
    p_role = resolve_role(semantic_classes(p_element)) or 'plain'

    runs = []
    state = {'role': None, 'parts': []}

    def flush():
        if state['parts']:
            text = ''.join(state['parts']).strip()
            if text:
                runs.append((state['role'], text))
        state['parts'] = []

    def add(role, text):
        if role == state['role']:
            state['parts'].append(text)
        else:
            flush()
            state['role'] = role
            state['parts'] = [text]

    for child in p_element.children:
        if isinstance(child, NavigableString):
            text = str(child)
            if not text.strip():
                continue
            add(p_role, text)

        elif isinstance(child, Tag):
            if child.name == 'br':
                if state['parts']:
                    state['parts'].append('\n')
                continue

            span_role = resolve_role(semantic_classes(child))
            role = span_role if span_role is not None else p_role
            # Inside a verse paragraph the span classes just restate the
            # colour of the line; keep the paragraph's stanza role.
            if p_role in VERSE_FAMILIES and role in ('lung', 'plain', 'root'):
                role = p_role

            inner = []
            for sub in child.descendants:
                if isinstance(sub, NavigableString):
                    inner.append(str(sub))
                elif isinstance(sub, Tag) and sub.name == 'br':
                    inner.append('\n')
            text = ''.join(inner)
            if not text.strip():
                continue
            add(role, text)

    flush()
    return runs


# ---------------------------------------------------------------------------
# Block formatting
# ---------------------------------------------------------------------------

def wrap_callout(callout_type, text):
    return '[[' + callout_type + '|' + text.strip() + ']]\n\n'


CALLOUT_FOR_ROLE = {
    'toc': 'toc',
    'lung': 'quote',
    'quote-verse': 'quote',
    'verse': 'verse',
    'root': 'root',
}


def emit_run(role, text):
    """Emit one run as the appropriate Markdown block."""
    text = text.strip()
    if not text:
        return ''
    callout = CALLOUT_FOR_ROLE.get(role)
    if callout:
        return wrap_callout(callout, text)
    return text + '\n\n'


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

TITLES_EN = {
    '1': 'The Words of My Perfect Teacher (Kunzang Lama\'i Shelung), Part 1',
    '2': 'The Words of My Perfect Teacher (Kunzang Lama\'i Shelung), Part 2',
}


def dc(book, key):
    raw = book.get_metadata('DC', key)
    return raw[0][0] if raw else None


def opf_meta(book):
    result = {}
    ns = 'http://www.idpf.org/2007/opf'
    for val, attrs in book.metadata.get(ns, {}).get('meta', []):
        name = attrs.get('name') or attrs.get('property')
        content = attrs.get('content') or val
        if name:
            result[name] = content
    return result


def detect_part(book):
    for item_id, _ in book.spine:
        item = book.get_item_with_id(item_id)
        if not item:
            continue
        name = item.get_name().split('/')[-1]
        if name.startswith('RDI-SS-'):
            bits = name.replace('.xhtml', '').split('-')
            if len(bits) >= 4:
                return bits[3]
    return None


def extract_metadata(book, epub_path):
    meta = opf_meta(book)
    source_id = None
    for val, attrs in book.get_metadata('DC', 'identifier') or []:
        if attrs.get('id') == 'BookId' or 'uuid' in str(val).lower():
            source_id = val
            break
    part = detect_part(book)
    d = {
        'title': (dc(book, 'title') or 'Unknown Title').strip(),
        'title_en': TITLES_EN.get(part),
        'author': dc(book, 'creator') or 'Unknown Author',
        'author_en': 'Dza Patrul Rinpoche',
        'language': 'bo',
        'part': int(part) if part and part.isdigit() else part,
        'date': dc(book, 'date'),
        'source_id': source_id,
        'source_file': epub_path.split('/')[-1],
        'source_description': 'Extracted from EPUB source (RDI-SS-42 series)',
    }
    calibre_sort = meta.get('calibre:title_sort')
    if calibre_sort:
        d['calibre_title_sort'] = calibre_sort
    return {k: v for k, v in d.items() if v is not None}


# ---------------------------------------------------------------------------
# Document processing
# ---------------------------------------------------------------------------

def process_body(body):
    """
    Return (markdown, sabche_labels) for one spine document.
    Verse families are grouped into one callout per stanza; karchak entries
    become list items; inline sabche spans inside karchak are not collected
    into the generated TOC.
    """
    elements = body.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    md = ''
    sabche_labels = []
    i = 0

    while i < len(elements):
        el = elements[i]

        if el.name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            text = el.get_text().strip()
            if text:
                md += '#' * int(el.name[1]) + ' ' + text + '\n\n'
            i += 1
            continue

        cls = semantic_classes(el)
        role = resolve_role(cls)

        # Navigation boilerplate ("Return to the table of contents" links)
        if ' '.join(el.get_text().split()).lower() in NAV_TEXTS:
            i += 1
            continue

        if role == 'skip':
            i += 1
            continue

        if role == 'chapter':
            text = el.get_text().strip()
            if text:
                md += '# ' + text + '\n\n'
            i += 1
            continue

        if role == 'heading':
            text = el.get_text().strip()
            if text:
                md += '## ' + text + '\n\n'
            i += 1
            continue

        if role == 'karchak':
            text = ' '.join(el.get_text().split())
            if text:
                md += '- ' + text + '\n'
                if i + 1 >= len(elements) or \
                        resolve_role(semantic_classes(elements[i + 1])) != 'karchak':
                    md += '\n'
            i += 1
            continue

        if role in VERSE_FAMILIES:
            family = role
            lines = []
            j = i
            while j < len(elements):
                j_cls = semantic_classes(elements[j])
                if resolve_role(j_cls) != family:
                    break
                # A new *-First-Line paragraph opens the next stanza.
                if j > i and is_first_line(j_cls):
                    break
                t = ' '.join(elements[j].get_text().split())
                if t:
                    lines.append(t)
                j += 1
            if lines:
                md += wrap_callout(CALLOUT_FOR_ROLE[family], '\n'.join(lines))
            i = j if j > i else i + 1
            continue

        runs = extract_runs(el)
        for idx, (run_role, text) in enumerate(runs):
            if run_role == 'toc':
                sabche_labels.append(' '.join(text.split()))
            block = emit_run(run_role, text)
            # Keep a following run on the same line, e.g. [[toc|label]]prose
            if idx < len(runs) - 1:
                block = block.rstrip('\n')
            md += block

        i += 1

    return md, sabche_labels


# ---------------------------------------------------------------------------
# Main conversion
# ---------------------------------------------------------------------------

def convert_epub_to_markdown(epub_path, output_path):
    book = epub.read_epub(epub_path)

    metadata = extract_metadata(book, epub_path)
    frontmatter = ('---\n'
                   + yaml.dump(metadata, allow_unicode=True, sort_keys=False)
                   + '---\n\n')

    body_md = ''
    all_labels = []

    for item_id, _linear in book.spine:
        item = book.get_item_with_id(item_id)
        if not item or item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue

        fname = item.get_name().split('/')[-1]
        if fname.endswith(FRONT_MATTER_SUFFIXES) or fname == 'toc.xhtml':
            continue

        soup = BeautifulSoup(item.get_content(), 'html.parser')
        for t in soup(['script', 'style']):
            t.decompose()
        body = soup.find('body')
        if not body:
            continue

        doc_md, doc_labels = process_body(body)
        if doc_md.strip():
            if body_md:
                body_md += '---\n\n'
            body_md += doc_md
        all_labels.extend(doc_labels)

    toc_block = ''
    if all_labels:
        toc_lines = ['- ' + label for label in all_labels]
        toc_block = ('## ས་བཅད་ / Outline\n\n'
                     + '\n'.join(toc_lines) + '\n\n---\n\n')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(frontmatter + toc_block + body_md)

    print('Successfully extracted to ' + output_path)
    print('Outline (sabche) entries: %d' % len(all_labels))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='EPUB to Markdown — RDI-SS series')
    parser.add_argument('epub_path', help='Path to the source EPUB file')
    parser.add_argument('output_path', help='Path to the output Markdown file')
    args = parser.parse_args()
    convert_epub_to_markdown(args.epub_path, args.output_path)
