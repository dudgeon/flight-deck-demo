# Intent: tell customers when a held payment will be released

**Depth:** 3 of 5, Shaped · **Framework:** Intent framework (notional) · **Next level asks for:** evidence on the riskiest assumption, and answers from the teams it depends on

## Customer
Sole traders who take card payments in person, in their first month, at the moment their first or second unusually large payment is held. Not served on purpose: established businesses, whose holds are rare and who have a relationship manager.

## Problem
"My first big payment gets held and nobody can tell me when I will get it." They pay suppliers from personal money, phone support repeatedly, and some move back to their previous bank. It has not been solved because the release date exists only inside the risk rules and was never treated as something a customer should see.

## Outcome
A customer whose payment is held knows the same day when the money will arrive. The measure: the share of accounts with a held payment in their first 30 days that are inactive by day 60. Today it is 41%, against 17% for new business accounts overall. It should fall.

## Scope
**In:** a release date on the held payment in the app, and the same date in the support console.
**Deliberately out:** changing which payments are held; releasing payments sooner; explaining why a payment was held.

## Risks
1. A visible date could help someone time a fraud. Risk Review: acceptable if the date is shown only after the hold is placed and never the rule behind it.
2. A date that then slips is worse than no date. Open, with Mara Okafor.
3. The rules may not be able to produce a date for every kind of hold. Open, with Risk Review.

## Dependencies
Risk rules (Risk Review), the card authorization platform (Cards Platform), the support console.

## Not yet covered
Cost is not required until the next level.

## What it would take to reach "Tested"
- Put the slipping-date question to design and choose a behaviour.
- Get an answer from Risk Review on whether every hold can carry a date.
- Decide what level of the measure counts as success.
