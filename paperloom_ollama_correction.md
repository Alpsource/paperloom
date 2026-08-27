# Paperloom spec — corrections and additions

**How to apply:** replace Section 11 of `paperloom.md` entirely with the "New Section 11" below. Insert the "Section 8 addition" as new subsections at the end of Section 8 (right before `## 9. The MCP server`). Add the one new tool described in "Tool addition" to Section 9's list, bringing the total to 10 tools.

---

## New Section 11: model-agnostic architecture (replaces "Ollama backend")

**Non-goal: paperloom does not call an LLM.** Ever. Not for synthesis, not for classification, not for embedding. The MCP server is pure file operations. This is design principle #1 and #4 from Section 1; this section explains what that means for users who want to run paperloom against local models.

### The correct boundary

```
┌──────────────────────────────────────────────────────────┐
│  HOST AGENT (any MCP-compatible client)                  │
│  - Claude Code           → Anthropic API                 │
│  - Continue.dev          → any model incl. Ollama        │
│  - Cline (VSCode)        → any model incl. Ollama        │
│  - Aider                 → any model incl. Ollama        │
│  - Gemini CLI            → Google API                    │
│  - Codex CLI             → OpenAI API                    │
│  - Custom Agent SDK apps → anything                      │
│                                                          │
│  THIS IS WHERE THE LLM LIVES. Paperloom doesn't know     │
│  which one; paperloom doesn't care.                      │
└─────────────────────────┬────────────────────────────────┘
                          │  MCP protocol over stdio
                          │  (identical regardless of host or model)
                          ▼
┌──────────────────────────────────────────────────────────┐
│  PAPERLOOM MCP SERVER                                    │
│  10 tools, pure file operations, no LLM code path.       │
└──────────────────────────────────────────────────────────┘
```

**Consequence:** paperloom's code is identical whether the user runs Claude Sonnet, Gemini Pro, GPT-5, or Qwen3-14B on Ollama. There is no `--model` flag on `paperloom mcp`. There is no `ANTHROPIC_API_KEY` or `OLLAMA_HOST` in paperloom's config. The host agent handles all of that.

### For users who want offline / local models

Recommend one of these agent products in the docs (in `docs/quickstart-local.md`). Do not bundle any of them; do not depend on any of them; just tell users which one to install:

| Host agent | Local model support | Setup difficulty | Notes |
|---|---|---|---|
| **Continue.dev** | Excellent, first-class Ollama | Easy | VSCode/JetBrains extension. Best local-first UX. |
| **Cline** | Excellent, native Ollama config | Easy | VSCode extension. Per-tool confirmation dialogs. |
| **Aider** | Good; `--model ollama/qwen3:14b` | Easy | CLI, git-aware. |
| **OpenCode** | Good, model-agnostic | Medium | Newer, actively developed. |
| **Custom app** | Whatever you build | Hard | Claude Agent SDK or MCP Python SDK. |

