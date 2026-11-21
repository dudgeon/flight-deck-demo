# Allowances: product requirements

Visigoth Bank · Cards · Draft 3 · invented for demos

## 1. Problem

Cardholders who add a family member to their credit card have no way to cap what that person spends. They find out on the statement. Calls about "a charge I didn't expect from my teenager" are the third most common reason families remove an authorized user.

## 2. Who it is for

Parents of teenagers first. Later, couples and carers.

## 3. Setting an allowance

3.1 A cardholder can give each authorized card user a monthly allowance. Each card user has their own amount, anywhere from $10 up to the card's credit limit. A card user with no allowance is not affected.

3.2 The allowance resets on a day of the month the cardholder picks, at midnight in the account's time zone.

3.3 If the cardholder changes the amount, the new amount applies right away, and what has already been spent this cycle still counts.

3.4 There is one allowance per card user. Budgets by merchant type are out of scope for launch.

## 4. Enforcing it

4.1 A purchase that is approved in real time is declined if it would take the card user past the allowance. A purchase for exactly what is left goes through.

4.2 Some charges post without live approval, such as transit taps and some in-flight purchases. These are counted against the allowance but not blocked.

4.3 Refunds go back into the allowance for the cycle they arrive in.

4.4 A decline caused by the allowance must be distinguishable from every other decline, so the app and our agents can explain it.

4.5 Checking the allowance must add less than 50 ms to approval at the 99th percentile, at twice expected peak volume.

## 5. The card user's experience

5.1 The card user can see how much is left and when it resets. The amount should be no more than a minute old.

5.2 After a decline, the card user gets a message within 10 seconds that names the allowance as the reason and says how far over the purchase was.

5.3 The card user can ask for a top-up for this cycle, with an amount and an optional note. One open request at a time.

5.4 Optionally, the card user is alerted when the remaining allowance drops below a threshold the cardholder sets.

## 6. The cardholder's experience

6.1 The cardholder can approve or decline a top-up request in one step from a notification. Approval raises this cycle's allowance only.

6.2 The monthly statement groups spend by card user and shows each allowance beside the subtotal.

6.3 When counted charges take a card user past the allowance, the cardholder is alerted once per cycle, naming the merchant.

## 7. Servicing and compliance

7.1 Agents can see a card user's allowance, the amount left and 90 days of limit declines in the existing account view.

7.2 A limit decline must never raise the fraud score or open a fraud case.

7.3 Before turning the feature on, cardholders are told which charges are blocked and which are only counted. Compliance approves the wording.

7.4 An allowance for a card user under 18 needs recorded consent.

## FAQ

**Does a changed amount apply immediately?** It applies from the next cycle.
