# Intent shaping

A scripted run with an invented idea and a notional framework. Press Next, or use the controls where the script waits for you.

[start: hide area, gap]

**You:** I keep coming back to this: we should just show people the release date when a payment is held. Help me shape it.

**Aviator:** I will shape it against the intent framework in your workspace. It has five depths, from a spark to something a team could commit to, and seven areas an idea has to cover. First, how far do you want to take this today?

[widget target]
[wait for submit]

**Aviator:** Shaped it is. Here is the idea as it stands, laid against the framework.
[task: Capturing the idea]

[show map empty as "Intent map"]

[reveal AR-1, AR-2, AR-3, AR-4, AR-5, AR-6, AR-7]

**Aviator:** It is not yet at the first level, and the reason is worth seeing. You have named a customer, loosely. But the idea is a solution: show a date. The framework asks for a problem first. What goes wrong for the customer today that a release date would fix?
[task: Framing · depth 0 of 5]

[widget area for AR-2]

**You:** It is in the discovery we did on new business accounts. Use the problem brief.

**Aviator:** Reading it.

[set AR-2: depth=4, depth_name="Tested", status=reviewed, by=aviator, question=null, statement="\"My first big payment gets held and nobody can tell me when I will get it.\" They pay suppliers from personal money, phone support repeatedly, and some go back to their old bank.", next="A size, with its source."]
[set AR-1: depth=4, depth_name="Tested", status=reviewed, by=aviator, question=null, statement="Sole traders who take card payments in person, in their first month, when their first or second unusually large payment is held. Not served on purpose: established businesses.", next="We know how many there are and how to reach them."]
[set AR-3: status=needs-you, question="If this worked, what would be different for that sole trader, and what number would move?"]
[fact depth="1 · Spark"]
[task: Framing · depth 1 of 5]

**Aviator:** That moved two areas a long way, because the discovery already holds evidence for and against. The idea is now held back by Outcome, which is empty. If this worked, what would be different for that sole trader, and what number would move?

**You:** They would know the same day when the money lands. And fewer of them should go quiet. The 41% number from support.

[set AR-3: depth=3, depth_name="Shaped", status=reviewed, by=you, question=null, statement="A customer whose payment is held knows the same day when the money will arrive. Measure: the share of accounts with a held payment in their first 30 days that are inactive by day 60. It should fall from 41%.", next="A baseline for that measure, and a level that would count as success."]
[reveal G-4]
[set AR-4: status=needs-you, question="What is in, and what are two things you are deliberately not doing?"]
[set AR-5: status=working]
[set AR-6: status=working]
[fact depth="2 · Framed"]
[task: Shaping · depth 2 of 5]

**Aviator:** Framed. To be shaped it needs boundaries, risks and dependencies. Scope is yours: what is in, and what are two things you are deliberately not doing? While you think, I am asking Risk Review and Cards Platform about the other two, since they are the ones who would know.

[call Risk Review: We want to show customers the release date of a held payment. What are the things most likely to sink that?]

**Risk Review:** Two from my side. A visible date could help someone time a fraud; that is acceptable if the date appears only after the hold is placed and the rule behind it is never shown. And I cannot yet promise the rules produce a date for every kind of hold.

[Risk Review leaves: Timing risk is acceptable with two conditions. Whether every hold can carry a date is open.]

[call Cards Platform: Which of your systems would showing a release date on a held payment depend on?]

**Cards Platform:** The authorization platform already carries the hold. It would need one new field passed through to the app and the support console.

[Cards Platform leaves: Needs one new field through the authorization platform.]

[set AR-5: depth=3, depth_name="Shaped", status=reviewed, by=risk-review, statement="1. A visible date could help time a fraud (Risk Review: acceptable with conditions). 2. A date that then slips is worse than no date. 3. The rules may not produce a date for every hold.", next="The riskiest one has been put to whoever would know."]
[reveal G-1, G-2]
[set AR-6: depth=3, depth_name="Shaped", status=reviewed, by=cards-platform, statement="Risk rules (Risk Review), the card authorization platform (Cards Platform), the support console.", next="Each has been asked, and has answered."]
[reveal G-3]

**Aviator:** Risks and dependencies are at the target, with three gaps noted for the next level. Scope is the last one. You can answer here or write it straight into the area in the canvas.
[hint: Try it: open Scope in the canvas, write what is in and out, then Send your changes and Send. Or just press Next.]
[wait]

[apply edits]
[set AR-4: depth=3, depth_name="Shaped", status=reviewed, by=you, question=null, statement="In: a release date on the held payment in the app, and the same date in the support console. Deliberately out: changing which payments are held; releasing payments sooner; explaining why a payment was held.", next="The smallest version that would still produce the outcome."]
[fact depth="3 · Shaped"]
[task: Shaped · depth 3 of 5]

**Aviator:** Shaped. Every required area is at depth 3 or beyond, and Cost is not required until the next level. Here is the intent brief at this depth, and what it would take to go one further.

[open document as "intent-brief.md"]

[widget summary]
[task: none]
