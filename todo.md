# Implementation Todo List: Mochi-Creator Test Suite

**Status:** Ready for Implementation
**Created:** 2025-11-13
**Plan ID:** fe2def8e
**Target Completion:** 6-10 working days

---

## Phase 1: Foundation (Tasks 1-5)

### Infrastructure Setup

- [ ] **TASK-001** – Create test directory structure
  - [ ] Create `tests/unit/` with `__init__.py`
  - [ ] Create `tests/integration/` with `__init__.py`
  - [ ] Create `tests/fixtures/` with `__init__.py`
  - [ ] Create `tests/__init__.py`
  - **Status:** Pending | **Complexity:** Simple | **Dependencies:** None

- [ ] **TASK-002** – Add test dependencies to pyproject.toml
  - [ ] Add pytest, pytest-cov, pytest-mock, responses, vcrpy
  - [ ] Define test optional-dependencies group
  - [ ] Verify `uv sync --extra test` works
  - **Status:** Pending | **Complexity:** Simple | **Dependencies:** TASK-001

- [ ] **TASK-003** – Create pytest.ini configuration
  - [ ] Configure test discovery paths
  - [ ] Define custom markers (unit, integration, slow)
  - [ ] Set coverage options (--cov, --cov-fail-under=95)
  - [ ] Enable HTML coverage report
  - **Status:** Pending | **Complexity:** Simple | **Dependencies:** TASK-002

- [ ] **TASK-004** – Create .coveragerc configuration
  - [ ] Set source to scripts/mochi_api.py
  - [ ] Add exclusions (CLI code, abstract methods)
  - [ ] Configure report formats (term, html, json)
  - [ ] Set 95% coverage threshold
  - **Status:** Pending | **Complexity:** Simple | **Dependencies:** TASK-003

- [ ] **TASK-005** – Create global tests/conftest.py
  - [ ] Create `mock_api_key` fixture
  - [ ] Create `api_instance` fixture
  - [ ] Create `vcr_config` fixture
  - [ ] Add fixture docstrings and type hints
  - **Status:** Pending | **Complexity:** Medium | **Dependencies:** TASK-002

---

## Phase 2: Test Data & Fixtures (Tasks 6-10)

### Shared Test Infrastructure

- [ ] **TASK-006** – Create tests/fixtures/mock_responses.py
  - [ ] Define MOCK_CARD_RESPONSE with all fields
  - [ ] Define MOCK_DECK_RESPONSE with all fields
  - [ ] Define MOCK_TEMPLATE_RESPONSE with all fields
  - [ ] Define error response formats
  - [ ] Verify responses are deep-copyable
  - **Status:** Pending | **Complexity:** Medium | **Dependencies:** TASK-005

- [ ] **TASK-007** – Create tests/fixtures/builders.py
  - [ ] Implement CardBuilder with fluent API
  - [ ] Implement DeckBuilder with fluent API
  - [ ] Implement TemplateBuilder
  - [ ] Add sensible defaults to builders
  - [ ] Support method chaining
  - **Status:** Pending | **Complexity:** Medium | **Dependencies:** TASK-005

- [ ] **TASK-008** – Create tests/fixtures/test_data.py
  - [ ] Create SAMPLE_CARDS list (3+ examples)
  - [ ] Create SAMPLE_DECKS list (2+ examples)
  - [ ] Create SAMPLE_TEMPLATES list (2+ examples)
  - [ ] Verify all data matches API specification
  - **Status:** Pending | **Complexity:** Simple | **Dependencies:** TASK-006

- [ ] **TASK-009** – Create tests/unit/conftest.py
  - [ ] Create `mock_card_response` fixture
  - [ ] Create `mock_deck_response` fixture
  - [ ] Create `card_builder` fixture
  - [ ] Create `deck_builder` fixture
  - [ ] Ensure fixtures are function-scoped
  - **Status:** Pending | **Complexity:** Medium | **Dependencies:** TASK-006, TASK-007

- [ ] **TASK-010** – Create tests/integration/conftest.py
  - [ ] Configure VCR with cassette directory
  - [ ] Create `integration_api` fixture (module-scoped)
  - [ ] Create `test_deck` fixture with cleanup
  - [ ] Create `cleanup_cards` fixture for tracking
  - [ ] Implement auto-cleanup with autouse=True
  - **Status:** Pending | **Complexity:** Medium | **Dependencies:** TASK-005

---

