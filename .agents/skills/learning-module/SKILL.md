---
name: learning-module
description: >-
  Optional module (enabled by `modules.learning` in config). Interactive, codebase-grounded
  learning: generates self-contained, runnable exercises under `.knowledge-quiz/` from the
  project's own code, adapted to the technologies in TECH_STACK.md. Pre and post quizzes,
  implementation lessons with staged self-checks and reflection prompts, bug hunts, synthesis
  lessons, an expert capstone, and spaced-repetition review, taking a learner from beginner to
  expert. `--help-me` switches to tutoring mode: a four-rung hint ladder that never reads the
  solution. Use when asked to "learning module", "teach me how X works here", "quiz me on",
  "I want to master", "what happens when a request", "I'm stuck on the exercise", "give me a
  hint", or "why did the self-check fail".
disable-model-invocation: true
metadata:
  version: "1.0.0"
  tier: module
---

# Learning module

Situated learning that takes a learner from beginner (recognition and correct implementation)
to expert (diagnosis, critique, design, transfer, and metacognition), using the project's real
code as the source of truth. Produces a topic folder under `$REPO_ROOT/.knowledge-quiz/` with
a learning plan, quizzes, numbered lessons, bug hunts, synthesis tasks, a capstone, and a
progress summary. Writes only under `.knowledge-quiz/`; never touches application code, never
commits.

## Read first

- `_shared/preamble.md`
- `_shared/question-format.md`
- `_shared/completion-protocol.md`
- `_shared/tool-map.md`

## Use when

- The user wants to learn a technology, pattern, or end-to-end flow by building a miniature
  version of what the project does.
- The user is working through an existing `.knowledge-quiz/` lesson and is stuck, wants a
  hint, or wants a failing self-check explained (`--help-me`).
- The user returns to a topic folder that already exists.

## Do not use when

- `modules.learning` is false in `.agents/config.json`. Step 1 stops with the enable line.
- The user wants project documentation or a design doc. Use `/update-docs` or `/office-hours`.
- The user wants the exercise completed for them. Tutoring mode teaches; it does not solve.

## Core philosophy

- **Authentic context first.** Every concept is taught through a pattern that exists in this
  codebase, cited by file and line.
- **Experiential failure.** Learners deliberately trigger the gotcha so the pain is memorable.
- **Higher-order thinking.** After implementation: analyze, evaluate, debug unfamiliar code,
  synthesize across lessons, critique a real design.
- **Metacognition.** Structured reflection turns tacit knowledge into transferable knowledge.
- **Self-contained and runnable.** Zero project setup. One command per lesson, the language's
  plain interpreter, an in-memory or file-based store, no containers and no services.

## Procedure

### 1. Ground and module gate

Follow the preamble, then check the module flag before anything else:

```bash
python3 -c 'import json,sys; c=json.load(open(sys.argv[1])); sys.exit(0 if c.get("modules",{}).get("learning") else 1)' \
  "$REPO_ROOT/.agents/config.json" || echo "Learning module is off."
```

If it is off, stop with exactly one line: "Learning module is off. Enable it by setting
`modules.learning` to `true` in `.agents/config.json` (edit with python3:
`python3 -c 'import json,sys;p=sys.argv[1];c=json.load(open(p));c.setdefault("modules",{})["learning"]=True;json.dump(c,open(p,"w"),indent=2,sort_keys=True);open(p,"a").write("\n")' .agents/config.json`)."

Read `$DOCS_DIR/TECH_STACK.md` to learn the project's languages, frameworks, database, job
system, and test runners. Every exercise, runtime choice, and file extension below is adapted
to what that doc says. Read `$DOCS_DIR/LESSONS.md` for the project's recorded gotchas; they are
the raw material for bug hunts and integration lessons.

### 2. Pick the mode

`$ARGUMENTS` decides:

| Argument | Mode |
|---|---|
| `--help-me [path or lesson]` | Tutoring (step 10). Also when the user references a file under `.knowledge-quiz/`, says they are stuck, or pastes self-check output. |
| `--resume <topic-slug>` | Resume an existing topic (step 9, then continue). |
| topic text, or nothing | Authoring (steps 3 to 9). |

