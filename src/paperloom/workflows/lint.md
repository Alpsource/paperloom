Step 1: Call list_pages(subdir="sources/research", pattern="*.md") to get
        every research page.
Step 2: For each page, call read_page(path=...) and check:
        a. Does every [[wikilink]] in the body point at a page that
           actually exists? (Call search or list_pages to check — do not
           guess.) If not, that's a dangling link.
        b. Does every non-trivial paragraph carry a [[raw:...]] citation,
           or one of {{common-knowledge}}, {{synthesis}},
           {{unclear-in-source}}? If not, that's an unbacked claim.
Step 3: For each page, note whether any OTHER page links to it. A page
        nothing else links to is an orphan.
Step 4: List every method/dataset name mentioned inside paper pages that
        does not have its own page under sources/research/methods/ or
        sources/research/datasets/ — that's a missing page.
Step 5: Present all findings to the user as a short report, grouped by
        category (orphans, dangling links, unbacked claims, missing
        pages). Do not fix anything yourself — wait for the user to say
        what to do about each finding.
