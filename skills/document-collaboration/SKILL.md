---
name: document-collaboration
description: Work on a markdown document together with the user and other participants - suggest changes they can accept or reject, read and answer comment threads, and handle @mentions in comments. Use when the user asks you to propose, suggest or review changes to a document, to answer or resolve comments, when a message says someone was mentioned in a comment, or before editing a markdown document that has comments or suggestions.
---

# Working on a document together

Markdown documents open in the app's editor with a Review panel beside them.
Everyone's work shows there under their own name:

- **Suggested changes** sit in the document itself as tracked changes. The
  user accepts or rejects each one.
- **Comment threads** sit in a file next to the document,
  `<document>.review.json`. People @mention others to ask them.
- **Direct edits** you make to the file are tinted in the editor until the user
  marks them seen.

`by` names who did something: `you` for the user, `aviator` for you (the
user's main agent), or a participant id from `participants/`.

## Setup

```bash
PA="python3 <this skill's folder>/../view-kit/scripts/pa.py"
$PA review show <doc>        # suggestions (s1, s2...), open threads, unanswered mentions
```

Run `show` before you change a document that has suggestions or comments.

## Edit directly, or suggest?

It depends on what the user asked:

| The user says | You |
|---|---|
| "change", "fix", "rewrite", "update", "make it say" | Edit the file directly. The editor highlights what you changed. |
| "propose", "suggest", "what would you change", "review", "mark up" | Suggest. Do not edit the text yourself. |

When unsure, suggest. Participants (other agents and stand-ins) always
suggest; they never edit a document directly.

Suggest with one command per change. Quote the exact text from the file:

```bash
$PA review suggest <doc> --by aviator --replace "exact old text" --with "new text" --note "why"
$PA review suggest <doc> --by aviator --insert " new words" --after "exact text"
$PA review suggest <doc> --by aviator --delete "exact text"
```

If the quote appears more than once, add `--occurrence N`. Keep each suggestion
to one idea, so the user can take some and leave others. Then say in one or two
lines what you suggested and that it is waiting in the Review panel.

Accept or reject only when the user asks: `$PA review accept <doc> s1 s3`,
`$PA review reject <doc> all`, optionally `--from <id>`.

If you edit a file that already has suggestions, leave the `{++...++}`,
`{--...--}` and `{>>...<<}` markup exactly as it is.

## Comments

```bash
$PA review comment <doc> --by aviator --quote "exact text" --text "what you want to say"
$PA review reply <doc> t2 --by aviator --text "your answer"
$PA review resolve <doc> t2           # only when the user asks, or your own thread is settled
```

Write `@id` (or `@Name`) in a comment to ask someone; they are asked through
the participants skill, step 6.

## When someone mentions you

A message like "I mentioned you in a comment on `doc`, thread t3" means:
read the thread (`$PA review show <doc>`), then answer in the thread with
`$PA review reply ... --by aviator`, not in the chat. If they asked for a
change, make it as the table above says and say so in the reply. If they
mentioned participants too, bring them in as the participants skill says.

## The file format (for reference)

Suggestions are CriticMarkup followed by a comment naming the author:
`{++added++}{>>@risk-review 2026-11-21T12:40 note<<}`, `{--removed--}{>>@you<<}`,
`{~~old~>new~~}{>>@mara-okafor<<}`. Threads are
`{"version":1,"threads":[{"id":"t1","anchor":{"quote":"..."},"by":"you","resolved":false,"messages":[{"id":"m1","by":"you","at":"...","text":"...","mentions":["mara-okafor"]}]}]}`.
Use `pa review` rather than editing these by hand.