## Phase 3: Unit Tests - API Operations (Tasks 11-16)

### API Authentication & Operations

- [ ] **TASK-011** – Write tests/unit/test_authentication.py
  - [ ] Test: API key from MOCHI_API_KEY env var
  - [ ] Test: Missing API key raises error
  - [ ] Test: API key parameter overrides env var
  - [ ] Test: Empty string API key raises error
  - [ ] Test: Auth header construction (Basic prefix)
  - [ ] Test: API key as first argument in Basic auth
  - **Status:** Pending | **Complexity:** Medium | **Dependencies:** TASK-009

- [ ] **TASK-012** – Write tests/unit/test_api_operations.py (Deck Operations)
  - [ ] Test: `list_decks()` returns list
  - [ ] Test: `list_decks()` handles pagination
  - [ ] Test: `create_deck(name)` succeeds
  - [ ] Test: `create_deck()` with parent_id creates subdeck
  - [ ] Test: `get_deck()` returns deck data
  - [ ] Test: `update_deck()` modifies properties
  - [ ] Test: `delete_deck()` sends DELETE request
  - [ ] Test: Field name transformation (snake_case → kebab-case)
  - **Status:** Pending | **Complexity:** Large | **Dependencies:** TASK-009

- [ ] **TASK-013** – Write tests/unit/test_api_operations.py (Card Operations)
  - [ ] Test: `list_cards()` returns paginated list
  - [ ] Test: `list_cards()` filters by deck_id
  - [ ] Test: `create_card(content, deck_id)` creates simple card
  - [ ] Test: `create_card()` with template_id and fields
  - [ ] Test: `get_card()` returns card data
  - [ ] Test: `update_card()` modifies content
  - [ ] Test: `update_card()` with trashed field soft-deletes
  - [ ] Test: `delete_card()` hard-deletes (204 No Content)
  - [ ] Test: Boolean field transformation (bool → bool?)
  - **Status:** Pending | **Complexity:** Large | **Dependencies:** TASK-009

- [ ] **TASK-014** – Write tests/unit/test_api_operations.py (Template Operations)
  - [ ] Test: `list_templates()` returns template list
  - [ ] Test: `create_template(name, content, fields)` succeeds
  - [ ] Test: Template field structure preserved in request
  - [ ] Test: `get_template()` returns template data
  - [ ] Test: `update_template()` modifies template
  - [ ] Test: Field validation in template creation
  - **Status:** Pending | **Complexity:** Large | **Dependencies:** TASK-009

- [ ] **TASK-015** – Write tests/unit/test_api_operations.py (Omitted Cards)
  - [ ] Test: `list_omitted_cards()` operation (if implemented)
  - [ ] Test: Correct endpoint and parameters
  - **Status:** Pending | **Complexity:** Simple | **Dependencies:** TASK-009

- [ ] **TASK-016** – Write tests/unit/test_error_handling.py
  - [ ] Test: HTTP 400 raises MochiAPIError
  - [ ] Test: HTTP 401 raises MochiAPIError
  - [ ] Test: HTTP 404 raises MochiAPIError with message
  - [ ] Test: HTTP 500 raises MochiAPIError
  - [ ] Test: Network timeout raises MochiAPIError
  - [ ] Test: Connection refused raises MochiAPIError
  - [ ] Test: Invalid JSON response raises MochiAPIError
  - [ ] Test: Error message includes HTTP status
  - [ ] Test: Field-level errors in error message
  - **Status:** Pending | **Complexity:** Medium | **Dependencies:** TASK-009

---

## Phase 4: Unit Tests - Validation & Helpers (Tasks 17-21)

### Validation Logic & Helper Functions

- [ ] **TASK-017** – Write tests/unit/test_validation.py (Prompt Quality)
  - [ ] Test: Focused validation (detects " and ", commas)
  - [ ] Test: Precise validation (detects vague words)
  - [ ] Test: Consistent validation (detects variable prompts)
  - [ ] Test: Binary validation (detects yes/no questions)
  - [ ] Test: Pattern-matchable validation (question length)
  - [ ] Test: Trivial validation (detects trivial indicators)
  - [ ] Test: Valid prompt returns valid=true
  - [ ] Test: Invalid prompt returns issues and suggestions
  - [ ] Test: Strict mode raises PromptQualityError
  - [ ] Test: Non-strict mode returns dict with issues
  - **Status:** Pending | **Complexity:** Medium | **Dependencies:** TASK-009

