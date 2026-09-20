# Lesson templates

Loaded by `learning-module` step 6. Shapes are language-neutral; render them in the lesson's
language with its comment and docstring conventions.

## Exercise file header and sections

```
"""
LESSON: <title>
TOPIC: <topic-slug>/<number>
DIFFICULTY: beginner | intermediate | advanced
BLOOM: Apply | Analyze | Evaluate | Create
BASED ON: <real project files, with line ranges>
RUN: <the one command>

What you'll learn:
- <concept 1>
- <concept 2>

Prerequisites:
  <install command for any non-standard package>
"""

# --- SETUP (do not modify) ---
# Self-contained models, engine or client, fixtures. Mirror the project's patterns
# against the in-memory store.

# --- EXERCISE ---
# TODOs that teach the concept before asking for code (see below).

# --- SELF-CHECK ---
# Staged checks with helpful messages (see below).

# --- REFLECTION PROMPTS ---
"""
After the self-check passes and before opening the solution, answer in reflection.md:
1. In your own words, why does this pattern exist in the production code?
2. What mental model are you using for the key abstraction?
3. What would you tell a teammate about to write the broken version of this?
4. How does this connect to the previous lesson(s)?
"""
```

## Concept-first TODOs

A TODO is not a copy-paste recipe. For each non-obvious API or pattern, in this order:

- **Mental model**: the role this concept plays in the flow, in one sentence.
- **Why it exists**: the problem it solves in the real project, with the file that shows it.
- **Failure mode**: what breaks, and how it looks, when it is omitted or misused.
- **Implementation hint**: the smallest useful nudge; a full answer only when the goal is
  syntax recognition.

Example shape for a multi-layer request lesson (rendered for the project's stack):

```text
<HTTP method> <path>
   |
   v
route handler
   |  the request-scoped dependency yields a session or client for this request
   v
model layer: <entity>
   |  write, then flush or commit fills generated fields
   v
entity object with the related rows already loaded
   |  the response schema reads attributes and validates the public shape
   v
JSON response
```

## Staged self-checks

Help the learner validate partial work. Never one big end-to-end test that fails late and
hides which concept broke. Single-source pattern:

- One `check_<concept>` function per concept with a step name, a success message, a failure
  explanation, and the next hint.
- The language's standard test runner calls the same functions (one test per check), so the
  runner stays available.
- The script entrypoint runs the steps in order and prints a readable report.
- Later steps may depend on earlier ones; their failure messages name the earlier concept
  that is probably blocking.

```
def check_schema_shape():
    """Step 1: the response schema can read a nested related object."""
    ...

def test_schema_shape():
    check_schema_shape()

if __name__ == "__main__":
    run_steps([
        ("Schema shape", check_schema_shape),
        ("Dependency yields a session", check_dependency),
        ("Create returns the nested response", check_create),
        ("Read eager-loads relationships", check_read),
    ])
```

Expected output:

```text
Step 1/4: Schema shape
  PASS The response schema reads a nested related object from attributes.

Step 2/4: Dependency yields a session
  FAIL The framework received a generator object instead of a session.
  Hint: pass a real generator function to the dependency, not a lambda that returns one.
```

## Solution file

- Every TODO completed.
- Inline **WHY** comments, not WHAT.
- A **Common Mistakes** section at the bottom.
- An **Alternative Designs** section comparing other approaches and their trade-offs.

## reflection.md

```markdown
# Reflection: <lesson title>

Fill this in after the self-check passes and before opening the solution.

## 1. Why does this pattern exist in the production code?
<!-- Your answer here -->

## 2. What mental model are you using for the key abstraction?
<!-- Your answer here -->

## 3. What would you tell a teammate about to write the broken version?
<!-- Your answer here -->

## 4. How does this connect to the previous lesson(s)?
<!-- Your answer here -->
```

## Bug hunt

`buggy.<ext>`: a self-contained but flawed version of a real pattern (a wrong session setting,
an incorrect loading strategy, a missing flush, a job that is not idempotent, a component that
mutates during render). `exercise.md`: "Run the script. You will see <symptom>. Diagnose the
root cause and propose a minimal fix. Then implement it." `solution.md`: the diagnosis step by
step, the corrected version, and why the bug was subtle. Pull candidates from
`$DOCS_DIR/LESSONS.md` Bug Log and gotcha sections first.

## Synthesis

After a tier: one task that requires combining that tier's concepts in a single coherent
implementation (for example create a parent and child in one transaction, respecting the
foreign-key delete rule, and return the nested shape), plus a short written justification:
which production file does this mirror, and why was the pattern chosen?

## Expert synthesis capstone

- `critique-task.md`: "Here is a real snippet from `<file>:<line>`. Write a code review: is the
  pattern correct, what are the risks, suggest an improvement."
- `design-task.md`: "The current approach uses X. Design an alternative suitable for
  <new constraint>. Justify your choices."
- `open-response.md`: two or three essay questions requiring synthesis and transfer.

## learning-plan.md

```markdown
# Learning plan: <topic>

Mode: trace | deep dive | focused
Runtime: <one-line description of the isolated runtime>

## Tier 1: <name>
| # | Lesson | Type | Bloom | Based on | Run |
|---|---|---|---|---|---|
| 01 | ... | implementation | Apply | <files> | <command> |
| bug-hunt-01 | ... | bug hunt | Analyze | <files> | <command> |
| synthesis-01 | ... | synthesis | Evaluate | <files> | <command> |

## Tier 2: ...

## Capstone
critique, design, open response
```

## summary.md

```markdown
# Summary: <topic>

## Sessions
### <utc-date>
- Pre-quiz: <score> (<per-question results>)
- Misconception profile: strong on ...; weak on ...
- Completed: ... · Struggled with: ... · Bug hunts solved: ...
- Needed extra explanation: ...
- Reflection excerpts: "..." (01), "..." (02)
- Post-quiz: <score or not taken>

## Review scheduler
- <utc-date>: before starting Tier 2, replay the self-check of lesson 01 (5 minutes)
```

## quiz-pre.md and quiz-post.md

Each question: the question in plain English, lettered options, the correct answer, a
one-line explanation with the project file that shows it, and the learner's answer once given.