**Do not recommend:** running LiteLLM in front of anything (security), or building your own agent (not paperloom's job).

### Model quality tiers and what to expect

This is the honest guidance to put in the docs. The three-question test in `tests/qualitative/three_question_eval.md` is the reference for what "works well" looks like.

| Model class | Examples | Expected quality against three-question test |
|---|---|---|
| **Frontier** | Claude Sonnet 4.5+, GPT-5, Gemini 2.5 Pro | Excellent — this is the reference bar |
| **Strong local** | Qwen3-32B, Llama 3.3-70B (on capable hardware) | Good — noticeable quality gap but usable |
| **Medium local** | Qwen3-14B, Llama 3.1-8B | Acceptable for factual retrieval; weaker at synthesis; use `mode: local` schema |
| **Small local** | Llama 3.2-3B, Qwen3-4B | Retrieval only; do not expect synthesis quality. Use as a fallback. |

Do not promise more than this. Do not hide the tier gap in the README.

### The one accommodation paperloom makes for small models

Add exactly one MCP tool (Section 9 addition below) that returns an explicit step-by-step workflow recipe. Small models that would otherwise lose the thread across a multi-step operation call this tool as their first move and follow the recipe verbatim. Frontier models ignore it because CLAUDE.md is already sufficient guidance.

This is the *only* concession paperloom makes to model capability. Everything else stays in the schema.

---

## Section 8 addition: mode-aware CLAUDE.md

Add these subsections to `templates/scientific-paper-vault/CLAUDE.md` right after the "Domain focus" section.

````markdown
## Operating mode (EDIT THIS ONCE)

Set one of the following based on what host agent you use with this vault:

- `mode: capable` — you use Claude Code with Sonnet-tier or better, Gemini
  CLI with Gemini 2.5 Pro, or GPT-5-tier via Codex/similar. The agent is
  expected to follow this schema in full, use judgment about when to
  synthesize, walk the graph 2 hops deep, and proactively offer to file
  answers as synthesis pages.

- `mode: local` — you use Continue.dev / Cline / Aider pointed at a local
  Ollama model (Qwen3-14B, Llama 3-8B, or similar). The agent gets
  step-by-step recipes for every operation, does not attempt multi-hop
  reasoning, asks for confirmation before every write, and reads fewer
  pages per query to fit smaller context windows.

**Current mode: capable**    ← edit to `local` if using local models

The rest of this file has sections marked "[all modes]", "[capable only]",
and "[local only]". Follow the sections that match your mode.
````

Then, throughout the CLAUDE.md, tag each behavioral rule with its applicable mode. Example rewrite of the `/ask` workflow:

````markdown
### /ask — answer a question from the wiki [all modes]

**[capable mode] Workflow:**
1. Call `search` for candidates.
2. Read top pages via `read_page`. Follow [[wikilinks]] up to 2 hops.
3. If a claim needs an exact number, read the underlying raw file.
4. Answer with citations. Offer to file as a synthesis page.

**[local mode] Workflow:**
1. Call `describe_workflow(operation="ask")` first if you're unsure of the steps.
2. Call `search` with a 2-3 word query. Get top 5 hits only.
3. Read the single most relevant page. Do not follow wikilinks unless
   the user explicitly asks a follow-up.
4. Answer using only what you read. Cite the one page you consulted.
5. Ask the user: "Should I also read [[X]] and [[Y]] to expand this?"
   Wait for confirmation before reading more.
6. Do not offer to file synthesis pages unless the user asks.
````

The pattern is: every workflow section has both variants, clearly labeled, and the agent follows the one matching its mode.

**Why this beats two separate files:**
- One source of truth. Schema changes propagate to both modes automatically.
- The user sees both variants and can switch modes any time by editing one line.
- Diffs are readable — a change to workflow shows up in both variants side-by-side.
- Small models don't get confused by irrelevant capable-mode instructions because the section header tells them to skip.

---

## Section 9 tool addition: 10 tools, not 9

Add this tool to Section 9's list. It's the tenth and final tool. Do not add more.

**10. `describe_workflow(operation: str) -> str`**

Return an explicit step-by-step recipe for a paperloom workflow. Used primarily by small local models that need workflow guidance beyond what CLAUDE.md provides.

```python
@mcp.tool
def describe_workflow(operation: str) -> str:
    """Return a step-by-step recipe for a paperloom workflow.

    Args:
        operation: one of "contribute", "ask", "lint", "rebuild_context",
                   "ingest", or "list_all".

    Returns:
        Plain text recipe with numbered steps, one per line, referencing
        the specific paperloom tools to call at each step. Frontier models
        typically don't need this; small local models should call this
        first before executing an operation for the first time.
    """
    root = find_vault_root()
    workflows_dir = Path(__file__).parent / "workflows"
    if operation == "list_all":
        return "\n".join(sorted(f.stem for f in workflows_dir.glob("*.md")))
    recipe_file = workflows_dir / f"{operation}.md"
    if not recipe_file.exists():
        return f"No recipe for '{operation}'. Available: " + ", ".join(
            sorted(f.stem for f in workflows_dir.glob("*.md"))
        )
    return recipe_file.read_text()
```

**Ship `src/paperloom/workflows/` with these files:**

- `contribute.md` — 8-step Karpathy ingest, one step per line, tool calls named.
- `ask.md` — the local-mode variant from the CLAUDE.md addition.
- `lint.md` — walk `sources/research/`, categorize findings, don't auto-fix.
- `rebuild_context.md` — snapshot old, read all, write new.
- `ingest.md` — usually the user runs this via CLI, but included for completeness.

Example `workflows/ask.md`:

```
Step 1: Understand the question. Identify 2-3 keywords.
Step 2: Call search(query=<keywords>, top_k=5).
Step 3: Read the top result via read_page(path=<top_hit>).
Step 4: If the top result answers the question, go to step 6.
Step 5: If not, read the second result. Stop after 3 pages max.
Step 6: Compose the answer using only what you read.
Step 7: Every claim in your answer must cite the page you got it from
        as [[wikilink]] or [[raw:...]].
Step 8: If your answer draws on multiple pages, ask the user if they
        want you to file it as a synthesis page.
```

These files are the workflow's source of truth. When a workflow changes, update its file and CLAUDE.md points at it.

---

## Rationale: why this is the right architecture

Three principles hold this design together. Any deviation should be checked against them:

**1. Paperloom's value is its schema and its file operations, not its intelligence.** The intelligence lives in the host agent. Adding LLM calls inside paperloom would make the same product MindBase already is, complete with the API-key requirement you specifically rejected.

**2. Model capability should affect the schema, not the code.** The tool interface is invariant. Only the CLAUDE.md instructions change per mode. This keeps the code testable (one code path) while letting the user experience adapt to model capability (via schema).

**3. Small-model support is best-effort, not core.** Frontier models are the primary target because they produce the demo-worthy answers that drive adoption. Small-model support is a graceful degradation path for users who need offline or free operation. Do not compromise the frontier experience to make small models work better.

If you find yourself adding a second CLAUDE.md, a `run_llm` tool, an OpenRouter integration, or a "smart" server-side pipeline, stop. Re-read this section. Choose the version that doesn't do those things.

---

## What to remove from the original spec

Delete these entirely from `paperloom.md`:

1. **Section 11's `ollama_synth` plugin.** No plugin that calls an LLM ships with paperloom. If a user builds one as a vault-local plugin for a specific personal use case, that's their choice; paperloom doesn't distribute it.

2. **The `[ollama]` optional-dependency extra in Section 4's pyproject.toml.** Delete it. `pip install paperloom[ollama]` should not exist. Users who want Ollama install it via their host agent (Continue.dev, Cline, etc.), not via paperloom.

3. **Any mention of `synth`, `synth_available`, or LLM-backend selection in the config schema.** The `.paperloom/config.yaml` has no LLM-related fields. It has: vault name, template used at init, search backend preference, plugin allowlist. That's it.

4. **The "Auto-selection helper" for Ollama models in the old Section 11.** Gone. If the user wants to pick a model, they configure their host agent, not paperloom.

Delete these lines and this architecture becomes provably clean: paperloom does file operations, agents do reasoning, models do inference, and no layer knows about layers above it.