- [ ] **TASK-018** – Write tests/unit/test_validation.py (Atomic Prompts)
  - [ ] Test: Complex prompt broken into atomic prompts
  - [ ] Test: Each atomic prompt is more focused
  - [ ] Test: Returns list of dicts with 'question' and 'answer'
  - [ ] Test: Handles empty input gracefully
  - [ ] Test: Preserves original answer content
  - **Status:** Pending | **Complexity:** Medium | **Dependencies:** TASK-009

- [ ] **TASK-019** – Refactor helper functions for dependency injection
  - [ ] Modify `create_procedural_cards()` to accept optional `api` parameter
  - [ ] Modify `create_conceptual_lens_cards()` to accept optional `api` parameter
  - [ ] Maintain backward compatibility (create new instance if not provided)
  - [ ] Verify no breaking changes to existing usage
  - **Status:** Pending | **Complexity:** Medium | **Dependencies:** None (code change)

- [ ] **TASK-020** – Write tests/unit/test_helpers.py (Procedural Cards)
  - [ ] Test: Creates cards for transitions
  - [ ] Test: Creates cards for rationales
  - [ ] Test: Creates cards for timing
  - [ ] Test: All cards have correct deck_id
  - [ ] Test: All cards have base_tags
  - [ ] Test: API errors are propagated
  - [ ] Test: Works with mocked MochiAPI instance
  - **Status:** Pending | **Complexity:** Large | **Dependencies:** TASK-019, TASK-009

- [ ] **TASK-021** – Write tests/unit/test_helpers.py (Conceptual Lens Cards)
  - [ ] Test: Creates 5 cards (one per lens)
  - [ ] Test: Cards for: attributes, similarities, parts, causes, significance
  - [ ] Test: All cards have correct deck_id and base_tags
  - [ ] Test: API errors are propagated
  - [ ] Test: Works with mocked MochiAPI instance
  - **Status:** Pending | **Complexity:** Large | **Dependencies:** TASK-019, TASK-009

---

## Phase 5: Integration Tests & CI/CD (Tasks 22-29)

### End-to-End Workflows & Automation

- [ ] **TASK-022** – Write tests/integration/test_card_workflows.py
  - [ ] Test: Create simple card workflow
  - [ ] Test: Create template-based card workflow
  - [ ] Test: Update card content
  - [ ] Test: Soft delete (trashed field)
  - [ ] Test: Hard delete (permanent)
  - [ ] Test: Card is retrievable after creation
  - [ ] Test: Soft deleted card marked as trashed
  - [ ] All tests use VCR cassettes
  - **Status:** Pending | **Complexity:** Large | **Dependencies:** TASK-010

- [ ] **TASK-023** – Write tests/integration/test_deck_workflows.py
  - [ ] Test: Create deck workflow
  - [ ] Test: Create subdeck with parent_id
  - [ ] Test: List cards in deck
  - [ ] Test: Pagination with bookmark
  - [ ] Test: Archive deck (soft delete)
  - [ ] Test: Deck hierarchy preserved
  - [ ] All tests use VCR cassettes
  - **Status:** Pending | **Complexity:** Large | **Dependencies:** TASK-010

- [ ] **TASK-024** – Write tests/integration/test_template_workflows.py
  - [ ] Test: Create template workflow
  - [ ] Test: Create card using template
  - [ ] Test: Update card with template fields
  - [ ] Test: Template field structure preserved
  - [ ] All tests use VCR cassettes
  - **Status:** Pending | **Complexity:** Large | **Dependencies:** TASK-010

- [ ] **TASK-025** – Record VCR cassettes for all integration tests
  - [ ] Set MOCHI_API_KEY environment variable with real key
  - [ ] Run: `pytest tests/integration -m integration`
  - [ ] Verify cassette files created in correct directories
  - [ ] Verify YAML cassette format
  - [ ] Verify authorization headers redacted
  - [ ] Test cassette playback (rerun tests)
  - [ ] Commit cassette files to version control
  - **Status:** Pending | **Complexity:** Medium | **Dependencies:** TASK-022, TASK-023, TASK-024

- [ ] **TASK-026** – Create .github/workflows/test.yml
  - [ ] Create GitHub Actions workflow file
  - [ ] Configure runs on: push to main, pull_request
  - [ ] Test against Python 3.10, 3.11, 3.12
  - [ ] Run unit tests on every push (mock API key)
  - [ ] Run integration tests on main push only (real API key secret)
  - [ ] Upload coverage to Codecov
  - [ ] Fail if coverage < 95%
  - **Status:** Pending | **Complexity:** Medium | **Dependencies:** TASK-003

