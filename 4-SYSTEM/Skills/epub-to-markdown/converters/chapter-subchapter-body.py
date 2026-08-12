#!/usr/bin/env python3
"""
Converter: InDesign "Chapter / Sub-Chapter / Body" template (no colour coding)
Generated: 2026-08-12

First seen in: Chos_Go-q50uya.epub — ཆོས་ཀྱི་སྒོ་འབྱེད་, Spyan snga ba Blo gros
rgyal mtshan dpal bzang po, 2018 digital edition.

Publisher: absent from OPF metadata. This converter is not tied to one
publisher — it handles any epub whose paragraphs carry only the three
structural classes below and no colour-coded semantic classes. Check the
inspector profile first: if every `css_classes` entry is #000000 and the class
names are Chapter / Sub-Chapter / Body, this is the right converter.

CSS class -> Markdown mapping
-----------------------------
  Chapter      -> # heading
  Sub-Chapter  -> ## heading
  Body         -> plain text
  (no colour-coded classes, so no [[root|…]] / [[quote|…]] callouts)

Because there is no colour coding, semantic block types (root text, citation,
sa bcad) cannot be recovered from the epub — the source simply does not mark
them. Do not invent callouts here; a later pass over the Markdown can add them
if a human identifies the boundaries.

Structure notes
---------------
- The spine splits the work across one document per section, each named after
  the full title; `cover.xhtml` and `toc.xhtml` are skipped.
- A flat list of every Sub-Chapter label is emitted at the top of the file, in
  document order, as input for the `add-toc` skill (which infers the nesting
  from the Tibetan ordinals and adds `^toc-X-Y-Z` block IDs).
- Author: the OPF has no `creator`. The title page carries the label
  མཛད་པ་པོ། ("author") followed by the name in the next Body paragraph;
  `extract_metadata()` reads it from there.
"""

import argparse
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import yaml


CHAPTER_CLASSES = {'Chapter'}
SUBCHAPTER_CLASSES = {'Sub-Chapter'}
BODY_CLASSES = {'Body'}

SKIP_DOCS = ('cover.xhtml', 'toc.xhtml')

AUTHOR_LABEL = 'མཛད་པ་པོ།'   # "author" — title-page label


def is_utility(cls):
    return (
        cls.startswith('_id')
        or cls.startswith('ParaOverride')
        or cls.startswith('CharOverride')
    )


def semantic_classes(element):
    return {c for c in element.get('class', []) if not is_utility(c)}


def resolve_role(cls_set):
    if cls_set & CHAPTER_CLASSES:
        return 'chapter'
    if cls_set & SUBCHAPTER_CLASSES:
        return 'subchapter'
    if cls_set & BODY_CLASSES:
        return 'body'
    return None


def clean(text):
    """Collapse whitespace, including the leading tabs InDesign emits."""
    return ' '.join(text.split())


def content_docs(book):
    for item_id, _linear in book.spine:
        item = book.get_item_with_id(item_id)
        if not item or item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        if item.get_name().split('/')[-1] in SKIP_DOCS:
            continue
        yield item


def iter_paragraphs(book):
    for item in content_docs(book):
        soup = BeautifulSoup(item.get_content(), 'html.parser')
        for t in soup(['script', 'style']):
            t.decompose()
        body = soup.find('body')
        if not body:
            continue
        for el in body.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            yield el


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

def dc(book, key):
    raw = book.get_metadata('DC', key)
    return raw[0][0] if raw else None


def find_author(book):
    """Read the author from the title page: the paragraph after མཛད་པ་པོ།."""
    take_next = False
    for el in iter_paragraphs(book):
        text = clean(el.get_text())
        if take_next and text:
            return text
        if text == AUTHOR_LABEL:
            take_next = True
    return None


def extract_metadata(book, epub_path):
    source_id = None
    for val, attrs in book.get_metadata('DC', 'identifier') or []:
        if attrs.get('id') == 'BookId' or 'uuid' in str(val).lower():
            source_id = val
            break
    d = {
        'title': (dc(book, 'title') or 'Unknown Title').strip(),
        'author': dc(book, 'creator') or find_author(book) or 'Unknown Author',
        'date': dc(book, 'date'),
        'source_id': source_id,
        'source_file': epub_path.split('/')[-1],
        'source_description': 'Extracted from EPUB source',
    }
    return {k: v for k, v in d.items() if v is not None}


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------

def looks_like_heading(text):
    """
    A paragraph whose entire text is wrapped in Tibetan section marks ༼ … ༽
    is a section label, whatever class it carries. Some source files style a
    few of these as Body by mistake, which leaves a hole in the section
    numbering (see BUG-005 in converters/README.md).
    """
    return text.startswith('༼') and text.endswith('༽')


def convert_epub_to_markdown(epub_path, output_path, frontmatter=None,
                             draft_toc=True, promote_orphan_headings=False):
    """
    Convert the epub to Markdown.

    frontmatter: dict replacing the metadata read from the epub (use this to
                 write the 1-SOURCES frontmatter spec directly).
    draft_toc:   emit the flat Sub-Chapter list for the `add-toc` skill.
    promote_orphan_headings:
                 treat Body paragraphs that are wholly wrapped in ༼ … ༽ as
                 Sub-Chapters. Off by default — this is a structural repair of
                 the source, so turn it on deliberately and check the log of
                 what was promoted.
    """
    book = epub.read_epub(epub_path)
    promoted = []

    body_md = ''
    labels = []
    prev_role = None

    for el in iter_paragraphs(book):
        if el.name.startswith('h'):
            # Native headings only occur in the nav document, which is skipped;
            # keep the branch so stray headings are not silently dropped.
            text = clean(el.get_text())
            if text:
                body_md += '#' * int(el.name[1]) + ' ' + text + '\n\n'
            continue

        role = resolve_role(semantic_classes(el))
        text = clean(el.get_text())
        if not text:
            continue

        if role == 'body' and promote_orphan_headings and looks_like_heading(text):
            promoted.append(text)
            role = 'subchapter'

        if role == 'chapter':
            body_md += '# ' + text + '\n\n'
        elif role == 'subchapter':
            labels.append(text)
            body_md += '## ' + text + '\n\n'
        else:
            if role is None and prev_role is None:
                print('  [warn] unclassified paragraph: ' + text[:40])
            body_md += text + '\n\n'
        prev_role = role

    meta = frontmatter if frontmatter is not None else extract_metadata(book, epub_path)
    fm = '---\n' + yaml.dump(meta, allow_unicode=True, sort_keys=False) + '---\n\n'

    toc_block = ''
    if draft_toc and labels:
        toc_block = ('## དཀར་ཆག / Table of Contents\n\n'
                     + '\n'.join('- ' + label for label in labels)
                     + '\n\n---\n\n')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(fm + toc_block + body_md)

    print('Successfully extracted to ' + output_path)
    print('Sub-Chapter entries: %d' % len(labels))
    for text in promoted:
        print('  [promoted from Body] ' + text)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='EPUB to Markdown — Chapter/Sub-Chapter/Body template')
    parser.add_argument('epub_path', help='Path to the source EPUB file')
    parser.add_argument('output_path', help='Path to the output Markdown file')
    args = parser.parse_args()
    convert_epub_to_markdown(args.epub_path, args.output_path)
