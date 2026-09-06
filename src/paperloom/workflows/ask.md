Step 1: Understand the question. Identify 2-3 keywords. Keep the search
        query SHORT and literal — 1-3 words that would appear verbatim in
        the text (e.g. "JEPA mask", not "JEPA masking modality adaptation").
        Search is exact substring matching, not natural-language
        understanding: a longer, more natural-sounding query is LESS
        likely to match, not more. If a query returns nothing, remove
        words rather than adding them before trying again.
Step 2: Call search(query=<keywords>, top_k=5).
Step 3: Read the top result via read_page(path=<top_hit>).
Step 4: If the top result answers the question, go to step 6.
Step 5: If not, read the second result. Stop after 3 pages max.
Step 6: Compose the answer using only what you read.
Step 7: Every claim in your answer must cite the page you got it from —
        as [[wikilink]] or [[raw:...]]. Do this mechanically: when you
        use a fact or quote that sat next to a [[raw:...]] tag in the
        page you read, copy that exact tag into your own answer right
        next to the same fact. Do not paraphrase a citation away — if the
        source page cited [[raw:2409.19407#Abstract]] for a claim, your
        answer repeats [[raw:2409.19407#Abstract]] for that same claim,
        word-for-word, not a summary of it. An answer with zero
        [[raw:...]] or [[wikilink]] tags in it is wrong even if every
        fact in it is correct.
Step 8: If your answer draws on multiple pages, ask the user if they
        want you to file it as a synthesis page.

Do not follow [[wikilinks]] to additional pages on your own. If the answer
seems incomplete, tell the user which linked pages you did not read and
ask whether to read them, then wait for confirmation.
