Step 1: Determine the input type.
        - A short pasted thought (not from sources/raw/): go to step 8.
        - A reference to sources/raw/<id>/ (an already-ingested paper):
          continue to step 2.
Step 2: Call read_page(path="sources/raw/<id>/paper.md") and
        read_page(path="sources/raw/<id>/meta.json").
Step 3: Identify 2-4 candidate names for this paper's method(s) and any
        datasets it uses (from the title, abstract, and section headers
        you just read).
Step 4: For each candidate name, call search(query=<name>,
        path_prefix="sources/research/") to check whether a page for it
        already exists. Do not create a duplicate page for something that
        already exists — use append_to_page on the existing page instead.
Step 5: Decide what to create and what to update. Write this down as a
        short plan: one line per new page (with its type: paper / method /
        dataset / concept), one line per existing page to update (with
        what you'll add).
Step 6: Show the plan to the user. Wait for their approval before writing
        anything, unless they already said "batch mode" for this session.
Step 7: On approval, write every planned file:
        - New pages: create_note(path=..., title=..., content=..., ...).
        - Updates: append_to_page(path=..., content=..., section=...).
        Use [[wikilinks]] in the body text wherever you reference another
        page. Every non-trivial claim needs a [[raw:<id>#section]] citation,
        or one of {{common-knowledge}}, {{synthesis: ...}},
        {{unclear-in-source}} — never write a claim with none of these.
Step 8: Call log_entry(kind="CONTRIBUTE", text=<one-line summary of what
        was added>). If this was a short pasted thought (not a paper), the
        log entry is the only output — nothing else to write.
