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

Do not follow [[wikilinks]] to additional pages on your own. If the answer
seems incomplete, tell the user which linked pages you did not read and
ask whether to read them, then wait for confirmation.
