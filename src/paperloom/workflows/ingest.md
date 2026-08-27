This is usually run by the user directly from the command line
(`paperloom ingest <folder>`), not by the agent. It only touches
sources/raw/ — never sources/research/ — and never needs an LLM: it's a
mechanical PDF-to-markdown parse via MinerU.

If the agent does need to ingest a single PDF mid-session (e.g. the user
pastes a path to a PDF that hasn't been ingested yet):

Step 1: Call ingest_pdf(pdf_path=<the path the user gave you>).
Step 2: Report the result to the user: the paper's id, how many pages
        were parsed, and the raw_path it landed at
        (sources/raw/<id>/paper.md).
Step 3: Ask whether they want to /contribute it into the wiki now, or
        just leave it parsed in sources/raw/ for later. Do not
        automatically continue into /contribute without asking.
