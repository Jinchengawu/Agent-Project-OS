# Organization and PMO Governance

[中文](ORGANIZATION.zh-CN.md)

Agent Project OS models a local AI engineering organization without turning the organization repository into a copy of every project ledger.

```text
Founder
└── Agent CEO
    ├── PMO
    │   ├── Project PM A → Project A agents and evidence
    │   ├── Project PM B → Project B agents and evidence
    │   └── Project PM N → Project N agents and evidence
    └── Agent HR → roles, evaluations, releases, promotion and retirement
```

## Ownership boundary

The organization root owns project registration, priorities, accountable-PM assignments, supervision dispatches, immutable child-PM reports, PMO reviews, portfolio reviews, and CEO exceptions. Each project repository continues to own its tasks, evidence, decisions, handoffs, and domain state. Reports contain summaries and evidence pointers, never a copied task ledger.

Every active project must have exactly one accountable PM. The PM may submit a report, but cannot review that report. PMO or the Founder records the terminal review. A `done` report needs at least one evidence reference; when the project path is a Git repository, the submitted commit must match its current HEAD.

## Minimal loop

```sh
agent-project org init --organization-id studio --name "Studio" \
  --founder human:founder --ceo-agent-id agent:ceo --pmo-agent-id agent:pmo

agent-project project add --project-id service --path projects/service \
  --owner human:founder --project-priority P1 \
  --verification "python -m unittest" --supervision weekly \
  --next-due-at 2026-08-24T01:00:00Z

agent-project project assign-pm --assignment-id service-pm \
  --project-id service --pm-agent-id agent:service-pm

agent-project supervision dispatch --dispatch-id service-week-34 \
  --project-id service --objective "Reconcile current evidence and blockers" \
  --expected-output "Bounded child PM report" --acceptance "References current commit" \
  --due-at 2026-08-25T01:00:00Z

agent-project supervision submit --report-id service-report-34 \
  --dispatch-id service-week-34 --summary "Validation is green" \
  --project-commit abc123 --reported-status waiting_review \
  --next-acceptance "Consumer accepts the contract" \
  --evidence-ref evidence:service-e2 --submitted-by agent:service-pm

agent-project supervision accept --review-id service-review-34 \
  --report-id service-report-34 --reviewed-by agent:pmo
agent-project portfolio review --review-id portfolio-week-34 \
  --as-of 2026-08-25T02:00:00Z
```

Acceptance advances the project's next daily, weekly, or monthly due time in its declared IANA timezone. Monthly scheduling follows local calendar days and accounts for DST before converting back to UTC.

## CEO exception queue

Portfolio reviews and the read-only dashboard raise active projects with no PM, missing or rejected reports, or declared blockers. They do not silently reprioritize a project or approve project work. Priority is an organization routing field (`P0`–`P3`), not proof of business value.
