---
id: vertical-agent-factory
name: Vertical Agent Factory
version: 1.0.0
status: stable

description: >
  Design, generate, extend, audit and maintain reusable vertical-domain
  Agent packages on top of a shared Agent Harness and MCP platform.

triggers:
  - A new vertical-domain agent must be designed.
  - An existing domain agent must be extended or refactored.
  - Domain skills, capabilities, MCP bindings, workflows, policies or evals must be generated.
  - Multiple domain assets must be kept structurally consistent.
  - A domain package must be audited for architectural drift.

inputs:
  type: object
  required:
    - domain

outputs:
  type: object
  required:
    - domain_package
    - generated_assets
    - validation_report

policy:
  preserve_core_harness: true
  capability_first: true
  tool_hardcoding: deny

runtime:
  max_phases: 12
---

# Objective

Convert a vertical-domain requirement into a structured, versionable and
maintainable Domain Package without duplicating the shared Harness.

# Core Invariant

```text
Vertical Agent
=
Shared Harness
+ Domain Package
```

Shared Harness:

```text
Runtime
State
Context Builder
Planner
Skill Resolver
Capability Resolver
Policy Engine
Approval
Tool Executor
Checkpoint
Trace
Evaluation Hooks
```

Domain Package:

```text
Domain Definition
Ontology
Task Taxonomy
Agent Manifest
Domain Skills
Domain Capabilities
MCP Bindings
Workflows
Knowledge Configuration
Domain Policies
Output Schemas
Golden Evals
```

# Input Normalization

Normalize user requirements into:

```yaml
domain_request:

  domain:
    id:
    name:
    description:

  scope:
    include: []
    exclude: []

  users: []

  task_types: []

  entities: []

  workflows: []

  data_sources: []

  external_systems: []

  write_actions: []

  risk_profile:
    autonomy:
    approval:
    prohibited_actions: []

  freshness:
    requirements: []

  evidence:
    requirements: []

  outputs: []

  non_functional:
    latency:
    availability:
    cost:
    audit:
```

If information is missing, use conservative defaults and mark assumptions.

# Generation Phases

## Phase 1 — Domain Boundary

Generate `domain.yaml`.

Define purpose, in-scope, out-of-scope, users, autonomy boundary, read/write
boundary and critical constraints.

Never begin from the system prompt.

## Phase 2 — Domain Ontology

Generate `ontology.yaml`.

Define canonical entities, identifiers, aliases, relationships and business
invariants.

Use business semantics, not vendor API object names.

Bad:

```text
SalesforceAccount
DatadogMonitor
```

Good:

```text
Customer
Service
Incident
Security
Contract
```

## Phase 3 — Task Taxonomy

Generate `task-taxonomy.yaml`.

Classify tasks into:

```text
QUERY
ANALYZE
DECIDE
WRITE
LONG_RUNNING
MONITOR
REPORT
```

Each task defines:

- required entities;
- required capabilities;
- side effects;
- evidence requirements;
- completion criteria;
- risk class.

## Phase 4 — Capability Model

Generate semantic capabilities.

Naming convention:

```text
<domain>.<resource>.<action>
```

Examples:

```text
finance.filing.read
ops.incident.create
crm.customer.read
```

Agents and Skills depend on capabilities, never concrete vendor tools.

## Phase 5 — MCP Binding

Generate bindings separately:

```yaml
- capability: finance.filing.read
  implementation:
    protocol: mcp
    server: sec
    tool: filing_read
```

A capability may have multiple implementations.

## Phase 6 — Domain Skills

Generate 3-10 initial Domain Skills.

Every Skill must define:

```text
id
version
description
triggers
task_types
preconditions
inputs
outputs
required capabilities
procedure
validation
failure handling
completion criteria
policy metadata
```

A Skill must not:

- hardcode credentials;
- bypass Harness Policy;
- directly bind business logic to vendor tools;
- treat model inference as externally confirmed fact;
- create unbounded recursive delegation.

## Phase 7 — Workflow

Generate workflows for multi-step, high-value, side-effecting, approval-heavy,
long-running or evidence-heavy tasks.

Prefer:

