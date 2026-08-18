# Archived: Web-product open-source reuse evaluation

> Historical note: this 2026-06-29 evaluation predates the Agent Project OS v0.1 local-first protocol decision. Its Vercel/PostgreSQL product assumptions are not current architecture. It is retained only as input to a possible future read-only control-plane projection.

# Open Source Reuse Evaluation

Research date: 2026-06-29

## Requirement Recap

The target system needs to support:

- cross-agent project collaboration records.
- online progress tracking.
- static output and document management.
- historical project documents.
- model-neutral and agent-neutral writes.
- deployment on Vercel.
- built-in prompts that normalize agent writes.
- open-source reuse first.

## Short Conclusion

No single open-source project found so far matches all requirements directly.

The closest full products are strong in either project management or knowledge management, but they are not designed as a Vercel-native, model-neutral, cross-agent project documentation framework.

Recommended path:

1. Reuse an open-source Vercel-native docs framework as the base UI and document layer.
2. Reuse mature open-source editor, schema, auth, and database components.
3. Borrow concepts from agent-oriented frameworks, but keep our write protocol custom and lightweight.

Best base direction:

- Build on `Fumadocs` or `Nextra` for the project/document library.
- Add our own project registry, progress ledger, artifact catalog, and agent write API.
- Optionally integrate `Tiptap` or `Yoopta` for browser editing.
- Optionally integrate `Liveblocks` only if realtime collaboration becomes a must-have.

## Candidate Matrix

| Project | Type | Reuse Fit | Vercel Fit | License | Recommendation |
| --- | --- | --- | --- | --- | --- |
| Plane | Project management | High for tasks/projects/docs | Low | AGPL-3.0 | Reference or fork only if Docker self-host is acceptable |
| OpenProject | Project management | High for enterprise PM | Low | GPL | Too heavy for this Vercel-first product |
| Docmost | Wiki/documentation | High for wiki/history/collab | Low | AGPL-3.0 core | Good reference for docs UX, not ideal as base |
| Outline | Team knowledge base | Medium-high for docs | Low | Open source repo, product-oriented server stack | Good reference, not ideal as base |
| AppFlowy | Notion-like workspace | High for docs/tasks | Low-medium | AGPL-3.0 | Strong product, too large and not Vercel-native |
| AFFiNE | Notion/Miro-like workspace | High for docs/canvas | Low-medium | Open source, check exact repo licensing before fork | Strong product, too broad for MVP |
| Agentic Project Management | Agent project framework | High for agent workflow concepts | Medium | MPL-2.0 | Reuse concepts/protocol ideas, not full app base |
| knowledge-base-server | Agent memory/MCP | Medium for cross-agent memory | Medium-low | Check repo license before reuse | Good integration/reference for MCP memory, not UI base |
| Tasks.md | Markdown Kanban | Medium for file-backed tasks | Low | Check repo license before reuse | Useful idea: Markdown-backed task cards |
| Fumadocs | Docs framework | High for Vercel docs UI | High | MIT | Strong candidate for base |
| Nextra | Docs framework | High for Vercel docs UI | High | MIT | Strong candidate for base |
| Tiptap | Rich-text editor framework | High for document editing | High | Check current package licenses before integration | Best editor component candidate |
| Yoopta Editor | Notion-like editor | Medium-high for document editing | High | Check current repo license before integration | Alternative editor component |
| Liveblocks examples | Realtime collaboration components | Medium-high for realtime editing | High | Examples are open source, SaaS dependency | Optional, only if realtime is required |

## Direct Reuse Assessment

### Plane

Plane is the strongest full project-management candidate. It already has projects, issues, cycles, roadmap-style planning, docs, and triage. It is open source under AGPL-3.0.

Why it is not a direct fit:

- It is a large project management product, not a project document memory framework.
- It uses a multi-service stack and is not Vercel-native.
- It does not solve agent-neutral write protocols out of the box.
- Forking it would likely make the product heavier than needed.

Best use:

- Study its project/task/docs information architecture.
- Reuse only if we decide to abandon Vercel-first deployment and accept Docker/self-host.

### Docmost

Docmost is a strong collaborative wiki and documentation product with realtime collaboration, page history, comments, search, permissions, diagrams, spaces, and attachments.

Why it is not a direct fit:

- It is primarily a wiki, not a progress ledger plus agent write framework.
- It is not Vercel-native.
- Agent write normalization would still need to be custom.

Best use:

