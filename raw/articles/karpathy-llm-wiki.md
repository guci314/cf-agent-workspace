# LLM Wiki (Karpathy)

> **Source**: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
> **Author**: Andrej Karpathy
> **Captured**: 2026-09-21
> **Layer**: raw (immutable — LLM reads only, never modifies)
> **Note**: 以下是原文核心摘录；完整原文 11,923 字符，见上方 URL。

A pattern for building personal knowledge bases using LLMs.

## The core idea

Most people's experience with LLMs and documents looks like RAG: you upload files, the LLM retrieves relevant chunks at query time, and generates an answer. This works, but the LLM is rediscovering knowledge from scratch on every question. There's no accumulation.

The idea here is different. Instead of just retrieving from raw documents at query time, the LLM **incrementally builds and maintains a persistent wiki** — a structured, interlinked collection of markdown files that sits between you and the raw sources. When you add a new source, the LLM reads it, extracts the key information, and integrates it into the existing wiki — updating entity pages, revising topic summaries, noting where new data contradicts old claims. The knowledge is compiled once and then *kept current*, not re-derived on every query.

**The wiki is a persistent, compounding artifact.** You never write the wiki yourself — the LLM writes and maintains all of it. You're in charge of sourcing, exploration, and asking the right questions. "Obsidian is the IDE; the LLM is the programmer; the wiki is the codebase."

Applicable contexts: personal tracking, research deep-dives, reading a book (think Tolkien Gateway), business/team internal wikis, competitive analysis, due diligence.

## Architecture — three layers

**Raw sources** — curated source documents (articles, papers, images, data files). **Immutable** — the LLM reads from them but never modifies them. This is your source of truth.

**The wiki** — a directory of LLM-generated markdown files. Summaries, entity pages, concept pages, comparisons, an overview, a synthesis. The LLM owns this layer entirely. You read it; the LLM writes it.

**The schema** — a document (e.g. CLAUDE.md for Claude Code or AGENTS.md for Codex) that tells the LLM how the wiki is structured, what the conventions are, and what workflows to follow. This is the key configuration file — it's what makes the LLM a disciplined wiki maintainer rather than a generic chatbot.

## Operations

**Ingest.** Drop a new source into raw and tell the LLM to process it. Flow: LLM reads the source, discusses key takeaways, writes a summary page, updates the index, updates relevant entity and concept pages, and appends an entry to the log. *A single source might touch 10-15 wiki pages.*

**Query.** Ask questions against the wiki. The LLM searches relevant pages, reads them, and synthesizes an answer with citations. Answers can be a markdown page, comparison table, slide deck (Marp), chart (matplotlib), canvas. Key insight: **good answers can be filed back into the wiki as new pages** — explorations compound just like ingested sources.

**Lint.** Periodically health-check the wiki. Look for: contradictions between pages, stale claims that newer sources superseded, orphan pages with no inbound links, important concepts lacking their own page, missing cross-references, data gaps fillable by web search.

## Indexing and logging

**index.md** — content-oriented catalog. Each page listed with a link, a one-line summary, optional metadata. Organized by category. Updated on every ingest. When answering a query, the LLM reads the index first, then drills in. Works well at moderate scale (~100 sources, ~hundreds of pages) — avoids embedding-based RAG infrastructure.

**log.md** — chronological, append-only record of ingests, queries, lint passes. Tip: with a consistent prefix (e.g. `## [2026-04-02] ingest | Article Title`), the log is parseable with unix tools — `grep "^## \[" log.md | tail -5` gives the last 5 entries.

## Tooling notes

- qmd — local markdown search engine (hybrid BM25/vector + LLM re-ranking), ships CLI **and** MCP server
- Obsidian Web Clipper — converts web articles to markdown
- Marp — markdown slide decks
- Dataview — queries over YAML frontmatter
- "The wiki is just a git repo of markdown files."

## Why this works

The tedious part of maintaining a knowledge base is not reading or thinking — it's the **bookkeeping**. Updating cross-references, keeping summaries current, noting contradictions, maintaining consistency across dozens of pages. "Humans abandon wikis because the maintenance burden grows faster than the value." LLMs don't get bored, don't forget a cross-reference, and can touch 15 files in one pass.

Related in spirit to Vannevar Bush's Memex (1945): a personal, curated knowledge store with associative trails. Bush couldn't solve *who does the maintenance*. The LLM handles that.
