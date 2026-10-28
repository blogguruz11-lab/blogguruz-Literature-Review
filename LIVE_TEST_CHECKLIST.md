# Five-paper live test

Version 2 is not reliable until this is done. Use papers you know well, and cover variety:

1. A clean single-column paper with a clear abstract.
2. A two-column journal article.
3. A paper with heavy tables.
4. A long paper (30+ pages) or a thesis chapter.
5. A paper that states no limitations, or has a vague objective.

## Before you start
- [ ] `pip install -r requirements.txt`, API key set, `streamlit run app.py` starts without errors.
- [ ] Note the model name shown on the results.

## For each paper, record the results
- [ ] Text check: open "Check the text extracted from the PDF". Is the reading order and wording sensible?
- [ ] Consent: Extract stays disabled until the box is ticked. The size estimate appears first.
- [ ] Count excerpt labels: text verified / wrong page / not found / too short.
- [ ] **Read every excerpt** and mark each statement: supported / partly supported / not supported.
- [ ] Objective and methodology: compare with the abstract and methods section.
- [ ] Findings: are they this paper's own results, not results of cited work?
- [ ] Missing fields: if "Not stated in the paper" appears, is it truly absent? If a field is filled,
      was it really stated?
- [ ] Reference list: was it removed (see the note under the model name)? Was any finding taken from it?
- [ ] Any "cut off", "could not be read" or API error messages? Note how often.
- [ ] Estimated tokens vs. actual usage on the Anthropic console.

## Whole-app checks
- [ ] Re-run with the same file and settings: no second API call.
- [ ] Change the research question: a new extraction is offered.
- [ ] Upload a file over the size limit: skipped with an explanation, nothing sent.
- [ ] Press **Delete all session data**: results disappear; consent tick resets.
- [ ] Privacy check: search disk, logs and terminal output for a unique phrase from a test PDF.
- [ ] Confirm the API key appears nowhere in the interface, logs or repository.

## Results table (copy per paper)

| Paper | Verified | Wrong page | Not found | Too short | Supported | Partly | Not supported | Notes |
|---|---|---|---|---|---|---|---|---|

## Suggested bar (adjust to your own standards)
- Nearly all excerpts text-verified, and every wrong-page or not-found item clearly flagged.
- Few or no "not supported" statements among those that are text-verified.
- No findings taken from cited works.
- No failures that go unnoticed by the user.
If the results fall short, change the prompt or model, bump `EXTRACTION_VERSION` in `core/config.py`,
and repeat the test.
