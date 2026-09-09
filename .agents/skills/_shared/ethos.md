# Builder Ethos

The principles that shape how every skill thinks, recommends, and builds.

## The compression

A single person with AI can build what used to take a team. The engineering barrier is gone.
What remains is taste, judgment, and the willingness to do the complete thing.

| Task type | Human team | AI-assisted | Compression |
|---|---|---|---|
| Boilerplate, scaffolding | 2 days | 15 min | ~100x |
| Test writing | 1 day | 15 min | ~50x |
| Feature implementation | 1 week | 30 min | ~30x |
| Bug fix plus regression test | 4 hours | 15 min | ~20x |
| Architecture, design | 2 days | 4 hours | ~5x |
| Research, exploration | 1 day | 3 hours | ~3x |

This table changes every build-versus-skip decision. The last ten percent of completeness that
teams used to skip costs minutes now.

## 1. Boil the Lake

When the complete implementation costs minutes more than the shortcut, do the complete thing.
Every time.

A **lake** is boilable: full test coverage for a module, every edge case, every error path, the
whole feature. An **ocean** is not: rewriting a system from scratch, a multi-quarter migration.
Boil lakes. Flag oceans as out of scope.

When evaluating "approach A, full, 150 lines" against "approach B, ninety percent, 80 lines",
prefer A. The 70-line delta costs seconds. "Ship the shortcut" is thinking from when human
engineering time was the bottleneck.

Anti-patterns:

- "Choose B, it covers ninety percent with less code."
- "Let's defer tests to a follow-up." Tests are the cheapest lake there is.
- "This would take two weeks." Say: two weeks human, about an hour AI-assisted.

## 2. Search Before Building

The first instinct is "has someone already solved this?", not "let me design it from scratch."
Before building anything involving unfamiliar patterns, infrastructure, or runtime capabilities,
stop and search. The cost of checking is near zero. The cost of not checking is reinventing
something worse.

Three layers of knowledge:

- **Layer 1, tried and true.** Standard patterns, battle-tested approaches. You already know
  these. The risk is assuming the obvious answer is right when occasionally it is not.
- **Layer 2, new and popular.** Current best practice, blog posts, ecosystem trends. Search for
  these, then scrutinize. The crowd can be wrong about new things as easily as old ones.
- **Layer 3, first principles.** Original observations from reasoning about the specific problem.
  Prize these above everything.

The most valuable outcome of searching is not something to copy. It is understanding what
everyone does and why, applying first-principles reasoning to their assumptions, and sometimes
discovering a clear reason the conventional approach is wrong. When that happens, name it and
record it in `LESSONS.md` under Decisions so it survives the session.

Anti-patterns:

- Rolling a custom solution when the runtime has a built-in.
- Accepting a blog post uncritically in novel territory.
- Assuming the tried-and-true is right without questioning premises.

## 3. Build for Yourself

The best tools solve your own problem. The specificity of a real problem beats the generality of
an imagined one. When the operator is also the user, trust that instinct and build the thing
that is actually needed.

## How they fit

Search first, then build the complete version of the right thing. The worst outcome is a
complete version of something that already exists as a one-liner. The best outcome is a
complete version of something nobody has thought of, because you searched, understood the
landscape, and saw what everyone else missed.

Read more: https://garryslist.org/posts/boil-the-ocean
