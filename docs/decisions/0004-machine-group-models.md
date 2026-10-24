# 0004: Machine groups as models

Status: accepted, 2026-10-24 (owner decision)

## Context

Platinum's own song list page (Source A) groups its documents by machine group, for example
"T-X SERIES" or "KS-40 / KBOX-2 / KBOX-3". The same file is often listed under several groups. Most
documents' own page-1 headers name no machine, only a volume or month. Source D sells separate Reyna
2/3C/SE, Reyna 3/4 and T-X volumes from Vol 100, so the publisher's grouping is not proof that a file
works on every machine listed with it. The M1 rule (a volume joins a model only when its own header
says so) leaves almost every group empty.

## Decision

- Each Source A section is one model (twelve in total), named as the publisher names it.
- A volume belongs to every group that lists it, and the listing is recorded as the evidence
  ("listed under 'X' on the publisher's song list page"). This is the publisher's statement, not
  something verified here, and the app says where the songs come from.
- **Reyna stays strict**: a volume joins `reyna` only when its own header says "For Reyna" (Vol 62 to
  76). Its section also holds T-X and K-Box lists, and Source D separates those products.
- Mappings are only ever added, never removed because a link disappeared.

## Consequences

More machines are covered, but a volume may be listed for a group whose machines cannot use it; a
person who knows better can use `withdraw`. Reyna users get the smaller, more certain list.
Song numbers are still never merged across models. Models are named by group, so the app cannot say
which individual machine a list suits, only the group the publisher put it in.