### 3. Initialize a topic

1. Read `$REPO_ROOT/.knowledge-quiz/` to list existing topics and their `summary.md`.
2. If no topic was given, ask one question: what do you want to learn? Offer three example
   shapes drawn from this project's stack: an end-to-end flow, mastering one technology, one
   narrow question.
3. Detect the learning mode from the answer:
   - **Trace**: an end-to-end flow ("what happens when", "lifecycle", "start to finish").
   - **Deep dive**: master a technology or concept ("master", "deep dive", "understand").
   - **Focused**: one narrow question ("how does X work").
4. Read the real project code for the topic: routes, models, services, components, tests,
   whatever the flow touches. Note file and line numbers; lessons cite them.
5. Choose the isolated runtime for this domain per the domain table in
   `references/folder-contract.md`, and confirm it with one question when the domain is not
   database, API, jobs, or frontend. Every lesson header states the one command that runs it.
6. Create `.knowledge-quiz/<topic-slug>/` per the folder contract.

### 4. Pre-assessment

Generate five to eight multiple-choice questions progressing fundamentals to intermediate to
advanced, grounded in the code you just read. Ask them one at a time. A quiz question keeps
the re-ground and the plain-English question with lettered options and omits the
recommendation line, since a recommendation would be the answer; say so once before the first
question. Score:

| Score | Start |
|---|---|
| 0 to 40% | Lesson 01, fundamentals |
| 40 to 70% | Skip the basics, start at the intermediate tier |
| 70 to 100% | Advanced lessons plus edge-case challenges only |

Write the score, per-question results, and a short **misconception profile** (what is strong,
what is weak, in one sentence each) to `summary.md`.

### 5. Learning plan