- [ ] **TASK-027** – Set up Codecov integration and badge
  - [ ] Connect repository to Codecov
  - [ ] Configure Codecov action in workflow
  - [ ] Create coverage badge markdown
  - [ ] Add badge to plugin README
  - [ ] Verify badge shows current coverage %
  - **Status:** Pending | **Complexity:** Simple | **Dependencies:** TASK-026

- [ ] **TASK-028** – Add test architecture documentation to plugin README
  - [ ] Add "Testing" section to README
  - [ ] Document how to run unit tests
  - [ ] Document how to run integration tests
  - [ ] Explain unit vs integration test purpose
  - [ ] Show how to write new tests (example)
  - [ ] Link to test architecture details
  - [ ] Show coverage goals (95%+)
  - **Status:** Pending | **Complexity:** Simple | **Dependencies:** TASK-027

- [ ] **TASK-029** – Validate 95%+ coverage target achieved
  - [ ] Run full test suite: `pytest --cov`
  - [ ] Verify overall coverage >= 95%
  - [ ] Verify API operations coverage = 100%
  - [ ] Verify helper functions coverage >= 95%
  - [ ] Generate HTML coverage report
  - [ ] Verify CI/CD shows green checkmark
  - [ ] Verify no coverage degradation from baseline
  - **Status:** Pending | **Complexity:** Simple | **Dependencies:** TASK-021, TASK-024

---

## Phase Completion Status

### Phase 1: Foundation
**Status:** ⏳ Pending
**Progress:** 0/5 tasks
**Estimated Duration:** 1-2 hours

- [ ] TASK-001
- [ ] TASK-002
- [ ] TASK-003
- [ ] TASK-004
- [ ] TASK-005

### Phase 2: Test Data & Fixtures
**Status:** ⏳ Pending (Blocked on Phase 1)
**Progress:** 0/5 tasks
**Estimated Duration:** 2-3 hours

- [ ] TASK-006
- [ ] TASK-007
- [ ] TASK-008
- [ ] TASK-009
- [ ] TASK-010

### Phase 3: Unit Tests - API Operations
**Status:** ⏳ Pending (Blocked on Phase 2)
**Progress:** 0/6 tasks
**Estimated Duration:** 3-4 hours

- [ ] TASK-011
- [ ] TASK-012
- [ ] TASK-013
- [ ] TASK-014
- [ ] TASK-015
- [ ] TASK-016

### Phase 4: Unit Tests - Validation & Helpers
**Status:** ⏳ Pending (Blocked on Phase 2)
**Progress:** 0/5 tasks
**Estimated Duration:** 2-3 hours

- [ ] TASK-017
- [ ] TASK-018
- [ ] TASK-019
- [ ] TASK-020
- [ ] TASK-021

### Phase 5: Integration Tests & CI/CD
**Status:** ⏳ Pending (Blocked on Phase 2)
**Progress:** 0/8 tasks
**Estimated Duration:** 2-3 hours

- [ ] TASK-022
- [ ] TASK-023
- [ ] TASK-024
- [ ] TASK-025
- [ ] TASK-026
- [ ] TASK-027
- [ ] TASK-028
- [ ] TASK-029

---

## Parallel Execution Opportunities

**After Phase 1 Complete:**
- TASK-006, TASK-007, TASK-008 can run in parallel

**After TASK-006-008 Complete:**
- TASK-009, TASK-010 can run in parallel

**After TASK-009, TASK-010 Complete:**
- TASK-011 through TASK-024 can run in parallel (in their groups)
  - TASK-011 through TASK-018 (unit tests) - independent
  - TASK-020, TASK-021 (after TASK-019 code change)
  - TASK-022, TASK-023, TASK-024 (integration tests) - independent

**After TASK-022, TASK-023, TASK-024 Complete:**
- TASK-025 (Record cassettes) - must run sequentially after tests written

**After TASK-025 Complete:**
- TASK-026, TASK-027, TASK-028 can run in parallel

**Final Phase:**
- TASK-029 (Validate coverage) - must run last

---

## Dependency Graph

