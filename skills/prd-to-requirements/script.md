# PRD to requirements

A scripted run with invented data. Press Next, or use the controls in each view where the script waits for you.

[open document as "allowances-prd.md"]

**You:** Catalog the requirements in this PRD.

**Aviator:** Before I start, three quick choices.

[widget scope]
[wait for submit]

**Aviator:** Reading the document. I am pulling out one testable statement at a time.
[task: Cataloging · reading sections 3 to 7]

[show catalog empty as "Requirements catalog"]

[reveal C-1, R-01, R-02, R-03, R-04]
[task: Cataloging · 4 of 20]

[reveal C-2, R-05, R-06, R-07, R-08, R-09]
[task: Cataloging · 9 of 20]

[reveal C-3, R-10, R-11, R-12, R-13, C-4, R-14, R-15, R-16]
[task: Cataloging · 16 of 20]

[reveal C-5, R-17, R-18, R-19, R-20]
[task: Catalog ready for review]

**Aviator:** 20 requirements in 5 groups. I marked 5 as reviewed where the document is unambiguous, and 3 need your answer. The summary is below.

[widget summary]

**You:** On R-03: it applies right away. The FAQ is out of date.

[set R-03: status=ready, question=null, confidence=5]

**Aviator:** Updated R-03 and cleared the question. Open any row to read it in full, change a priority in place, or approve it.
[hint: Try it: open a row, approve a few, then press Send to agent.]
[wait]

[apply edits]

**Aviator:** Saved your edits. When you are happy with the catalog, Map dependencies takes each reviewed requirement to the platform.
