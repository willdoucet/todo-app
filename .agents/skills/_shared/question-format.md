# Question format

Every question to the user follows this structure. One decision per question. Never batch.

1. **Re-ground.** State the project, the branch from `ctx` (never one remembered from the
   conversation), and the current plan or task. One or two sentences.
2. **Simplify.** Explain the problem in plain English a smart sixteen-year-old could follow.
   No function names, no internal jargon, no implementation detail. Concrete examples and
   analogies. Say what it does, not what it is called.
3. **Recommend.** `RECOMMENDATION: Choose [X] because [one-line reason]`. Prefer the complete
   option. Include `Completeness: X/10` for each option. If both are 8 or above pick the higher;
   if one is 5 or below, say so.
4. **Options.** Lettered: `A) ... B) ... C) ...`. When an option involves effort, show both
   scales: `(human: ~X / AI-assisted: ~Y)`.

Assume the user has not looked at this window in twenty minutes and does not have the code open.
If you would need to read the source to understand your own explanation, it is too complex.

## Harness fallback

Use the harness's structured question tool when one exists (see `_shared/tool-map.md`). When it
does not, write the same four parts as plain text, end with the lettered options, and wait for
the reply before doing anything else. Do not proceed on a guess.
