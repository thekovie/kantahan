# 0007: An all-machines view that never merges machines

Status: accepted, 2026-10-24.

## Context

The songbook was one machine at a time, because a song's number belongs to a machine: the same number can be a different song on another machine, and a song that exists on one machine may not exist on another. The owner asked for an "all" version that is not split by machine, and said that where song numbers conflict the app should just say which machine each one is for.

## Decision

- **An "All machines" choice** sits first in the machine chooser (and as the first option of the select when there are many machines). It is only offered when there is more than one machine. The choice is remembered like any other. **A first visit, with nothing chosen yet, opens on All machines** (owner decision, 2026-10-24); a visitor who picked a machine keeps it. With a single machine there is nothing to choose and that machine is shown.
- **Nothing is merged.** Every entry keeps its own machine and its own number. The same title on two machines is two rows. The same number on two machines is two rows. This keeps the rule that the app never claims a song exists on a machine because it exists on another.
- **Every row names its machine** next to the number (a dot in the machine's line colour and the name in text), not only the conflicting ones, so a number is never read without knowing which remote it is for. Opening a row shows the sign of that song's machine.
- **Search and browse work as before** over the combined list: by title, artist or number, and by letter.
- **Loading:** the view needs every machine's songs. Machines already saved on the device load from there; the rest are downloaded once and saved. If a machine cannot be loaded, it is named and the others still show. The all-machines index is rebuilt in memory when the catalog changes.
- **The sign** for the view is ink (no single machine colour applies) and says how many machines are included. The catalog note says that the same number can be a different song on another machine.

## Consequences

- Because All is now the default, a first visit downloads every machine's songs before showing the list (about 1 MB compressed on the real catalog) instead of one machine's. After that they are saved on the device and the app works offline for every machine.
- Opening All for the first time downloads every machine's bundle. The real catalog is 12 machines, about 78,000 songs and 3.4 MB of JSON in total (before compression). Measured on a desktop: the search index builds in about 0.3 s and uses about 100 MB of memory, and a query takes under 10 ms. A phone will be several times slower to build, so titles are folded once instead of inside the sort. The index is built on the main thread; if this proves slow on real phones, move it to a worker.
- Search results in All are capped like any other (80), so a short query across many machines shows the first matches and asks the visitor to type more.
- Updates are unchanged: once a machine's songs are saved on the device, the existing sync keeps them current.
