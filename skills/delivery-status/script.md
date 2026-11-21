# Delivery status update

A scripted run with an invented plan: five milestones toward showing customers a release date on held payments. Press Next, or use the controls where the script waits for you.

**You:** It is Thursday. Update the status on release dates for held payments, steering is tomorrow.

**Aviator:** I have the plan from 12 February open. I am checking each open milestone with its owner rather than trusting last week's dates.
[task: Checking milestones · 0 of 4]

[show plan as "Delivery plan"]

[status M-2, M-3, M-4, M-5: working]

[call Mara Okafor: Is the release date in the app (M-2) still landing on 6 March?]

**Mara Okafor:** Yes. It is in review now and nothing is open on the design side.

[Mara Okafor leaves: M-2 holds at 6 March.]

[set M-2: status=on-track, basis="Mara, today: in review, nothing open on design."]
[set M-3: status=on-track, basis="Checked the support console build notes today."]
[task: Checking milestones · 2 of 4]

[call Cards Platform: Is the load test at twice peak (M-4) still on for 9 to 13 March?]

**Cards Platform:** No. The performance environment was taken on Tuesday for an urgent fix on another programme. Our next slot is 18 March, so the earliest we finish is the 22nd.

[Cards Platform leaves: M-4 moves from 13 March to 22 March.]

[set M-4: status=late, projected="22 Mar", slip="+9 days", confidence=3, change="The performance test environment was taken for an urgent fix. Next slot is 18 March.", basis="Cards Platform, today."]
[set DP-1: status=late, due="18 Mar", note="Lost on Tuesday. Next slot 18 March."]
[set M-5: status=late, projected="2 Apr", slip="+9 days", confidence=3, change="Follows the load test.", basis="Launch needs the load test, then five working days of staged rollout."]
[fact projected="2 Apr"]
[task: Projecting the date]

**Aviator:** One thing moved, and it is on the path to launch. The load test lost its environment, so launch goes from 24 March to 2 April unless we do something. Everything else holds. I looked for ways to get the time back and found three:
[task: Ways to recover · 3 found]

[widget milestone for M-4]
[hint: Choose one of the ways to recover on the card, or open M-4 in the canvas to compare them. Then Send your changes, and Send.]
[wait]

[apply edits]
[set M-4: status=at-risk, projected="17 Mar", slip="+4 days", confidence=3, change="Environment lost, then borrowed from Payments for 11 to 13 March.", selected_option="A-1"]
[set M-5: status=at-risk, projected="26 Mar", slip="+2 days", confidence=3, change="Follows the load test. Seven of nine days recovered."]
[set DP-1: status=at-risk, due="11 Mar", note="Borrowed from Payments. Confirmed by message, not yet booked."]
[fact projected="26 Mar"]

**Aviator:** With the Payments environment, launch is projected for 26 March: two days late instead of nine. I have marked it at risk rather than on track, because the booking is a message and not yet in the scheduling tool. Here is the update for steering.
[task: Writing the update]

[open document as "status-update.md"]

[widget summary]

**Aviator:** I will check the booking on Monday and tell you if it has not appeared.
[task: none]
