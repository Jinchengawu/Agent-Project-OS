# Agent HR and Workforce Governance

[中文](WORKFORCE.zh-CN.md)

Agent HR keeps the Harness workforce evolvable without treating a model name or client session as an Agent identity. Agent records refer to runtime-neutral roles and versioned Prompt, Skill, or bundle assets by repository path, Git commit, and SHA-256.

## Invariants

- An Agent has at most one active release and one candidate release.
- A candidate requires a passed evaluation for the same Agent.
- The candidate Agent, independent reviewer, and promotion approver are three different identities.
- Promotion rechecks the candidate asset digest and preserves the previous active release as a rollback point.
- Rollback rechecks the old asset. Retirement is rejected while active role assignments still depend on the Agent.
- Production, permission escalation, public release, and Agent promotion remain human-authority gates.

## Release loop

```sh
agent-project role add --role-id project-pm --name "Project PM" \
  --purpose "Supervise one project" --authority submit_supervision_report

agent-project agent add --agent-id agent:service-pm --name "Service PM" \
  --role-id project-pm --release-id service-pm-v1 \
  --asset-path agents/service-pm.md --asset-commit abc123 \
  --asset-sha256 <sha256>

agent-project agent evaluate --evaluation-id service-pm-eval-v2 \
  --agent-id agent:service-pm --reviewer agent:hr-reviewer \
  --score 4 --outcome passed --evidence-ref evidence:eval-v2

agent-project agent propose-upgrade --proposal-id service-pm-upgrade-v2 \
  --agent-id agent:service-pm --release-id service-pm-v2 \
  --asset-path agents/service-pm-v2.md --asset-commit def456 \
  --asset-sha256 <sha256> --evaluation-id service-pm-eval-v2 \
  --proposed-by agent:service-pm

agent-project agent promote --proposal-id service-pm-upgrade-v2 \
  --approved-by agent:hr-approver
```

`agent-project workforce review` produces an immutable review record. The dashboard is only a projection of Agent lifecycle, roles, active release, and candidate release.

Agent Project OS owns the neutral records and transition rules. A capability repository such as AI-PMO may own concrete roles, Skills, Prompts, evaluation sets, and release content. Integration occurs through path, version, commit, digest, evidence, and CLI/Schema compatibility—not source copying.
