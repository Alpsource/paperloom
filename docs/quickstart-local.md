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

## Setting up Cline specifically

Cline's MCP config isn't project-scoped like Claude Code's `.mcp.json` —
it's one **global** file, shared across every VS Code workspace you open:

- Windows: `%APPDATA%\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`
- macOS: `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- Linux: `~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`

(Or open it from inside VS Code: the MCP Servers icon in the Cline panel →
"Configure MCP Servers".)

Add a `paperloom` entry — **`cwd` matters here, don't omit it:**

```json
{
  "mcpServers": {
    "paperloom": {
      "command": "paperloom",
      "args": ["mcp"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

**Why `cwd` is required, not optional:** `paperloom mcp` finds your vault
by walking up from its own working directory looking for `.paperloom/`
(`find_vault_root()`). Because Cline's config is global rather than
per-project, it has historically spawned stdio MCP servers with the wrong
working directory by default (VS Code's own install directory, not your
open workspace) unless `cwd` is set explicitly — see
[cline/cline#2990](https://github.com/cline/cline/pull/2990) and
[cline/cline#9950](https://github.com/cline/cline/issues/9950). With
`"cwd": "${workspaceFolder}"`, Cline expands that to whichever folder you
currently have open — so this one global config entry correctly follows
you to any paperloom vault you open, no per-vault Cline reconfiguration
needed (unlike `.mcp.json`, which — being per-project already — has no
equivalent problem for Claude Code, Continue.dev, or Aider).

After adding the entry: restart VS Code (or reload the Cline extension),
open your vault folder as the workspace, and check Cline's MCP panel shows
`paperloom` **connected** before doing anything else. If it's not
connected, or tools error immediately, the `cwd` field is the first thing
to check.

**Managing Ollama's memory footprint.** Ollama unloads a model from
RAM/VRAM automatically after 5 minutes of inactivity by default. If you'd
rather not wait, unload it immediately after a session:

```bash
ollama stop qwen3.5:4b
```

`ollama ps` shows what's currently loaded if you want to check before
starting something else memory-hungry.

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
| **Strong local** | Qwen3.5-27B+ (on capable hardware) | Good — noticeable quality gap but usable |
| **Medium local** | Qwen3.5-9B, Llama 3.1-8B-class | Acceptable for factual retrieval; weaker at synthesis |
| **Small local** | Qwen3.5-4B, Llama 3.2-3B | Retrieval only — don't expect real synthesis quality |

(Model names age fast — treat these as "the current generation as of this
writing," not gospel. Check what's actually current before picking one;
see the note in `PROGRESS.md` about how we picked Qwen3.5 over the
similarly-named-but-unrelated Qwen3.8 flagship line.)

We're not going to promise more than this, and we're not going to hide the
gap. A small model on a 6GB card can absolutely search your vault and
answer "what does paper X say about Y" with a citation. Asking it to
synthesize a novel connection across five papers the way a frontier model
can is a different task, and it will show.
