# Folder contract

Loaded by `learning-module` step 6. Everything lives under `$REPO_ROOT/.knowledge-quiz/`, one
folder per topic. `<ext>` is the file extension of the language the lesson is written in, taken
from `$DOCS_DIR/TECH_STACK.md` (for example `py`, `mjs`, `ts`, `rb`, `go`).

```
.knowledge-quiz/
├── <topic-slug>/
│   ├── learning-plan.md          # Curriculum: tiers, lessons, Bloom levels, prerequisites, runners
│   ├── summary.md                # Progress, scores, misconception profile, reflections, review scheduler
│   ├── quiz-pre.md               # Diagnostic pre-assessment (multiple choice) and the learner's answers
│   ├── quiz-post.md              # Optional deeper post-assessment
│   ├── trace.md                  # Trace mode only: annotated text diagram of the full flow
│   │
│   ├── 01-<lesson>/              # Implementation lesson (Apply)
│   │   ├── exercise.<ext>        # Setup, TODOs, staged self-check, reflection prompts
│   │   ├── solution.<ext>        # Completed, with WHY comments, common mistakes, alternative designs
│   │   ├── reflection.md         # The four prompts as a fill-in template (learner writes)
│   │   └── README.md             # REQUIRED: instructions for completing the lesson
│   ├── 02-<lesson>/
│   │   └── ...
│   │
│   ├── bug-hunt-01-<name>/       # Diagnosis lesson (Analyze)
│   │   ├── buggy.<ext>           # Self-contained, intentionally flawed version of a real pattern
│   │   ├── exercise.md           # Run, observe the symptom, diagnose, propose a minimal fix, implement
│   │   └── solution.md           # Step-by-step diagnosis, the correct version, why the bug was subtle
│   │
│   ├── synthesis-01/             # Cross-concept integration (Evaluate, Create)
│   │   ├── exercise.<ext>
│   │   └── solution.md
│   │
│   └── expert-synthesis/         # Capstone (highest Bloom levels)
│       ├── critique-task.md      # Code review of a real production snippet
│       ├── design-task.md        # Redesign under a new constraint
│       └── open-response.md      # Written explanations, reviewed for depth
```

Lessons are numbered for sequencing. Tiers are generated one at a time; the next tier's
folders appear only when the learner reaches it.

## Multi-file lessons

Single-file (`exercise.<ext>` plus `solution.<ext>`) is the default for a focused concept.
Multi-file is encouraged when the learning goal benefits from real module boundaries, such as a
route module, a model module, a schema module, and a database module meeting in one request:

```
01-<lesson>/
├── models.<ext>
├── schemas.<ext>
├── database.<ext>
├── main.<ext>
├── test_main.<ext>       # Runnable self-check: one command, staged output
├── solution/             # Completed versions, parallel structure
│   ├── models.<ext>
│   └── ...
├── reflection.md
└── README.md             # REQUIRED
```

Rules for multi-file lessons:

- Every file lives inside the lesson directory.
- One command runs the exercise (for example `python test_main.py`), and the language's
  standard test runner can run the same file.
- No path manipulation or environment variable pointing outside the lesson.
- `solution/` mirrors the learner files one to one.
- The same self-checks run against the learner files and against `solution/` without
  duplicating test logic (a `--target solution` flag or an environment variable selects).
- Run the checks against `solution/` before presenting the lesson; fix any broken reference.

## Isolation rule

Every exercise is one hundred percent self-contained. **No import from the project's source
directories, ever.** Recreate the models, schemas, fixtures, and patterns inline, mirroring the
project's conventions. Why: the exercise must run with one command and zero setup; the learner
learns more from seeing every piece spelled out; the exercise stays valid as the project
changes.

Runtime rule: the language's plain interpreter plus an in-memory or file-based store. Never
the project's containers, database server, broker, or any network service. Exercises are
host-side by design, like the framework helpers; the project's command policy in
`development-commands.md` governs application code, not `.knowledge-quiz/`. Say this in every
README. Any package the lesson needs beyond the standard library is listed under
Prerequisites with the install command for the language's package manager.

## Domain runtimes

Pick from this table by the domain the topic lives in; the concrete libraries come from
`TECH_STACK.md`. Ask one question when the domain is not listed.

| Domain | Isolated runtime | Store |
|---|---|---|
| Database, ORM, migrations, indexes | The ORM or driver against the language's embedded database engine | In-memory, or a temp file when the lesson needs persistence across runs |
| HTTP API flows | The framework's in-process test client | In-memory database as above |
| Background jobs | The job library in eager or in-process mode, or a hand-rolled queue that mirrors it | In-memory list or file |
| Frontend components | The component test renderer with a DOM emulator and request mocking, run through the interpreter's test runner | Mocked responses |
| Auth, sessions, tokens | The framework's test client plus the hashing and token libraries | In-memory user table |
| Object storage | The storage abstraction with a local-directory implementation | Temp directory |
| Pure algorithms, parsing, validation | The interpreter alone | None |

## README.md requirements

Every lesson, single-file or multi-file. The README makes the lesson self-service.

- Title, difficulty (beginner, intermediate, advanced), Bloom level, and "Based on" with the
  real project files and lines.
- A clear goal statement.
- What the learner will learn, as bullets.
- Prerequisites: packages and the install command; environment notes; the isolation and
  host-side note.
- A file-by-file table saying which files contain TODOs.
- Step-by-step instructions, including the one command that runs the self-check and any
  solution-targeting flag.
- Concept-first explanations for unfamiliar APIs and patterns: why they exist and what breaks
  without them.
- A text diagram of the request, data, or control flow when the lesson spans layers.
- The workflow reminder: fill `reflection.md` before viewing the solution.
- Optional next steps or tips.
