# ABOUTME: YAML frontmatter schema for solution files with enum values
# ABOUTME: Validates fields used in knowledge/solutions/ for grep-based retrieval

# Solution File YAML Schema

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Clear problem title |
| `project` | string (free-text) | Project name (e.g., my-api, web-app, cli-tool) |
| `date` | YYYY-MM-DD | When solved |
| `problem_type` | enum | Maps to category directory (see below) |
| `component` | enum | Technology/system involved (see below) |
| `symptoms` | string[] (1-5) | Observable symptoms, error messages |
| `solution_summary` | string | One-line summary of fix |
| `severity` | enum | critical, high, medium, low |

## Conditional Fields (Principles Only)

| Field | Type | Description |
|-------|------|-------------|
| `statement` | string | Concise, generalizable rule (1-2 sentences). Required when `problem_type: principles` |
| `confidence` | enum | high, medium, low — how validated the principle is. Required when `problem_type: principles` |

## Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `root_cause` | enum | What fundamentally caused it |
| `resolution_type` | enum | Type of fix applied |
| `tags` | string[] (max 8) | Freeform searchable keywords |
| `environment` | string | Runtime context (Python 3.12, K8s 1.28, etc.) |
| `related_solutions` | string[] (max 5) | Paths to related solution files. **Bidirectional**: if A links to B, B must link to A. Format: `category/filename.md` |

---

## `problem_type` Enum → Directory Mapping

| Value | Directory | When to Use |
|-------|-----------|-------------|
| `debugging` | `debugging/` | Service log failures, pods stuck, thread pool issues, error diagnosis |
| `infrastructure` | `infrastructure/` | ClusterIP routing, Docker storage, rate limits, networking |
| `patterns` | `patterns/` | Singleton dependency, extract-document-integrate, design approaches |
| `workflow` | `workflow/` | Scope creep, context loss, architecture evolution, process |
| `performance` | `performance/` | Slow startup, ARM slowness, N+1 queries, resource optimization |
| `security` | `security/` | Prisma scans, secrets management, ESO bootstrap, CVE remediation |
| `ci_cd` | `ci-cd/` | Helm publishing, GitOps promotion, Hadolint, pipeline issues |
| `configuration` | `configuration/` | Nested values, env var validation, MCP config, settings |
| `migration` | `migration/` | Unix socket→TCP, S6→K8s, legacy config extraction |
| `integration` | `integration/` | Cross-account Bedrock, metadata schemas, API compatibility |
| `principles` | `principles/` | Engineering wisdom, governing rules, validated best practices |

**Note**: `problem_type: ci_cd` maps to directory `ci-cd/` (underscore in YAML, hyphen in filesystem).

---

## `component` Enum

| Value | Description |
|-------|-------------|
| `api` | REST/GraphQL API endpoints |
| `database` | SQL/NoSQL databases, ORMs, migrations |
| `cache` | Redis, Memcached, caching layers |
| `queue` | Message queues, Kafka, RabbitMQ, Celery |
| `auth` | Authentication, authorization, OAuth, JWT |
| `frontend` | HTML, CSS, JavaScript, UI frameworks |
| `backend` | Server-side application logic |
| `cli` | Command-line tools and interfaces |
| `testing` | Test frameworks, fixtures, mocking |
| `deployment` | Fly.io, Heroku, Vercel, deployment targets |
| `monitoring` | Logging, metrics, alerting, observability |
| `networking` | DNS, routing, load balancing, firewalls |
| `storage` | File systems, object storage, S3 |
| `docker` | Docker containers and images |
| `kubernetes` | K8s clusters, pods, services, PVCs |
| `ci-cd-pipeline` | CI/CD pipelines, GitHub Actions, GitLab CI |
| `cloud-provider` | AWS, GCP, Azure services |
| `ai-ml` | LLMs, embeddings, vector stores, AI agents |
| `mcp` | Model Context Protocol servers |
| `claude-code` | Claude Code CLI, skills, plugins |
| `git` | Git version control |
| `general` | No specific technology |

Extend with project-specific values as needed. The enum is a starting vocabulary, not a constraint.

---

## `severity` Enum

| Value | Criteria |
|-------|----------|
| `critical` | Data loss risk, security vulnerability, production outage |
| `high` | Blocks development, affects multiple systems, hard to diagnose |
| `medium` | Significant time cost, non-obvious solution, likely to recur |
| `low` | Minor inconvenience, easy workaround exists |

---

## `root_cause` Enum

| Value | Description |
|-------|-------------|
| `missing_config` | Configuration not provided or incomplete |
| `wrong_api_usage` | API used incorrectly (wrong method, params, etc.) |
| `permission_issue` | Insufficient permissions or access controls |
| `resource_limit` | Rate limiting, memory, storage, or quota exceeded |
| `version_mismatch` | Incompatible versions of tools or dependencies |
| `network_issue` | Connectivity, DNS, routing, or firewall problems |
| `race_condition` | Timing-dependent failures |
| `data_format` | Wrong data format, encoding, or schema mismatch |
| `missing_dependency` | Required package, service, or resource not available |
| `logic_error` | Bug in application logic |
| `environment_mismatch` | Works in one environment but not another |
| `documentation_gap` | Documentation incorrect, missing, or misleading |

---

## `resolution_type` Enum

| Value | Description |
|-------|-------------|
| `code_fix` | Changed application source code |
| `config_change` | Modified configuration files or settings |
| `dependency_update` | Updated, added, or removed a dependency |
| `infrastructure_change` | Changed infrastructure (networking, storage, etc.) |
| `workflow_improvement` | Changed development or operational process |
| `workaround` | Temporary fix, not a root cause resolution |

---

## Validation Rules

1. All required fields must be present
2. `problem_type` must match a value in the enum table
3. `component` must match a value in the enum table
4. `severity` must be one of: critical, high, medium, low
5. `symptoms` must have 1-5 entries — **unless** `problem_type: principles` (symptoms not required for principles)
6. `tags` must have at most 8 entries
7. `date` must be in YYYY-MM-DD format
8. `root_cause` and `resolution_type` are optional but must match enum if provided
9. `related_solutions` paths must use `category/filename.md` format (relative to solutions directory root). Max 5 entries per file. Links must be bidirectional — when adding A→B, also add B→A
10. When `problem_type: principles`, `statement` and `confidence` are required; `confidence` must be one of: high, medium, low
