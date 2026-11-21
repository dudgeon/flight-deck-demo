# Explorer brief

Fill in before sending:

- PA: `<the full pa command>`
- DATASET: `<data/slug.json>`
- REQUIREMENT: `<id, e.g. R-07>`
- PLATFORM MAP: `<path(s) to read>`
- NOTE FROM THE USER (only on a second pass): `<their note or answer>`

---

You are exploring one requirement. Find what it depends on in the platform and
which existing capabilities could meet each dependency. Work only from the
platform map. Do not use the internet and do not invent capabilities.

1. Read the requirement: `PA get DATASET REQUIREMENT`. Read the platform map.
2. If this is a second pass, read what is there already:
   `PA get DATASET --where parent=REQUIREMENT`. Reuse those ids so you replace
   records instead of duplicating them.
3. Work out one to three dependencies. A dependency is something the
   requirement cannot ship without, stated as a need ("Know the remaining
   amount at approval time"), not as a product name.
4. For each dependency find one to three capabilities in the platform map that
   could meet it. Rate each for fit from 1 to 5 and note its gaps honestly.
5. Write them in one call. Leave out `id` on new records and `pa` assigns one.
   Add dependencies first, read back their ids, then add options with
   `parent` set to the dependency id.

```bash
PA add DATASET --json '[{"type":"dependency","parent":"REQUIREMENT","derived_from":["REQUIREMENT"],
  "title":"...","summary":"two or three sentences","effort":"S|M|L","confidence":4,
  "owner_team":"...","evidence":[{"source":"platform-map.md, section name","quote":"exact words"}]}]'
PA add DATASET --json '[{"type":"option","parent":"D-..","derived_from":["REQUIREMENT"],"title":"capability name",
  "summary":"what it does","fit":4,"effort":"S","maturity":"Live|Beta|Planned","owner_team":"...","gaps":"..."}]'
PA set DATASET D-.. selected_option=O-..      # the one you recommend
```

6. Finish with exactly one of:
   - `PA set DATASET REQUIREMENT explore_status=ready explore_note="one or two sentences: what you found" --no-stale`
   - If only the user can settle something (a trade-off, a missing fact):
     `PA set DATASET REQUIREMENT explore_status=needs-you explore_question="the question in one or two plain sentences" --no-stale`
     Still record what you found so far.

Rules: quote evidence exactly and say where it is. Shape of every record is in
`schemas/records.json` next to this skill. Never edit the dataset file
directly. Never set `reviewed` or `locked`. Reply with one line when done.
