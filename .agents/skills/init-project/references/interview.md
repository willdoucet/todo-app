# Discovery interview

Loaded by `init-project` step N1 (new) and A2 (adopt). One question at a time, in the shared
format from `_shared/question-format.md`. Never batch. Never skip a topic because the answer
seems obvious; obvious answers are the ones that turn into wrong assumptions.

## Technique

- **Why before how.** When the user offers a solution ("it needs a Kanban board"), ask what
  problem it solves before accepting it. The problem goes in the PRD; the solution may change.
- **Specificity is the only currency.** "Families" is not a persona. A name, a role, a
  situation, and the moment they reach for the app is. Push once, politely, when an answer is
  vague; accept the second answer.
- **Generative, not interrogative.** Builder mode: riff, suggest the adjacent idea, ask what
  would make someone say "whoa". Then narrow: the deliverable is a v1 you can build, not a
  vision deck.
- **Socratic, with a default.** Every question carries your best inference as the
  recommendation so the user can say "yes" instead of typing. Options are the two or three
  answers you can infer plus a free-text option. When you have nothing to infer yet, present
  the three most common shapes and no recommendation line.
- **Validate completeness before moving on.** The interview ends with the assumptions block,
  not with the last question. Anything you filled in yourself is an assumption.
- **Vibe shift.** If the user starts talking about customers, revenue, or fundraising, say
  the framework's design step (`/office-hours`) has a startup mode for those questions; this
  interview stays about what to build.
- **Learning goals are requirements.** When the user says they want to learn something, write
  it down as a constraint the stack decision must honor, not as a preference.

## Question bank: new project

Ask in this order. Each line is one question. The parenthetical says what the answer feeds.

1. **What is it?** One sentence, then the coolest version of it. (PRD executive summary)
2. **Who is it for?** Name one primary persona and any secondary ones: role, situation, the
   moment they open the app. (PRD target users)
3. **What is the core value?** The one thing it must do well; what they use today instead.
   (PRD problem statement, status quo)
4. **What is the "aha"?** The moment a first-time user gets it. (PRD, APP_FLOW first-run flow)
5. **Must-have v1 features.** List them; then rank. Each becomes a phase. (PRD features,
   IMPLEMENTATION_PLAN phases)
6. **Explicitly out of scope.** What v1 will not do, so nobody builds it by accident. (PRD
   non-goals)
7. **Who is building it?** Solo or a team; hours per week; deadline if any. (Effort scales in
   every later recommendation)
8. **Learning goals.** Technologies or concepts the user wants to learn by building this.
   (Stack decision `Teaches:` lines, LESSONS decisions)
9. **Budget.** Monthly spend ceiling for hosting and services; free-tier only is a valid
   answer. (Hosting, storage, auth layers)
10. **Hosting preference.** A provider they already use, a region, or "you pick". (Deploy
    targets)
11. **Mobile.** Desktop-first, responsive web, or native later. (FRONTEND_GUIDELINES
    breakpoints, APP_FLOW)
12. **Scale expectations.** Users in year one, data volume, anything real-time. (Database,
    background jobs, hosting)
13. **Data sensitivity and auth.** Personal data, money, health, children; single user,
    household, or public sign-up; who must never see what. (Auth layer, PRD security
    requirements, risk tags on later plans)
14. **Project shape.** Confirm `web-split` (separate backend and frontend directories). State
    that it is the only supported shape today. (config `layout`, `project_shape`)
15. **Deployment intent.** Local only for now, a private deployment for a few people, or
    public launch; when. (IMPLEMENTATION_PLAN phase order, development-commands)
16. **Look and feel.** Brand colors or "propose a palette", font preference, dark mode, dense or
    airy, any product whose look they admire. (FRONTEND_GUIDELINES tokens)
17. **Integrations.** External services the product must talk to (calendar, payments, email,
    AI, storage). (TECH_STACK integrations, BACKEND_STRUCTURE)
18. **Anything else?** The question that catches what the list missed.

Then the assumptions block. Typical assumptions worth surfacing: the persona count, whether
accounts are per person or per group, whether data must survive a device change, whether
offline matters, whether the first deployment is single-tenant, and which features are v1
versus v1.1.

## Question bank: adopt

The code answers most questions. Ask only these, and skip any the README already answers:

1. **Who is it for?** Personas, since code shows features, not people.
2. **What is the core value?** The one thing users rely on.
3. **What is next?** The roadmap intent: the next two or three pieces of work and what is
   deferred. Cross-check against TODO files and issues found in the survey.
4. **Non-goals.** What the project will not become.
5. **Command policy.** How application commands must run (containers only, host, either) and
   any exception for host-side tooling. The existing rules file may already say.
6. **Anything the code lies about.** Dead features, half-finished migrations, directories
   that look active but are not. One question, free text.

Then the assumptions block for everything inferred from the code: which directories are
active, which tests are the real suites, which env vars are required, which branch is the base.
