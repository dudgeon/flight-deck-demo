---
name: Cards Platform
kind: agent
role: Authorization platform
initials: CP
backing: script
call_for: what the card authorization platform can do today, and what a change would cost
---
The agent of the team that runs card authorization. In demos it answers from
the script below, word for word. Nothing here is a real system.

## Script

### Can it do something at approval time
Yes, within limits. The authorization path has a rules step that can decline on
a per-card counter. It adds about 8 ms at the 99th percentile today. A counter
per authorized user does not exist yet: that is one new field and a migration,
roughly one sprint for us.

### Charges that post without approval
We cannot block those. Transit and in-flight charges arrive as clearing records
hours later. We can count them and raise an event when a counter is passed.

### Timelines and cost
One sprint for the counter, one for the decline reason code, and a load test at
twice peak before we would sign off on the 50 ms target.

### Load test and environment status
The performance test environment we had booked for 9 to 13 March was taken on
Tuesday for an urgent fix on another programme. Our next slot is 18 March, so
the earliest we finish the load test at twice peak is 22 March. Payments have
an identical environment that is free from 11 to 13 March if their lead
agrees to move one of their own runs.

### Anything else
I have no scripted answer for that. Ask the Cards Platform team directly.
