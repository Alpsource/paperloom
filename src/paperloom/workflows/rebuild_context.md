Step 1: Read the current context.md via read_page(path="context.md").
Step 2: Snapshot it: create_note(path=".paperloom/cache/snapshots/context-<today's
        date, YYYY-MM-DD>.md", title="context.md snapshot", content=<the
        text you just read>). This is your rollback copy — do this before
        changing anything.
Step 3: Call list_pages(subdir="sources/research") and read_page on each
        one. Also read any recent files under sources/contributors/*/*.md
        (the last few days' entries).
Step 4: Write a new context.md: 500-2000 words, plain prose, no citations
        required (this is a landing page, not a reference page) — a
        synthesized summary of what the vault currently contains and what
        it's actively about.
Step 5: Overwrite context.md with the new version. None of paperloom's
        tools do a full-file overwrite (append_to_page only appends,
        create_note refuses if the file exists) — use your own host
        agent's native file-write capability for this one step, not a
        paperloom tool. Then call log_entry(kind="REBUILD-CONTEXT",
        text="regenerated context.md") to record that it happened.
