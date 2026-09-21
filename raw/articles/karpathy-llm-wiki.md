# LLM Wiki

> 原始来源：https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
> 作者：Andrej Karpathy ｜ 创建：2026-04-04 ｜ 星标 5000+
> 存档日期：2026-09-21 ｜ 原文 11923 字符

A pattern for building personal knowledge bases using LLMs.

This is an idea file, it is designed to be copy pasted to your own LLM Agent.
Its goal is to communicate the high level idea, but your agent will build out
the specifics in collaboration with you.

## The core idea

Most people's experience with LLMs and documents looks like RAG: you upload a
collection of files, the LLM retrieves relevant chunks at query time, and
generates an answer. This works, but the LLM is rediscovering knowledge from
scratch on every question. There's no accumulation.

... Instead, the LLM **incrementally builds and maintains a persistent wiki** —
a structured, interlinked collection of markdown files that sits between you and
the raw sources. When you add a new source, the LLM doesn't just index it for
later retrieval. It reads it, extracts the key information, and integrates it
into the existing wiki — updating entity pages, revising topic summaries, noting
where new data contradicts old claims, strengthening or challenging the evolving
synthesis. The knowledge is compiled once and then *kept current*, not re-derived
on every query.

**The wiki is a persistent, compounding artifact.** The cross-references are
already there. The contradictions have already been flagged. The synthesis
already reflects everything you've read.

You never (or rarely) write the wiki yourself — the LLM writes and maintains all
of it. You're in charge of sourcing, exploration, and asking the right questions.

> "Obsidian is the IDE; the LLM is the programmer; the wiki is the codebase."

## Architecture — three layers

**Raw sources** — your curated collection of source documents. Articles, papers,
images, data files. These are immutable — the LLM reads from them but never
modifies them. This is your source of truth.

**The wiki** — a directory of LLM-generated markdown files. Summaries, entity
pages, concept pages, comparisons, an overview, a synthesis. The LLM owns this
layer entirely. You read it; the LLM writes it.

**The schema** — a document (e.g. CLAUDE.md for Claude Code or AGENTS.md for
Codex) that tells the LLM how the wiki is structured, what the conventions are,
and what workflows to follow. This is the key configuration file — it's what
makes the LLM a disciplined wiki maintainer rather than a generic chatbot. You
and the LLM co-evolve this over time.

## Operations

**Ingest.** Drop a new source into the raw collection and tell the LLM to
process it. Flow: read the source → discuss key takeaways → write a summary page
→ update the index → update relevant entity and concept pages → append to the
log. A single source might touch 10-15 wiki pages.

**Query.** Ask questions against the wiki. The LLM searches for relevant pages,
reads them, and synthesizes an answer with citations. Answers can take different
forms — a markdown page, a comparison table, a slide deck (Marp), a chart
(matplotlib), a canvas. **Good answers can be filed back into the wiki as new
pages.** This way your explorations compound in the knowledge base just like
ingested sources do.

**Lint.** Periodically, ask the LLM to health-check the wiki. Look for:
contradictions between pages, stale claims that newer sources have superseded,
orphan pages with no inbound links, important concepts mentioned but lacking
their own page, missing cross-references, data gaps that could be filled with a
web search.

## Indexing and logging

Two special files help the LLM (and you) navigate the wiki as it grows.

**index.md** is content-oriented. It's a catalog of everything in the wiki —
each page listed with a link, a one-line summary, and optionally metadata like
date or source count. Organized by category. The LLM updates it on every ingest.
When answering a query, the LLM reads the index first to find relevant pages,
then drills into them. This works surprisingly well at moderate scale (~100
sources, ~hundreds of pages) and avoids the need for embedding-based RAG
infrastructure.

**log.md** is chronological. It's an append-only record of what happened and
when — ingests, queries, lint passes. A useful tip: if each entry starts with a
consistent prefix (e.g. `## [2026-04-02] ingest | Article Title`), the log
becomes parseable with simple unix tools — `grep "^## \[" log.md | tail -5`
gives you the last 5 entries.

## Optional: CLI tools

At some point you may want to build small tools that help the LLM operate on the
wiki more efficiently. A search engine over the wiki pages is the most obvious
one — at small scale the index file is enough. [qmd](https://github.com/tobi/qmd)
is a good option: a local search engine for markdown files with hybrid
BM25/vector search and LLM re-ranking, all on-device. It has both a CLI and an
MCP server.

## Tips and tricks

- **Obsidian Web Clipper** — browser extension that converts web articles to markdown.
- **Download images locally** — set "Attachment folder path" to `raw/assets/`,
  bind a hotkey to "Download attachments for current file".
- **Obsidian's graph view** — best way to see the shape of your wiki.
- **Marp** — markdown-based slide deck format.
- **Dataview** — Obsidian plugin that runs queries over page frontmatter.
- The wiki is just a git repo of markdown files. You get version history,
  branching, and collaboration for free.

## Why this works

The tedious part of maintaining a knowledge base is not the reading or the
thinking — it's the bookkeeping. Updating cross-references, keeping summaries
current, noting when new data contradicts old claims, maintaining consistency
across dozens of pages. Humans abandon wikis because **the maintenance burden
grows faster than the value**. LLMs don't get bored, don't forget to update a
cross-reference, and can touch 15 files in one pass. The wiki stays maintained
because the cost of maintenance is near zero.

The human's job is to curate sources, direct the analysis, ask good questions,
and think about what it all means. The LLM's job is everything else.

> The idea is related in spirit to Vannevar Bush's Memex (1945). Bush's vision
> was closer to this than to what the web became: private, actively curated,
> with the connections between documents as valuable as the documents
> themselves. The part he couldn't solve was who does the maintenance. The LLM
> handles that.

## Note

This document is intentionally abstract. It describes the idea, not a specific
implementation. The exact directory structure, the schema conventions, the page
formats, the tooling — all of that will depend on your domain, your preferences,
and your LLM of choice. Everything mentioned above is optional and modular.
