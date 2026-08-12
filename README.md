# How to Find Rest in Your Mind's True Nature — rails

A collaborative [Obsidian](https://obsidian.md) vault that makes AI-powered work on a **classical text** reliable, traceable, and consistent at scale.

This vault is the home for a series of **practice plans** built on the practice programme Longchenpa lays out in *Semnyi Ngalso* (སེམས་ཉིད་ངལ་གསོ།, *Finding Rest in the Nature of Mind*) — day-by-day, calendar-driven arcs that carry a practitioner through the stages of that programme in their own language.

## The text

The **root text** of this vault is Longchenpa's practice manual for *Semnyi Ngalso*:

> རྫོགས་པ་ཆེན་པོ་སེམས་ཉིད་ངལ་གསོའི་གནས་གསུམ་དགེ་བ་གསུམ་གྱི་དོན་ཁྲིད་བྱང་ཆུབ་ལམ་བཟང་
> *The Excellent Path to Enlightenment* (*don khrid byang chub lam bzang*) — the *don khrid*, or practice guide, to the three-part, threefold-virtue structure of *Semnyi Ngalso*.
> [`1-SOURCES/Text/bo-don-khrid-byang-chub-lam-bzang.md`](1-SOURCES/Text/bo-don-khrid-byang-chub-lam-bzang.md)

This is the text the practice plans are keyed to: it is the document that says *what to practise, in what order*.

Everything that explains or elaborates that programme is filed as a **commentary** in [`1-SOURCES/Commentaries/`](1-SOURCES/Commentaries/) — including *Semnyi Ngalso* itself, both its root verses and Longchenpa's own auto-commentary *Shingta Chenpo* (*The Great Chariot*), alongside the commentaries of later masters in the lineage. The first commentary ingested is Patrul Rinpoche's *Kunzang Lamé Zhalung* (*The Words of My Perfect Teacher*, `registered_id: kzls`), which is the standard oral-tradition exposition of the preliminary stages of the same programme.

Liturgies, prayer texts, and other related material that a practitioner uses alongside the programme — for example the ngöndro liturgy *Tarlam Rabsal* — are filed as **references** in [`1-SOURCES/References/`](1-SOURCES/References/).

Full vault-specific conventions — the addressing scheme, the registered commentary roster, the language tracks — live in [`4-SYSTEM/Guidelines/vault-annex.md`](4-SYSTEM/Guidelines/vault-annex.md).

## Why

AI models are powerful but unreliable at scale. Hand a model a classical text and a stack of commentary and ask for a translation, an adaptation, a study guide, or a daily reading, and what comes back looks fluent but is hard to trust:

- **Hallucinations** — fabricated meanings that sound plausible.
- **Inconsistency** — the same technical term rendered three different ways across one document.
- **Style drift** — register shifts as the context window fills.
- **No traceability** — no way to verify whether any specific claim is grounded in the commentary tradition or invented on the spot.
- **Doesn't scale** — every new output rediscovers the same interpretive work from scratch.

These failures aren't because the model is weak. They happen because the model is being asked to be **two different specialists at once** — a source-language domain expert who understands every nuance the commentary tradition has worked out, *and* a target-language stylist who knows how to render that meaning for a specific audience. With no preparation and no division of labour, it tries to do both jobs at generation time, in the same prompt, from raw sources. The drift is structural.

For practice plans the stakes are higher than for a study document: a plan is instruction someone will actually follow, day after day, and a drifted rendering of a meditation instruction is not a cosmetic error.

## How

The fix is to separate the two specialists, then let them collaborate.

**`2-RAILS/` is the source-language specialist, made permanent.** A pre-built, citation-grounded knowledge base of the commentary tradition — every sense distinction, every compound analysis, every commentator's reading — compiled once, by an LLM under domain-specialist review, with every claim citing the human source that grounds it.

**Each track in `3-TRANSFORMATIONS/` is a target-language specialist for one audience.** A Plan track is a specialist in pacing a study-and-practice arc along a calendar. A Translation track is a specialist in writing for a particular language and readership. An Adaptation track is a specialist in writing for a particular format (children's, scholarly, sermon). Each one is bound by its own `requirements.md` (style contract) and `termbase.md` (vocabulary contract).

Two principles hold the collaboration together:

- **Descriptive rails, prescriptive transformations.** The source specialist *describes* what the tradition attests: every commentator, every translator, every attested rendering. Each target specialist *prescribes* what *their* output does for *their* audience.
- **One-way citation chain.** `1-SOURCES/ → 2-RAILS/ → 3-TRANSFORMATIONS/`. Target specialists cite the source specialist; they never reach past the rails into raw commentary.

This is what makes the methodology scale. The expensive interpretive work happens once, in `2-RAILS/`, and is amortised over every plan, in every language, ever produced from the vault. **Lay the rails once; run many transformations on them.**

For the full reasoning — the specialist-pair and Wikipedia analogies — see [`4-SYSTEM/Guidelines/why-rails.md`](4-SYSTEM/Guidelines/why-rails.md).

## What

The vault is a four-stage pipeline. Each stage has its own folder; each folder's `About <Folder>.md` is the authoritative source on what goes in it and how.

```
1-SOURCES/   →   2-RAILS/   →   3-TRANSFORMATIONS/
human            original-       per-output prescriptive
authoritative    language        rails plus the
material         descriptive     AI-generated output
                 context

                ▲
                │ all driven by
                │
              4-SYSTEM/   skills, templates, methodology
```

- **[`1-SOURCES/`](1-SOURCES/)** — read-only ground truth.
  - `Text/` — the root text: the *don khrid byang chub lam bzang* practice manual.
  - `Commentaries/` — *Semnyi Ngalso* root verses and auto-commentary, plus the disciple and lineage commentaries (*Kunzang Lamé Zhalung* and others).
  - `References/` — liturgies, prayer texts, and related works used alongside the programme.
  - `Translations/`, `Audio/` — existing published translations and recitation or teaching recordings.
- **[`2-RAILS/`](2-RAILS/)** — original-language descriptive context at every level a transformation might need: section summaries, verse packages, per-term wiki articles, bilingual glossaries. Every claim cites `1-SOURCES/`.
- **[`3-TRANSFORMATIONS/`](3-TRANSFORMATIONS/)** — three categories of output. **Plans** is the primary track for this vault; **Translations** and **Adaptations** support it. Each track is governed by `requirements.md` (style contract) + `termbase.md` (vocabulary contract); the AI-generated output files sit alongside, citing the rails.
- **[`4-SYSTEM/`](4-SYSTEM/)** — skills and workflows for every stage of the pipeline, plus cross-cutting methodology docs and templates.

Each practice plan is a subfolder of [`3-TRANSFORMATIONS/Plans/`](3-TRANSFORMATIONS/Plans/) with one self-contained subfolder per published language, a day-by-day schedule, per-session day files, and ready-to-send notification copy. See [`3-TRANSFORMATIONS/Plans/About Plans.md`](3-TRANSFORMATIONS/Plans/About%20Plans.md) for the plan structure and how to start a new one.

## Getting started — pick your path

### If you are a human contributor

1. **This README** — the text · Why · How · What (you are here).
2. [Set up the vault on your computer](4-SYSTEM/How-to%20guides/Set%20up%20the%20vault.md) — install Obsidian, install Git, clone the repo, open it as a vault.
3. [Sync and troubleshoot](4-SYSTEM/How-to%20guides/Sync%20and%20troubleshoot.md) — how everyone's edits stay in sync; what to do when something goes wrong.
4. [`4-SYSTEM/Guidelines/why-rails.md`](4-SYSTEM/Guidelines/why-rails.md) — the specialist-pair and Wikipedia analogies in full.
5. [`4-SYSTEM/Guidelines/0-VAULT-Structure.md`](4-SYSTEM/Guidelines/0-VAULT-Structure.md) — the architecture and the citation chain.
6. [`1-SOURCES/About Sources.md`](1-SOURCES/About%20Sources.md) — rules for collecting, formatting, and linking source material.
7. [`2-RAILS/About Rails.md`](2-RAILS/About%20Rails.md) — the schema for the descriptive rails.
8. [`3-TRANSFORMATIONS/About Transformations.md`](3-TRANSFORMATIONS/About%20Transformations.md) — how transformation tracks are set up and how outputs are produced.
9. [`3-TRANSFORMATIONS/Plans/About Plans.md`](3-TRANSFORMATIONS/Plans/About%20Plans.md) — the practice-plan convention: session shape, language streams, day files.
10. [`4-SYSTEM/Guidelines/vault-annex.md`](4-SYSTEM/Guidelines/vault-annex.md) — the conventions specific to *this* vault.
11. [`4-SYSTEM/Skills/SKILLS-CATALOG.md`](4-SYSTEM/Skills/SKILLS-CATALOG.md) — every workflow skill, grouped by pipeline stage.

For day-to-day workflows not in the Skills catalog, see the rest of [`4-SYSTEM/How-to guides/`](4-SYSTEM/How-to%20guides/).

### If you are an AI agent

1. [`4-SYSTEM/CLAUDE.md`](4-SYSTEM/CLAUDE.md) — operational instructions: citation chain, write permissions, do-nots, standard operations. Read in full before touching any file.
2. The `About <Folder>.md` for the folder you're working in — [`1-SOURCES/About Sources.md`](1-SOURCES/About%20Sources.md), [`2-RAILS/About Rails.md`](2-RAILS/About%20Rails.md), or [`3-TRANSFORMATIONS/About Transformations.md`](3-TRANSFORMATIONS/About%20Transformations.md). Each is the canonical authority for that folder's rules.
3. [`4-SYSTEM/Guidelines/vault-annex.md`](4-SYSTEM/Guidelines/vault-annex.md) — vault-specific conventions, including the registered commentary roster.
4. The relevant `4-SYSTEM/Skills/<skill>/SKILL.md` for the specific task.

`AGENTS.md` files exist for tooling that expects them ([`4-SYSTEM/gemini-scribe/AGENTS.md`](4-SYSTEM/gemini-scribe/AGENTS.md)) — they are thin pointers to `CLAUDE.md` and the folder docs.
