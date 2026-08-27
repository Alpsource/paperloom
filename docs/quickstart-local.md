# Local / offline models

Paperloom never calls an LLM itself — not for synthesis, not for
classification, not for embedding, and that's true whether you're running
Claude Sonnet or a 3B model on your own GPU. The MCP server (`paperloom
mcp`) is 10 file-operation tools, nothing else. The LLM always lives in
your **host agent** — the thing on the other end of the MCP connection —
and paperloom's code is identical no matter which one you pick.

```
┌──────────────────────────────────────────────────────────┐
│  HOST AGENT (any MCP-compatible client)                  │
│  - Claude Code           → Anthropic API                 │
│  - Continue.dev          → any model incl. Ollama        │
│  - Cline (VSCode)        → any model incl. Ollama        │
│  - Aider                 → any model incl. Ollama        │
│  - Gemini CLI            → Google API                    │
│  - Codex CLI              → OpenAI API                    │
│  - Custom Agent SDK apps → anything                      │
│                                                          │
│  THIS IS WHERE THE LLM LIVES. Paperloom doesn't know      │
│  which one; paperloom doesn't care.                       │
└─────────────────────────┬────────────────────────────────┘
                          │  MCP protocol over stdio
                          │  (identical regardless of host or model)
                          ▼
┌──────────────────────────────────────────────────────────┐
│  PAPERLOOM MCP SERVER                                     │
│  10 tools, pure file operations, no LLM code path.         │
└──────────────────────────────────────────────────────────┘
```

There's no `--model` flag on `paperloom mcp`. There's no `ANTHROPIC_API_KEY`
or `OLLAMA_HOST` in paperloom's own config. If you want a fully offline,
free setup, you install a host agent that talks to a local model and point
it at the exact same `.mcp.json` this project always uses — nothing about
paperloom itself changes.

## Which host agent to use with a local model

Recommended, roughly by ease of setup:

| Host agent | Local model support | Setup difficulty | Notes |
|---|---|---|---|
| **Continue.dev** | Excellent, first-class Ollama | Easy | VSCode/JetBrains extension. Best local-first UX. |
| **Cline** | Excellent, native Ollama config | Easy | VSCode extension. Per-tool confirmation dialogs. |
| **Aider** | Good; `--model ollama/qwen3:14b` | Easy | CLI, git-aware. |
| **OpenCode** | Good, model-agnostic | Medium | Newer, actively developed. |
| **Custom app** | Whatever you build | Hard | Claude Agent SDK or MCP Python SDK. |

**Don't:** run a LiteLLM proxy in front of anything (a real security
surface for no real benefit here), or build your own agent from scratch —
that's not what paperloom is for; use one of the above instead.

## Switching your vault to local mode

Open `CLAUDE.md` at your vault root and change one line:

```diff
- **Current mode: capable**    ← edit to `local` if using local models
+ **Current mode: local**    ← edit to `local` if using local models
```

That's the entire switch. Every workflow section in `CLAUDE.md`
(`/contribute`, `/ask`, `/lint`, `/rebuild-context`) has both a
`[capable mode]` and a `[local mode]` variant written side by side — local
mode does fewer hops, reads fewer pages, and asks for confirmation before
every write, which matters more for a smaller context window and a model
less able to self-correct mid-task. If your local model still seems to
lose the thread on a multi-step operation, it can call the
`describe_workflow(operation=...)` tool for an explicit numbered recipe —
this is the one accommodation paperloom's schema makes for weaker models,
and it's there specifically so you don't need a second CLAUDE.md.

## What to actually expect, honestly

This is the guidance we'd rather you read here than discover the hard way.
The reference for "what good output looks like" is
[`tests/qualitative/three_question_eval.md`](https://github.com/Alpsource/paperloom/blob/main/tests/qualitative/three_question_eval.md)
in the repo — three real questions, with a real frontier-tier answer shown,
so you have something concrete to compare your own results against.

| Model class | Examples | Expected quality |
|---|---|---|
| **Frontier** | Claude Sonnet 4.5+, GPT-5, Gemini 2.5 Pro | Excellent — this is the reference bar |
| **Strong local** | Qwen3-32B, Llama 3.3-70B (on capable hardware) | Good — noticeable quality gap but usable |
| **Medium local** | Qwen3-14B, Llama 3.1-8B | Acceptable for factual retrieval; weaker at synthesis |
| **Small local** | Llama 3.2-3B, Qwen3-4B | Retrieval only — don't expect real synthesis quality |

We're not going to promise more than this, and we're not going to hide the
gap. A small model on a 6GB card can absolutely search your vault and
answer "what does paper X say about Y" with a citation. Asking it to
synthesize a novel connection across five papers the way a frontier model
can is a different task, and it will show.
