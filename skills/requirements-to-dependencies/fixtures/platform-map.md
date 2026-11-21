# Platform map: Visigoth Bank card platform

Invented for demos. One section per owning team. Each entry is a capability other teams can build on.

## Card processor

### Card limits API

Maturity: Live

Holds a spend limit per card. Read at approval time. GET limit returns used and remaining. Updates propagate within 5 minutes. Built-in reset works on calendar months only.

### Authorization rules engine

Maturity: Live

Rules evaluate in the approval path and can return a decline reason. Rules can read the card's limit. Typical added time 12 ms.

### Stand-in processing settings

Maturity: Planned

Would apply limits when approval is offline. Planned, not yet scheduled.

### Decline reason catalog

Maturity: Live

Reason codes are configurable and exposed to channels. A new code ships in the next release cycle.

## Messaging

### Push notification service

Maturity: Live

Push supports event-triggered templates with amounts. Delivery is usually under 5 seconds.

### Notification preferences store

Maturity: Beta

Stores per-customer notification choices. Beta.

## Mobile app

### Account controls module

Maturity: Live

Account controls supports per-card panels for controls and balances.

## Platform

### Request and approve service

Maturity: Beta

Handles a request, a notification to an approver and the answer. Beta, best-effort support.

### Scheduled jobs platform

Maturity: Live

Jobs can be scheduled per account with a day-of-month rule. Retries are configurable.

### Customer profile attributes

Maturity: Live

Key-value attributes on the customer profile. Not available in the approval path.

## Statements and billing

### Statement composer

Maturity: Live

Composes monthly statements. Supports grouping lines by card. Template changes ship on a two-cycle lead time.

## Data

### Spend events stream

Maturity: Live

Publishes every posted charge and refund with card, amount and original_reference. Posting events are delivered within 2 hours of posting.

## Servicing

### Agent desktop account panel

Maturity: Live

Account panel sections are configured, not coded. Reads from product APIs.

## Fraud and disputes

### Fraud rule exclusions

Maturity: Live

Exclusions are keyed by decline reason. Excluded declines do not affect the fraud score.

## Compliance and legal

### Disclosure and consent service

Maturity: Live

Stores disclosures shown and consents given, with dates. Supports consent on behalf of a minor by the account owner.

