# Rules block for CLAUDE.md / AGENTS.md

Append the block below to the repository's `CLAUDE.md` (Claude Code) or `AGENTS.md` (other agents). It encodes the usage rules that make the layer a saving rather than a cost: narrow, budgeted, impact-first, memory for the reasons. Keep the budget caps; large first-retrieval packs get re-sent on every later turn and cost more than they save.

```markdown
## CortexDB Codeplane (code intelligence + memory)

This checkout is served by CortexDB over MCP (server `cortexdb`). Use its
tools BEFORE searching the filesystem:

- Locating code, "where does X happen", "what calls Y": `code_explore`
  with token_budget 1200 or less. It returns verbatim cited snippets
  (repo:path@<hash>#Lstart-Lend) with files_considered / files_included.
  Open a file only when the citation is not enough. Do not re-fetch the
  same context twice; refine the query instead.
- Before changing a function signature or behavior: `code_impact` on the
  symbol first. It lists callers and tests per hop with the weakest
  precision tier on each path. Name every affected caller before you edit.
- Browsing structure (files, symbols, routes): `code_inventory` and
  `code_graph` (bounded traversals) instead of grep sweeps.
- "Why is this code like this", past decisions, past bugs, who decided:
  `memory_search` first. Team memory holds this repository's history.
- After completing a task or learning a non-obvious constraint:
  `memory_store` one short factual note naming the files it concerns,
  so the next session starts where this one ended.
- Budgets are hard ceilings: keep every code_explore call at or under
  1500 tokens. Never dump large workspace context packs when a symbol
  or impact query answers the question.
- If CortexDB tools error or are unavailable, fall back to normal search
  and say so.
```