```
TASK-001 ──┐
           ├─ TASK-002 ─┐
TASK-003 ──┤           ├─ TASK-005 ─┬─ TASK-009
TASK-004 ──┘           │            │
                       └─ TASK-010 ─┤
                                    ├─ TASK-011
                                    ├─ TASK-012
                 ┌───────────────────┤─ TASK-013
    TASK-006 ─┬─┤                   ├─ TASK-014
    TASK-007 ─┤ TASK-009            ├─ TASK-015
    TASK-008 ─┴─┤                   ├─ TASK-016
               TASK-010            ├─ TASK-017
                                    ├─ TASK-018
    TASK-019 ──┐                    ├─ TASK-020
               ├─ TASK-010          ├─ TASK-021
               │                    ├─ TASK-022
               │                    ├─ TASK-023
               │                    ├─ TASK-024
               └─ TASK-020          │
                                    ├─ TASK-025
    TASK-025 ──┐                    │
               ├─ TASK-026          │
               ├─ TASK-027 ─────────┤
               ├─ TASK-028          │
               │                    │
               └────────────────────┼─ TASK-029
                                    │
```

---

## Overall Progress Metrics

**Total Tasks:** 29
**Tasks Completed:** 0
**Tasks In Progress:** 0
**Tasks Pending:** 29
**Tasks Blocked:** 24

**Completion %:** 0% (0/29)

**Estimated Time Remaining:** 6-10 working days

---

## Key Milestones

1. ✅ **Specification Complete** (Phase 0 - Planning)
   - Investigation findings: 3,231 lines analyzed
   - Architecture designed: 3-tier system defined
   - Task breakdown: 29 GitHub-issue-sized tasks

2. ⏳ **Foundation Established** (Phase 1)
   - All configuration files created
   - Test infrastructure ready

3. ⏳ **Test Fixtures Ready** (Phase 2)
   - Mock responses available
   - Builders and test data ready

4. ⏳ **Unit Tests Complete** (Phases 3-4)
   - All API operations tested
   - All error conditions covered
   - All helper functions tested
   - 95%+ code coverage achieved

5. ⏳ **Integration Tests Complete** (Phase 5)
   - VCR cassettes recorded
   - End-to-end workflows verified

6. ⏳ **CI/CD Live** (Phase 5)
   - GitHub Actions workflow running
   - Codecov integration active
   - Coverage badge displayed

7. ⏳ **Documentation Complete** (Phase 5)
   - README updated
   - Test architecture documented

8. ⏳ **Final Validation** (Phase 5)
   - Coverage metrics verified
   - All tests passing
   - Ready for production use

---

## Success Criteria Checklist

Upon completion, verify:

- [ ] Overall code coverage: >= 95%
- [ ] API operations coverage: 100%
- [ ] Helper functions coverage: >= 95%
- [ ] Error handling coverage: >= 95%
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] No test order dependencies (tests run in random order)
- [ ] CI/CD pipeline green
- [ ] Coverage badge visible in README
- [ ] Documentation comprehensive and current
- [ ] Performance acceptable (unit tests < 10s, integration < 30s)
- [ ] No flaky tests

---

## Notes & Observations

**La Boeuf**, this todo list represents a production-grade test suite implementation plan. Key observations:

1. **Well-Scoped Tasks**: Each task is independent, measurable, and completable in 30-90 minutes
2. **Clear Dependencies**: Task execution order is explicit (can parallelize intelligently)
3. **Comprehensive Coverage**: All critical paths, edge cases, and error conditions covered
4. **Maintainable**: Tests use reusable fixtures, builders, and clear organization
5. **Tooling**: Using standard tools (pytest, responses, vcrpy) - no custom test framework
6. **TDD-First**: Tests written before implementation (failing tests define requirements)

**Recommended Execution Strategy:**
1. Start with Phase 1 (Foundation) - unblocks everything
2. Do Phase 2 (Fixtures) in parallel with Phase 1 final tasks
3. Parallelize Phase 3 & 4 unit tests (independent operations)
4. Do integration tests after fixtures solidify
5. Record cassettes once tests are passing
6. Set up CI/CD to ensure regression prevention

**Critical Success Factors:**
- Maintain TDD discipline (test → implementation → refactor)
- Keep fixture code simple and reusable
- Don't skip edge case testing
- Regularly commit progress (one task = one commit)
- Run full test suite after each phase completes

Ready to begin, La Boeuf?

---

**Last Updated:** 2025-11-13
**Plan Version:** 1.0
**Status:** Ready for Implementation