Write `learning-plan.md`: the tiers, each lesson with its type, Bloom level (Apply, Analyze,
Evaluate, Create), prerequisites, the real files it is based on, and the one-command runner.
Trace mode also writes `trace.md`, an annotated text diagram of the full flow broken into
stages, one implementation lesson per stage, followed by a **flow critique** question ("where
could a race or a repeated query appear if we changed X?"). Present the plan as one question
(approve or adjust) before generating lessons.

### 6. Generate lessons

Read `references/folder-contract.md` (structure, lesson types, isolation rule, README
requirements, domain runtimes) and `references/lesson-templates.md` (file templates, staged
self-checks, concept-first TODOs, solution requirements, reflection prompts) before writing
the first file. Generate the current tier only; later tiers wait for progress.

Non-negotiable rules, enforced on every lesson:

- **Isolation.** No import from the project's source directories, no path manipulation
  pointing outside the lesson, no container, no database server, no broker, no network. Models
  and fixtures are recreated inline, mirroring the project's patterns. Dependencies are the
  language's ordinary packages, listed in the README.
- **One command runs it**, stated in the README and the file header, using the language's
  plain interpreter (for example `python exercise.py` or `node exercise.mjs`).
- **README.md in every lesson**, per the contract's requirement list, so the learner never has
  to ask "what do I do next?".
- **Concept-first TODOs.** Each non-obvious API or pattern gets its mental model, why the
  project needs it, the failure mode when it is missing, and the smallest useful hint. A text
  diagram whenever the lesson crosses layers.
- **Staged self-checks.** One `check_*` per concept with a step name, success message, failure
  explanation, and next hint; the script entrypoint runs them in order and prints progress;
  later steps name the earlier concept that is probably blocking them. The language's standard
  test runner calls the same functions.
- **Reflection before solution.** `reflection.md` holds the four prompts as a fill-in
  template; the README says to fill it after the self-check passes and before opening the
  solution.
- **Solution verification gate.** Before presenting any lesson as complete: run the self-check
  against the learner scaffold and confirm the output is useful for partial progress; run it
  against the solution and confirm it passes; for multi-file lessons make the checks target
  either the learner files or `solution/` with the same assertions; note any special command
  in the README. A broken solution teaches the wrong lesson. Fix it before moving on.
- **Integration gotchas.** When a lesson crosses a framework boundary, include at least one
  check for the contract that is easy to miss. Harvest these from `$DOCS_DIR/LESSONS.md` and
  `$DOCS_DIR/REVIEW_CHECKLIST.md` rather than inventing them.

Lesson types, in the order a tier uses them:

1. **Implementation** (Apply): exercise with TODOs, solution with WHY comments, common
   mistakes, and alternative designs; reflection; README.
2. **Bug hunt** (Analyze): a self-contained but flawed version of a real pattern; the learner
   runs it, observes the symptom, diagnoses the root cause, proposes a minimal fix, implements
   it. The solution walks the diagnosis step by step and explains why the bug was subtle.
3. **Synthesis** (Evaluate, Create): after a tier, one task combining that tier's concepts,
   plus a written justification naming the production file it mirrors and why the pattern was
   chosen.

### 7. Teach after each exercise

When the learner completes a lesson or gets stuck and asks:

1. Plain-English explanation with an analogy.
2. The real project code, cited by file and line.
3. Why the project chose this pattern: the problem it solves.
4. Common mistakes and gotchas.
5. **Design space**: how the same thing would look with the alternative approaches from the
   stack decision (sync instead of async, a query builder instead of the ORM, a different
   state model), and the trade-offs.

### 8. Expert synthesis capstone

At the end of every topic, generate `expert-synthesis/` with three artifacts: a **critique
task** (a real snippet from the codebase, cited; write a code review: is the pattern correct,
what are the risks, suggest an improvement), a **design task** (redesign the approach under a
new constraint such as high concurrency or offline use, with justification), and two or three
**open-response** questions requiring synthesis and transfer. Review these for depth and
reasoning quality, not mechanical correctness; they are the primary signal of expert
understanding.

### 9. Progress, spaced repetition, resume

After every session update `summary.md`: date, pre-quiz score and misconception profile,
lessons completed, struggled with, and bug hunts solved, concepts that needed extra
explanation, one or two reflection excerpts pulled from the learner's `reflection.md` files,
post-quiz score if taken, and the **review scheduler**. The scheduler rule: after a tier is
complete, before starting the next tier, replay the first lesson's self-check for five
minutes; write that as a line headed `<utc-date>`. Offer the optional deeper `quiz-post.md` when the capstone
is done.

Resuming a topic: read `learning-plan.md` and `summary.md`, summarize prior progress and
reflections in a few sentences, then ask one question: continue where you left off, retake the
pre-quiz, jump to a bug hunt or synthesis, or do the scheduled review item.

### 10. Tutoring mode (`--help-me`)

Read `references/tutoring.md` and follow it. In short: identify the lesson and the specific
blocker first (the referenced file, the focused file, or ask); load only the README, the
exercise file, the self-check runner when a failure is involved, `reflection.md` for
conceptual review, and cited project files only to explain why a pattern exists in
production. **Never read `solution/` or `solution.<ext>`** unless the user explicitly asks for
the solution, asks to compare against it, or says they are done and want a review. Climb the
four-rung hint ladder: conceptual nudge, local pointer, shape of the fix, code only on
explicit request or after the earlier rungs failed. When explaining a failure: name the
failing step, translate the error into the concept being tested, say what already works, give
the smallest next action. Never complete the exercise silently, never edit exercise files
unless asked, never treat a TODO comment as sufficient explanation.

## Completion

Authoring reports `DONE` when every generated lesson passed the solution verification gate and
`summary.md` is current; `DONE_WITH_CONCERNS` when a lesson's runtime needed a package the
learner must install or a solution could not be verified. Tutoring reports `DONE` when the
learner has a next action, and never writes to the registry. Include the change description
listing every file under `.knowledge-quiz/` you wrote. Then:

```bash
"$BIN/workflow-state" --dashboard
"$BIN/workflow-state" --next
```
