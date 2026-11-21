# Review a document with others

A scripted run with invented data. Other participants are scripted too. Press Next, or use the controls where the script waits for you.

[start: hide finding]

[open document as "allowances-prd.md"]

**You:** I have finished the Allowances PRD. Help me review it.

**Aviator:** I read it end to end. It is in good shape. I left two comments in the document, and one of them needs you.
[task: Reviewing · first read]

[comment by Aviator on "It applies from the next cycle.": This contradicts 3.3, which says a changed amount applies right away. Which one is right?]

[comment by Aviator on "no more than a minute old": Worth stating what the card user sees when the amount cannot be refreshed.]

**You:** 3.3 is right. The FAQ is out of date.

[resolve comment on "It applies from the next cycle."]

[show findings as "Review findings"]
[reveal F-08]

**Aviator:** Resolved, and I started a findings list in the canvas. Before this goes wider, two people usually have views on a card feature. Who should I call in?
[task: none]

[widget who]
[hint: Pick who to call in, press Call them in, then Send.]
[wait for submit]

[call Risk Review: Review the Allowances PRD for regulatory, conduct and fraud risk. Add findings to the shared list.]
[task: Risk Review is reading]

**Risk Review:** Reading sections 4 and 7 against the disclosure, minors and retention policies. I will comment in the document and list findings as I go.

[comment by Risk Review on "These are counted against the allowance but not blocked.": High. A parent will read an allowance as a cap. This sentence is where that stops being true. See F-01.]

[comment by Risk Review on "needs recorded consent": Whose consent? The cardholder's and the minor's are different records. See F-03.]

[tab "Review findings"]
[reveal F-01, F-02]

[reveal F-03, F-04]

**Risk Review:** Four findings, one High. Nothing blocks sign-off if F-01 becomes a launch gate. I need one answer from you to close F-03:

[widget question from Risk Review]
[hint: Answer Risk Review's question, then Send.]
[wait for submit]

[set F-03: status=ready, question=null, answer="The cardholder, as parent or guardian"]

**Risk Review:** Recorded on F-03. No blockers from Risk. I will look again when the 7.3 wording exists.
[task: none]
[Risk Review leaves: 4 findings, 1 High. No blockers once F-01 is a launch gate.]

**Aviator:** Risk is done. Mara next, on the card user's experience. An agent is standing in for her today, working from her notes.

[call Mara Okafor: Look at section 5 of the Allowances PRD from the card user's side. Add findings to the shared list.]
[task: Mara (stand-in) is reading]

**Mara Okafor:** Hi! Section 5 is close. My worry is the decline moment. A teenager at a till will not wait ten seconds, and five of the eight families I spoke to in spring said as much.

[comment by Mara Okafor on "within 10 seconds": Too slow at a till. Three seconds, and tell them what to do next. See F-05.]

[tab "Review findings"]
[reveal F-05, F-06, F-07]

**Mara Okafor:** Three from me. One question back: if I can only keep one of the two alerts in 5.4 and 6.3, which would you keep?
[hint: Type a reply to Mara and press Send.]
[wait]

**Mara Okafor:** That works. I would cut 5.4 from launch then, and I have noted it on F-07.
[task: none]
[Mara Okafor leaves: 3 findings, 1 High. Suggests cutting 5.4 from launch.]

**Aviator:** Both reviews are in. Eight findings from three of us, two High. Everything is in one list, with who raised what.

[widget summary]

**Aviator:** Open any finding to read it, accept it or push back. Pushing back goes to whoever raised it.
[hint: Try it in the canvas: open F-05 and accept it, or push back on F-06. Then Send.]
[wait]

[apply edits]

**Aviator:** Done. When you are ready, I can apply the accepted findings to the PRD as suggested edits.