- Reference its document history, comments, spaces, permissions, and attachment model.

### Outline

Outline is a mature collaborative knowledge base built with React and Node.js.

Why it is not a direct fit:

- It is optimized for team knowledge base workflows.
- It requires its own server/runtime setup.
- It does not model cross-agent progress events or artifact evidence.

Best use:

- Reference its knowledge-base navigation and document UX.

### AppFlowy / AFFiNE

These are broad Notion-like or Notion/Miro-like workspaces. They are feature-rich and open-source-oriented, with docs, databases, tasks, knowledge management, collaboration, and AI features.

Why they are not a direct fit:

- They are much broader than the target.
- They are not optimized for a small Vercel-hosted project library.
- They would make customization and deployment heavier than necessary.

Best use:

- Reference block editing, database-like views, and project/workspace organization.

### Agentic Project Management

APM is closest in spirit to cross-agent project coordination. It structures complex AI-assisted projects across specialized agents and handoffs.

Why it is not a direct fit:

- It is a framework/process layer, not the Vercel-hosted document management app.
- It does not replace the need for our project registry, UI, artifact catalog, and source-of-truth documents.

Best use:

- Borrow concepts around agent roles, handoffs, task decomposition, and context continuity.

### knowledge-base-server

knowledge-base-server is directly relevant to the "one brain, multiple agents" problem. It focuses on persistent memory, MCP, REST APIs, SQLite FTS, Obsidian sync, and multi-agent retrieval.

Why it is not a direct fit:

- It is a memory server, not a project progress/document management UI.
- Its storage and deployment shape do not directly match Vercel-first hosting.

Best use:

- Consider a later MCP integration.
- Borrow memory ingestion and retrieval ideas.

## Recommended Assembly Plan

### Base

Use `Fumadocs` or `Nextra`.

Reason:

- Vercel-friendly.
- Markdown/MDX-first.
- open-source and lightweight.
- aligned with a project-document library.
- easier to customize than forking a large PM/wiki product.

Preference:

- `Fumadocs` if we want more customizable app-like documentation UI.
- `Nextra` if we want the fastest minimal docs portal.

### Application Layer

Build custom modules:

- Project registry.
- Workstream tracker.
- Task tracker.
- Progress ledger.
- Artifact catalog.
- Decision records.
- Agent activity.
- Review queue for agent writes.

### Data Layer

Use:

- PostgreSQL for operational state.
- Drizzle ORM or Prisma.
- Markdown/MDX files for portable docs.
- Zod for agent write validation.

### Editor Layer

Start with Markdown/MDX forms and preview.

Add later:

- Tiptap for rich-text editing.
- Yoopta if we want Notion-like blocks.
- Liveblocks if true realtime collaboration becomes necessary.

### Agent Layer

Keep custom:

- `/api/agent/write`
- write payload schema.
- built-in prompts.
- validation rules.
- trust levels.
- review queue.

Borrow from:

- Agentic Project Management for handoff/workflow concepts.
- knowledge-base-server for future MCP/memory integration.

## Final Recommendation

Do not fork Plane, Docmost, Outline, AppFlowy, or AFFiNE as the base for this project unless the requirement changes from "Vercel-first lightweight project library" to "self-hosted full workspace".

For this requirement, the better open-source reuse strategy is:

```text
Fumadocs or Nextra
+ Next.js App Router
+ PostgreSQL
+ Drizzle or Prisma
+ Zod
+ custom agent write protocol
+ optional Tiptap/Liveblocks later
```

This keeps the product small, deployable, agent-neutral, and easier to evolve.

## Source Links

- Plane: https://github.com/makeplane/plane
- OpenProject: https://github.com/opf/openproject
- Docmost: https://github.com/docmost/docmost
- Outline: https://github.com/outline/outline
- AppFlowy: https://github.com/AppFlowy-IO/AppFlowy
- AFFiNE: https://github.com/toeverything/AFFiNE
- Agentic Project Management: https://github.com/sdi2200262/agentic-project-management
- knowledge-base-server: https://github.com/willynikes2/knowledge-base-server
- Tasks.md: https://github.com/BaldissaraMatheus/Tasks.md
- Fumadocs: https://github.com/fuma-nama/fumadocs
- Nextra: https://github.com/shuding/nextra
- Tiptap: https://github.com/ueberdosis/tiptap
- Yoopta Editor: https://github.com/yoopta-editor/Yoopta-Editor
- Liveblocks examples: https://liveblocks.io/examples