```text
Deterministic Workflow Skeleton
+
Model Reasoning Nodes
```

over unconstrained Agent loops.

## Phase 8 — Policies

Generate layered policies:

```text
Global
Tenant
Domain
Agent
Task
Capability / Tool
```

Define:

- read/write boundaries;
- approvals;
- forbidden actions;
- data restrictions;
- confidence thresholds;
- evidence thresholds;
- escalation.

Lower-level policies may tighten but must not weaken higher-level policy.

## Phase 9 — Knowledge and Memory

Classify information into:

```text
Reference Knowledge
Operational Knowledge
Policy Knowledge
Historical Cases
Live State
```

Use RAG/Resources for stable knowledge and MCP Tools for live state.

Optionally define Entity Memory and Case Memory.

## Phase 10 — Output Contracts

Generate structured result schemas before UI rendering.

Recommended pattern:

```text
DomainResult
   ├── Chat Renderer
   ├── API Renderer
   ├── Report Renderer
   └── Dashboard Renderer
```

Where applicable distinguish:

```text
facts
claims
inferences
assumptions
evidence
uncertainty
actions
```

## Phase 11 — Evaluation

Generate Golden Evals for:

```text
Happy Path
Edge Case
Ambiguous Input
Insufficient Evidence
Conflicting Evidence
Tool Failure
Policy Boundary
Adversarial Input
Stale Data
```

Always measure:

```text
task completion
skill selection
capability selection
policy compliance
evidence quality
latency
cost
```

Add domain-specific KPIs.

## Phase 12 — Package Assembly

Produce:

```text
agents/<domain>/
domains/<domain>/
skills/<domain>/
capabilities/<domain>.yaml
mcp/bindings/<domain>.yaml
policies/<domain>/
evals/<domain>/
```

Return:

1. architecture summary;
2. generated asset list;
3. assumptions;
4. unresolved dependencies;
5. validation report;
6. implementation sequence.

# Maintenance Mode

When a package already exists, do not regenerate everything blindly.

Classify changes as PATCH / MINOR / MAJOR using semantic versioning.

## PATCH

Wording, validation fixes, non-contract bug fixes.

## MINOR

New optional task, Skill, provider, workflow branch or output field.

## MAJOR

Incompatible ontology, Skill contract, Capability semantics, task contract or
autonomy changes.

# Change Impact Analysis

Before changing anything, evaluate:

```text
Change
  ├── Ontology impact
  ├── Task impact
  ├── Skill impact
  ├── Capability impact
  ├── MCP binding impact
  ├── Policy impact
  ├── Schema impact
  └── Eval impact
```

Update affected assets together.

# Dependency Rules

Enforce:

```text
Agent
  -> Skill
  -> Capability
  -> Binding
  -> MCP Tool
```

And:

```text
Workflow
  -> Skills / Capabilities
```

Never allow:

```text
Agent -> Vendor Tool directly
Domain Skill -> Secret
LLM -> Policy bypass
```

# Validation Rules

A package is valid only when:

- every Agent references registered Skills;
- every Skill capability exists;
- every required capability has a valid binding or is marked unresolved;
- every write action has risk classification;
- every high-risk action has explicit approval policy;
- every workflow has completion and failure behavior;
- every structured output has a schema;
- every major task has Golden Evals;
- no Skill hardcodes secrets;
- no Agent directly binds concrete vendor MCP tools;
- version metadata exists.

# Batch Generation

When generating multiple domains:

1. preserve shared Core Skills;
2. deduplicate common capabilities;
3. reuse common MCP servers;
4. isolate Domain Skills;
5. isolate Domain Policies;
6. produce a compatibility matrix.

# Architecture Drift Audit

Check:

```text
No direct vendor coupling in Agents
No unregistered capability use
No orphan Skills
No unused MCP bindings
No Policy bypass
No undocumented write capability
No stale schema reference
No Eval gaps for major workflows
No duplicated canonical domain entities
```

# Completion Criteria

PASS only if:

- domain boundary is explicit;
- package can be generated deterministically;
- capability/tool separation is preserved;
- policy and eval coverage exist;
- maintenance impact can be traced;
- unresolved dependencies are listed.
