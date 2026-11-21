# Decision review

A scripted run with invented data. The decisions come from an earlier review and dependency map. Press Next, or use the controls where the script waits for you.

[start: hide decision, follow-up]

**You:** Before we take this to the steering group, walk me through what is still open on Allowances.

**Aviator:** I went through the review findings, the dependency map and our conversation. Seven things need a decision from you. I am preparing each one with options and a recommendation.
[task: Gathering what is open]

[show queue empty as "Decisions"]

[reveal D-6, FU-1]

[reveal D-1, D-2, D-3]
[task: Preparing · 4 of 7]

[reveal D-4, D-5, D-7]
[task: Ready for you · 4 open]

**Aviator:** One is already settled from earlier, one is waiting on a number you asked for, and Risk Review is still preparing one. Four are ready. The first is the one Risk will not sign off without:

[widget card for D-1]
[hint: Pick an option on the card, or open any row in the canvas. Your picks collect: press Send your changes when you have a few, then Send.]
[wait]

[apply edits]
[status D-1: reviewed]

**Aviator:** Recorded. That one came from Risk Review, so I am letting them know.

[call Risk Review: The product manager has decided D-1, whose consent an under-18 allowance needs. Does this clear your finding?]

**Risk Review:** It does, provided the consent record is kept seven years. I have also finished preparing D-7: Fraud Strategy should own the control, and they have agreed in principle.

[set D-7: status=ready, context="Fraud models retrain on decline history, so a new decline reason leaks in unless someone excludes it on purpose. Fraud Strategy has agreed in principle to own it.", recommended="Fraud Strategy", reason="They own the model inputs. Platform can only supply the reason code."]
[Risk Review leaves: D-1 clears the consent finding. D-7 is ready, with Fraud Strategy recommended.]

**Aviator:** Five are open now. You can take them in any order, ask whoever raised one, or take my recommendations for the rest.
[task: Your decisions · 2 of 7 made]
[hint: Try it: open D-2 and pick, or press "I need more first" on one. Then Send.]
[wait]

[apply edits]

**Aviator:** Saved. Here is where things stand.

[widget summary]

**Aviator:** When you are done I will write the decision log, with who raised each question, what you picked and why, and the follow-ups each decision causes.
[task: none]
