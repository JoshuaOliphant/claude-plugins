# TDD Implementation Plan: Comprehensive Test Suite for Mochi-Creator Plugin

**Created:** 2025-11-13
**Task ID:** fe2def8e
**Objective:** Add comprehensive test suite for the mochi-creator plugin using Test-Driven Development

---

## Executive Summary

This plan decomposes the test suite implementation into **29 GitHub-issue-sized tasks** organized across 5 phases:

1. **Foundation** (5 tasks): Test infrastructure, configuration, fixtures
2. **Test Data** (5 tasks): Mock responses, builders, shared test data
3. **Unit Tests - API** (6 tasks): Authentication, operations, error handling
4. **Unit Tests - Helpers** (5 tasks): Validation, helper functions, refactoring
5. **Integration Tests & CI/CD** (8 tasks): Workflows, cassettes, CI/CD pipeline

**Total Effort:** 6-10 working days
**Target Coverage:** 95%+ with 100% for critical paths
**Complexity:** Medium-High (15 API operations + 4 helper functions + error handling)

---

## Architecture Overview

### Three-Tier Testing System

```
┌─────────────────────────────────────────┐
│  Unit Tests (mocked HTTP)               │ ← Fast, isolated, run always
│  • 15 API operations                    │
│  • Authentication                       │
│  • Error handling                       │
│  • Helper functions (mocked)            │
│  • Validation logic                     │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  Integration Tests (VCR cassettes)      │ ← Real workflows, recorded
│  • Card creation workflows              │
│  • Deck organization                    │
│  • Template-based cards                 │
│  • Pagination handling                  │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  CI/CD Pipeline (GitHub Actions)        │ ← Automated quality gates
│  • Unit + integration tests              │
│  • Coverage reporting                   │
│  • Multiple Python versions             │
└─────────────────────────────────────────┘
```

### Directory Structure

```
plugins/mochi-creator/
├── pyproject.toml                    # Dependencies: pytest, responses, vcrpy
├── pytest.ini                        # Test configuration and markers
├── .coveragerc                       # Coverage exclusions
├── scripts/
│   └── mochi_api.py                  # Code under test (15 APIs + 4 helpers)
├── tests/
│   ├── conftest.py                   # Global fixtures
│   ├── unit/
│   │   ├── conftest.py               # Unit-specific fixtures (mocks)
│   │   ├── test_authentication.py    # API key handling
│   │   ├── test_api_operations.py    # All 15 CRUD operations
│   │   ├── test_error_handling.py    # HTTP + network errors
│   │   ├── test_helpers.py           # Helper functions (mocked API)
│   │   └── test_validation.py        # Prompt quality validation
│   ├── integration/
│   │   ├── conftest.py               # VCR configuration
│   │   ├── test_card_workflows.py    # Card CRUD workflows
│   │   ├── test_deck_workflows.py    # Deck operations
│   │   ├── test_template_workflows.py # Template-based cards
│   │   └── cassettes/                # VCR recording files
│   └── fixtures/
│       ├── mock_responses.py         # Sample API responses
│       ├── builders.py               # Test data builders (fluent API)
│       └── test_data.py              # Sample cards/decks/templates
└── .github/
    └── workflows/
        └── test.yml                  # GitHub Actions CI/CD
```

---

## Phase 1: Foundation (Tasks 1-5)

### Purpose
Set up test infrastructure, configuration, and base fixtures.

### Tasks

#### TASK-001: Create test directory structure
**Complexity:** S (Simple)
**Dependencies:** None
**Description:** Create directory hierarchy for tests.

**Acceptance Criteria:**
- [ ] `tests/unit/` directory created with `__init__.py`
- [ ] `tests/integration/` directory created with `__init__.py`
- [ ] `tests/fixtures/` directory created with `__init__.py`
- [ ] `tests/__init__.py` created (root test module)

**Test Code (Verify via filesystem inspection):**
```python
# Verify directory structure (run before implementation)
import os
assert os.path.isdir("tests/unit")
assert os.path.isdir("tests/integration")
assert os.path.isdir("tests/fixtures")
```

---

#### TASK-002: Add test dependencies to pyproject.toml
**Complexity:** S
**Dependencies:** TASK-001
**Description:** Configure test dependencies and test command.

**Acceptance Criteria:**
- [ ] `pytest>=7.4.0` added to optional dependencies
- [ ] `pytest-cov>=4.1.0` added for coverage reporting
- [ ] `pytest-mock>=3.11.1` added for mocking
- [ ] `responses>=0.23.0` added for HTTP mocking
- [ ] `vcrpy>=5.1.0` added for request recording
- [ ] `pyproject.toml` has test extra defined
- [ ] Can run `uv sync --extra test` successfully

**Test Code:**
```python
# Verify dependencies can be imported
import pytest
import responses
import vcr
import pytest_mock

# Verify pyproject.toml structure
import tomllib
with open("pyproject.toml", "rb") as f:
    config = tomllib.load(f)
    assert "test" in config["project"].get("optional-dependencies", {})
```

---

#### TASK-003: Create pytest.ini configuration
**Complexity:** S
**Dependencies:** TASK-002
**Description:** Configure pytest with test discovery, markers, coverage settings.

**Acceptance Criteria:**
- [ ] `pytest.ini` created in plugin root directory
- [ ] Test discovery configured (`testpaths = ["tests"]`)
- [ ] Custom markers defined: `unit`, `integration`, `slow`
- [ ] Coverage options configured: `--cov=scripts.mochi_api`, `--cov-fail-under=95`
- [ ] HTML coverage report configured
- [ ] Running `pytest --help` shows custom markers

**Test Code:**
```python
# Verify pytest.ini configuration
import configparser
config = configparser.ConfigParser()
config.read("pytest.ini")
assert config["pytest"]["testpaths"] == "tests"
assert "unit" in config["pytest"]["markers"]
assert "coverage" in config["pytest"]["addopts"]
```

---

#### TASK-004: Create .coveragerc configuration
**Complexity:** S
**Dependencies:** TASK-003
**Description:** Configure coverage reporting and exclusions.

**Acceptance Criteria:**
- [ ] `.coveragerc` created in plugin root
- [ ] `source = scripts/mochi_api.py` configured
- [ ] CLI code excluded (`if __name__ == "__main__":`)
- [ ] Abstract methods excluded
- [ ] Coverage reports include term, html, and json formats
- [ ] Coverage threshold set to 95%

**Test Code:**
```python
# Verify .coveragerc content
import configparser
config = configparser.ConfigParser()
config.read(".coveragerc")
assert config["run"]["source"] == "scripts/mochi_api.py"
assert "if __name__" in config["report"]["exclude_lines"]
```

---

#### TASK-005: Create global tests/conftest.py with base fixtures
**Complexity:** M (Medium)
**Dependencies:** TASK-002
**Description:** Create pytest fixtures available to all tests (API instances, environment setup).

**Acceptance Criteria:**
- [ ] `tests/conftest.py` created
- [ ] `mock_api_key` fixture sets `MOCHI_API_KEY` environment variable
- [ ] `api_instance` fixture provides configured `MochiAPI()` instance
- [ ] `vcr_config` fixture provides VCR configuration dict
- [ ] Fixtures are function-scoped where appropriate
- [ ] Docstrings explain fixture purposes
- [ ] All fixtures can be imported by test modules

**Test Code (TDD - Write First):**
```python
import pytest
from scripts.mochi_api import MochiAPI

def test_mock_api_key_fixture_sets_env(mock_api_key):
    """Verify mock_api_key fixture sets MOCHI_API_KEY."""
    import os
    assert os.getenv("MOCHI_API_KEY") == "test_key_12345"

def test_api_instance_fixture_provides_mochi_api(api_instance):
    """Verify api_instance fixture returns MochiAPI."""
    assert isinstance(api_instance, MochiAPI)

def test_vcr_config_fixture_has_required_keys(vcr_config):
    """Verify vcr_config has all required configuration."""
    assert "cassette_library_dir" in vcr_config
    assert "record_mode" in vcr_config
    assert "filter_headers" in vcr_config
```

**Implementation Pattern:**
```python
# tests/conftest.py
import pytest
import os
from scripts.mochi_api import MochiAPI

@pytest.fixture
def mock_api_key(monkeypatch):
    """Sets MOCHI_API_KEY for tests."""
    monkeypatch.setenv("MOCHI_API_KEY", "test_key_12345")
    return "test_key_12345"

@pytest.fixture
def api_instance(mock_api_key):
    """Provides MochiAPI instance with mocked key."""
    return MochiAPI()

@pytest.fixture(scope="session")
def vcr_config():
    """VCR configuration for integration tests."""
    return {
        "cassette_library_dir": "tests/integration/cassettes",
        "record_mode": "once",
        "match_on": ["uri", "method", "body"],
        "filter_headers": ["authorization"],
    }
```

---

## Phase 2: Test Data & Fixtures (Tasks 6-10)

### Purpose
Create reusable test data, mock responses, and fixture infrastructure.

### Tasks

#### TASK-006: Create tests/fixtures/mock_responses.py
**Complexity:** M
**Dependencies:** TASK-005
**Description:** Create realistic mock API responses for all operations.

**Acceptance Criteria:**
- [ ] Mock responses for all 15 API operations included
- [ ] Responses match real API structure (from SKILL.md documentation)
- [ ] Deck, card, and template responses include all fields
- [ ] Error responses include both field-level and general error formats
- [ ] Module can be imported: `from tests.fixtures.mock_responses import ...`
- [ ] Responses are deep-copyable (use dicts, not objects)

**Test Code (TDD):**
```python
from tests.fixtures.mock_responses import (
    MOCK_CARD_RESPONSE,
    MOCK_DECK_RESPONSE,
    MOCK_TEMPLATE_RESPONSE,
    MOCK_ERROR_RESPONSE
)

def test_mock_card_response_has_required_fields():
    """Card response includes all documented fields."""
    card = MOCK_CARD_RESPONSE
    assert "id" in card
    assert "content" in card
    assert "deck-id" in card

def test_mock_responses_are_copyable():
    """Mock responses can be deep-copied without side effects."""
    import copy
    card = copy.deepcopy(MOCK_CARD_RESPONSE)
    card["id"] = "modified"
    assert MOCK_CARD_RESPONSE["id"] != "modified"
```

**Implementation Pattern (Sample):**
```python
# tests/fixtures/mock_responses.py
MOCK_CARD_RESPONSE = {
    "id": "card-uuid-123",
    "content": "# What is Python?\n---\nA programming language",
    "deck-id": "deck-uuid-123",
    "template-id": None,
    "fields": None,
    "archived?": False,
    "trashed?": None,
    "review-reverse?": False,
    "pos": 0,
    "manual-tags": ["python"],
    "created-at": "2025-01-01T00:00:00Z",
    "updated-at": "2025-01-01T00:00:00Z"
}

MOCK_DECK_RESPONSE = {
    "id": "deck-uuid-123",
    "name": "Python Basics",
    "parent-id": None,
    "archived?": False,
    "trashed?": None,
    "cards": 42,
    # ... more fields
}

# ... responses for all 15 operations
```

---

#### TASK-007: Create tests/fixtures/builders.py
**Complexity:** M
**Dependencies:** TASK-005
**Description:** Create fluent builder classes for generating test data.

**Acceptance Criteria:**
- [ ] `CardBuilder` class with fluent API (with_content, with_deck, with_tags, build)
- [ ] `DeckBuilder` class with fluent API (with_name, with_parent, with_archived, build)
- [ ] `TemplateBuilder` class for creating template test data
- [ ] All builders return dicts suitable for API calls
- [ ] Builders have sensible defaults
- [ ] Builders can be imported: `from tests.fixtures.builders import CardBuilder`

**Test Code (TDD):**
```python
from tests.fixtures.builders import CardBuilder, DeckBuilder

def test_card_builder_default_build():
    """CardBuilder with no customization builds valid card."""
    card = CardBuilder().build()
    assert "content" in card
    assert "deck_id" in card

def test_card_builder_fluent_api():
    """CardBuilder supports method chaining."""
    card = (CardBuilder()
            .with_content("# Q\n---\nA")
            .with_deck("deck123")
            .with_tags("python", "advanced")
            .build())

    assert card["content"] == "# Q\n---\nA"
    assert card["deck_id"] == "deck123"
    assert card["manual_tags"] == ["python", "advanced"]

def test_builders_create_independent_copies():
    """Multiple builds don't share state."""
    builder = CardBuilder()
    card1 = builder.with_deck("deck1").build()
    card2 = builder.with_deck("deck2").build()
    assert card1["deck_id"] == "deck1"
    assert card2["deck_id"] == "deck2"
```

**Implementation Pattern:**
```python
# tests/fixtures/builders.py
from typing import Optional, Dict, List

class CardBuilder:
    """Builder for test card data."""

    def __init__(self):
        self.content = "# Default Question\n---\nDefault Answer"
        self.deck_id = "deck123"
        self.template_id = None
        self.manual_tags = []

    def with_content(self, content: str):
        """Set card content."""
        self.content = content
        return self

    def with_deck(self, deck_id: str):
        """Set deck ID."""
        self.deck_id = deck_id
        return self

    def with_tags(self, *tags):
        """Set manual tags."""
        self.manual_tags = list(tags)
        return self

    def build(self) -> dict:
        """Build and return card dict."""
        return {
            "content": self.content,
            "deck_id": self.deck_id,
            "template_id": self.template_id,
            "manual_tags": self.manual_tags
        }
```

---

#### TASK-008: Create tests/fixtures/test_data.py
**Complexity:** S
**Dependencies:** TASK-006
**Description:** Pre-built sample test data (cards, decks, templates).

**Acceptance Criteria:**
- [ ] `SAMPLE_CARDS` list with 3+ example cards (various formats)
- [ ] `SAMPLE_DECKS` list with 2+ example decks (including hierarchies)
- [ ] `SAMPLE_TEMPLATES` list with 2+ example templates
- [ ] All data structures valid per API specification
- [ ] Can be imported: `from tests.fixtures.test_data import SAMPLE_CARDS`

**Test Code (TDD):**
```python
from tests.fixtures.test_data import SAMPLE_CARDS, SAMPLE_DECKS, SAMPLE_TEMPLATES

def test_sample_cards_valid():
    """All sample cards have required structure."""
    assert len(SAMPLE_CARDS) >= 3
    for card in SAMPLE_CARDS:
        assert "content" in card
        assert "---" in card["content"]

def test_sample_decks_valid():
    """All sample decks have required fields."""
    assert len(SAMPLE_DECKS) >= 2
    for deck in SAMPLE_DECKS:
        assert "name" in deck
```

---

#### TASK-009: Create tests/unit/conftest.py
**Complexity:** M
**Dependencies:** TASK-006, TASK-007
**Description:** Unit test-specific fixtures for HTTP mocking and test data.

**Acceptance Criteria:**
- [ ] `mock_card_response` fixture provides clean MOCK_CARD_RESPONSE copy
- [ ] `mock_deck_response` fixture provides clean MOCK_DECK_RESPONSE copy
- [ ] `card_builder` fixture provides CardBuilder instance
- [ ] `deck_builder` fixture provides DeckBuilder instance
- [ ] `responses_mock` fixture activates @responses.activate
- [ ] Fixtures don't interfere with each other

**Test Code (TDD):**
```python
def test_mock_responses_are_fresh(mock_card_response):
    """Each call gets fresh copy."""
    mock_card_response["id"] = "modified"
    # Next test shouldn't see this modification

def test_builders_available(card_builder, deck_builder):
    """Builders are available in unit tests."""
    card = card_builder.with_deck("test").build()
    deck = deck_builder.with_name("test").build()
    assert card["deck_id"] == "test"
    assert deck["name"] == "test"
```

---

#### TASK-010: Create tests/integration/conftest.py
**Complexity:** M
**Dependencies:** TASK-005
**Description:** Integration test fixtures for VCR configuration and test cleanup.

**Acceptance Criteria:**
- [ ] VCR configuration applied (cassette directory, record mode, filtering)
- [ ] `integration_api` fixture provides real MochiAPI instance
- [ ] `test_deck` fixture creates and cleans up test deck
- [ ] `cleanup_cards` fixture tracks created cards for deletion
- [ ] Cleanup happens after each test automatically
- [ ] VCR cassettes saved to correct directory

**Test Code (TDD):**
```python
import vcr

@pytest.mark.integration
@vcr.use_cassette("tests/integration/cassettes/test_example.yaml")
def test_vcr_cassette_created(integration_api):
    """VCR cassette file is created after test runs."""
    # Test implementation
    assert True
    # Afterward, cassettes/test_example.yaml should exist

def test_cleanup_after_integration_test(integration_api, test_deck):
    """Test deck is cleaned up after test."""
    assert test_deck["id"]
    # After test, deck should be archived
```

---

## Phase 3: Unit Tests - API Operations (Tasks 11-16)

### Purpose
Test all 15 API operations with mocked HTTP requests.

### Tasks

#### TASK-011: Write tests/unit/test_authentication.py
**Complexity:** M
**Dependencies:** TASK-009
**Description:** Test API key handling and authentication header construction.

**Acceptance Criteria:**
- [ ] Test: API key from MOCHI_API_KEY env var loads successfully
- [ ] Test: Missing API key raises MochiAPIError with clear message
- [ ] Test: API key precedence (parameter > env var)
- [ ] Test: Empty string API key raises error
- [ ] Test: Authentication header includes "Basic" prefix
- [ ] Test: API key is first argument in Basic auth (no password)

**Test Code (TDD - Write These First):**
```python
import pytest
from scripts.mochi_api import MochiAPI, MochiAPIError

def test_api_key_from_environment(mock_api_key):
    """MochiAPI loads API key from MOCHI_API_KEY env var."""
    api = MochiAPI()
    assert api.api_key == "test_key_12345"

def test_missing_api_key_raises_error(monkeypatch):
    """MochiAPIError raised when MOCHI_API_KEY not set."""
    monkeypatch.delenv("MOCHI_API_KEY", raising=False)

    with pytest.raises(MochiAPIError, match="MOCHI_API_KEY"):
        MochiAPI()

def test_api_key_parameter_overrides_env(mock_api_key):
    """API key parameter takes precedence over env var."""
    api = MochiAPI(api_key="explicit_key_456")
    assert api.api_key == "explicit_key_456"

def test_empty_api_key_raises_error():
    """Empty string API key is invalid."""
    with pytest.raises(MochiAPIError):
        MochiAPI(api_key="")

@responses.activate
def test_auth_header_construction(api_instance, responses_mock):
    """Request includes Basic auth header."""
    responses_mock.add(
        responses.GET,
        "https://app.mochi.cards/api/decks",
        json={"docs": []},
        status=200
    )

    api_instance.list_decks()

    auth_header = responses_mock.calls[0].request.headers.get("Authorization")
    assert auth_header.startswith("Basic ")
```

---

#### TASK-012: Write tests/unit/test_api_operations.py - Deck Operations
**Complexity:** L (Large)
**Dependencies:** TASK-009
**Description:** Test deck CRUD operations (list, create, get, update, delete).

**Acceptance Criteria:**
- [ ] Test: `list_decks()` returns list of decks
- [ ] Test: `list_decks()` handles pagination with bookmark
- [ ] Test: `create_deck(name)` returns created deck
- [ ] Test: `create_deck()` with parent_id creates subdeck
- [ ] Test: `get_deck(deck_id)` returns deck data
- [ ] Test: `update_deck()` modifies deck properties
- [ ] Test: `delete_deck()` sends DELETE request (404 handling)
- [ ] All tests verify request structure (URL, method, body)
- [ ] All tests verify response parsing

**Test Code (TDD):**
```python
@responses.activate
def test_list_decks(api_instance, mock_deck_response):
    """list_decks returns list of decks."""
    responses.add(
        responses.GET,
        "https://app.mochi.cards/api/decks",
        json={"docs": [mock_deck_response], "bookmark": None},
        status=200
    )

    result = api_instance.list_decks()

    assert len(result["docs"]) == 1
    assert result["docs"][0]["id"] == mock_deck_response["id"]

@responses.activate
def test_list_decks_pagination(api_instance, mock_deck_response):
    """list_decks respects bookmark parameter."""
    responses.add(
        responses.GET,
        "https://app.mochi.cards/api/decks?bookmark=next_page",
        json={"docs": [mock_deck_response], "bookmark": None},
        status=200
    )

    result = api_instance.list_decks(bookmark="next_page")

    assert len(responses.calls) == 1
    assert "bookmark=next_page" in responses.calls[0].request.url

@responses.activate
def test_create_deck(api_instance, mock_deck_response):
    """create_deck returns created deck."""
    responses.add(
        responses.POST,
        "https://app.mochi.cards/api/decks",
        json=mock_deck_response,
        status=200
    )

    result = api_instance.create_deck(name="Python")

    assert result["id"] == mock_deck_response["id"]
    request_body = json.loads(responses.calls[0].request.body)
    assert request_body["name"] == "Python"

@responses.activate
def test_create_subdeck_with_parent(api_instance, mock_deck_response):
    """create_deck with parent_id creates subdeck."""
    responses.add(
        responses.POST,
        "https://app.mochi.cards/api/decks",
        json=mock_deck_response,
        status=200
    )

    result = api_instance.create_deck(name="Advanced", parent_id="parent123")

    request_body = json.loads(responses.calls[0].request.body)
    assert request_body["parent-id"] == "parent123"

# ... test_get_deck, test_update_deck, test_delete_deck follow same pattern
```

---

#### TASK-013: Write tests/unit/test_api_operations.py - Card Operations
**Complexity:** L
**Dependencies:** TASK-009
**Description:** Test card CRUD operations with simple and template-based formats.

**Acceptance Criteria:**
- [ ] Test: `list_cards()` returns paginated card list
- [ ] Test: `list_cards()` filters by deck_id when provided
- [ ] Test: `create_card(content, deck_id)` creates simple card
- [ ] Test: `create_card()` with template_id and fields creates template card
- [ ] Test: `get_card()` returns card data
- [ ] Test: `update_card()` modifies card content
- [ ] Test: `update_card()` with trashed field soft-deletes
- [ ] Test: `delete_card()` hard-deletes (204 No Content)
- [ ] All tests verify field name transformation (snake_case → kebab-case)

**Test Code (TDD):**
```python
@responses.activate
def test_list_cards(api_instance, mock_card_response):
    """list_cards returns paginated cards."""
    responses.add(
        responses.GET,
        "https://app.mochi.cards/api/cards",
        json={"docs": [mock_card_response], "bookmark": None},
        status=200
    )

    result = api_instance.list_cards()

    assert len(result["docs"]) == 1
    assert result["docs"][0]["id"] == mock_card_response["id"]

@responses.activate
def test_list_cards_by_deck(api_instance, mock_card_response):
    """list_cards filters by deck_id."""
    responses.add(
        responses.GET,
        "https://app.mochi.cards/api/cards?deck-id=deck123",
        json={"docs": [mock_card_response], "bookmark": None},
        status=200
    )

    result = api_instance.list_cards(deck_id="deck123")

    assert "deck-id=deck123" in responses.calls[0].request.url

@responses.activate
def test_create_simple_card(api_instance, mock_card_response):
    """create_card creates simple markdown card."""
    responses.add(
        responses.POST,
        "https://app.mochi.cards/api/cards",
        json=mock_card_response,
        status=200
    )

    result = api_instance.create_card(
        content="# Q\n---\nA",
        deck_id="deck123"
    )

    request_body = json.loads(responses.calls[0].request.body)
    assert request_body["content"] == "# Q\n---\nA"
    assert request_body["deck-id"] == "deck123"

@responses.activate
def test_create_template_card(api_instance, mock_card_response):
    """create_card with template_id uses template."""
    responses.add(
        responses.POST,
        "https://app.mochi.cards/api/cards",
        json=mock_card_response,
        status=200
    )

    result = api_instance.create_card(
        content="",
        deck_id="deck123",
        template_id="template456",
        fields={"word": "ephemeral", "definition": "Lasting briefly"}
    )

    request_body = json.loads(responses.calls[0].request.body)
    assert request_body["template-id"] == "template456"
    assert request_body["fields"] is not None

@responses.activate
def test_soft_delete_card(api_instance, mock_card_response):
    """update_card with trashed field soft-deletes."""
    from datetime import datetime
    responses.add(
        responses.PATCH,
        "https://app.mochi.cards/api/cards/card123",
        json=mock_card_response,
        status=200
    )

    now = datetime.utcnow().isoformat()
    api_instance.update_card("card123", trashed=now)

    request_body = json.loads(responses.calls[0].request.body)
    assert "trashed?" in request_body

@responses.activate
def test_hard_delete_card(api_instance):
    """delete_card sends DELETE request."""
    responses.add(
        responses.DELETE,
        "https://app.mochi.cards/api/cards/card123",
        status=204
    )

    api_instance.delete_card("card123")

    assert responses.calls[0].request.method == "DELETE"
```

---

#### TASK-014: Write tests/unit/test_api_operations.py - Template Operations
**Complexity:** L
**Dependencies:** TASK-009
**Description:** Test template CRUD operations and field management.

**Acceptance Criteria:**
- [ ] Test: `list_templates()` returns template list
- [ ] Test: `create_template(name, content, fields)` creates template
- [ ] Test: Template field structure is preserved in request
- [ ] Test: `get_template()` returns template data
- [ ] Test: `update_template()` modifies template
- [ ] Test: Field validation in template creation (structure check)

**Test Code (TDD):**
```python
@responses.activate
def test_list_templates(api_instance):
    """list_templates returns all templates."""
    template = {
        "id": "template123",
        "name": "Vocabulary",
        "content": "# << Word >>",
        "fields": {}
    }
    responses.add(
        responses.GET,
        "https://app.mochi.cards/api/templates",
        json={"docs": [template], "bookmark": None},
        status=200
    )

    result = api_instance.list_templates()

    assert len(result["docs"]) == 1
    assert result["docs"][0]["name"] == "Vocabulary"

@responses.activate
def test_create_template(api_instance):
    """create_template creates new template."""
    template = {
        "id": "template123",
        "name": "Vocabulary",
        "content": "# << Word >>\n---\n<< Definition >>",
        "fields": {
            "word": {"id": "word", "name": "Word", "type": "text", "pos": "a"},
            "definition": {"id": "definition", "name": "Definition", "type": "text", "pos": "b"}
        }
    }
    responses.add(
        responses.POST,
        "https://app.mochi.cards/api/templates",
        json=template,
        status=200
    )

    result = api_instance.create_template(
        name="Vocabulary",
        content="# << Word >>\n---\n<< Definition >>",
        fields={
            "word": {"id": "word", "name": "Word", "type": "text", "pos": "a"},
            "definition": {"id": "definition", "name": "Definition", "type": "text", "pos": "b"}
        }
    )

    assert result["id"] == "template123"
    request_body = json.loads(responses.calls[0].request.body)
    assert request_body["name"] == "Vocabulary"
    assert "fields" in request_body
```

---

#### TASK-015: Write tests/unit/test_api_operations.py - Omitted Cards
**Complexity:** S
**Dependencies:** TASK-009
**Description:** Test omitted cards operation.

**Acceptance Criteria:**
- [ ] Test: `list_omitted_cards()` returns list (if implemented)
- [ ] OR: Test that operation is not implemented (skip/xfail if needed)
- [ ] Verify correct endpoint and parameters

---

#### TASK-016: Write tests/unit/test_error_handling.py
**Complexity:** M
**Dependencies:** TASK-009
**Description:** Test HTTP errors, network errors, and error response parsing.

**Acceptance Criteria:**
- [ ] Test: HTTP 400 (Bad Request) raises MochiAPIError
- [ ] Test: HTTP 401 (Unauthorized) raises MochiAPIError
- [ ] Test: HTTP 404 (Not Found) raises MochiAPIError with message
- [ ] Test: HTTP 500 (Server Error) raises MochiAPIError
- [ ] Test: Network timeout raises MochiAPIError
- [ ] Test: Connection refused raises MochiAPIError
- [ ] Test: Invalid JSON response raises MochiAPIError
- [ ] Test: Error message includes HTTP status code
- [ ] Test: Error messages are informative for debugging
- [ ] Test: Field-level errors are included in error message

**Test Code (TDD):**
```python
import pytest
from scripts.mochi_api import MochiAPI, MochiAPIError

@responses.activate
def test_http_400_error(api_instance):
    """HTTP 400 Bad Request raises MochiAPIError."""
    responses.add(
        responses.POST,
        "https://app.mochi.cards/api/cards",
        json={"errors": {"content": "Required field"}},
        status=400
    )

    with pytest.raises(MochiAPIError) as exc_info:
        api_instance.create_card(content="", deck_id="deck123")

    assert "400" in str(exc_info.value)

@responses.activate
def test_http_404_not_found(api_instance):
    """HTTP 404 Not Found raises MochiAPIError."""
    responses.add(
        responses.GET,
        "https://app.mochi.cards/api/decks/nonexistent",
        json={"errors": ["Deck not found"]},
        status=404
    )

    with pytest.raises(MochiAPIError, match="not found"):
        api_instance.get_deck("nonexistent")

@responses.activate
def test_http_500_error(api_instance):
    """HTTP 500 Server Error raises MochiAPIError."""
    responses.add(
        responses.GET,
        "https://app.mochi.cards/api/decks",
        json={"errors": ["Internal server error"]},
        status=500
    )

    with pytest.raises(MochiAPIError) as exc_info:
        api_instance.list_decks()

    assert "500" in str(exc_info.value)

def test_network_timeout(api_instance, monkeypatch):
    """Network timeout raises MochiAPIError."""
    import requests

    def mock_request(*args, **kwargs):
        raise requests.Timeout("Connection timeout")

    monkeypatch.setattr(requests, "request", mock_request)

    with pytest.raises(MochiAPIError, match="timeout|timeout"):
        api_instance.list_decks()

@responses.activate
def test_invalid_json_response(api_instance):
    """Invalid JSON in response raises MochiAPIError."""
    responses.add(
        responses.GET,
        "https://app.mochi.cards/api/decks",
        body="{ invalid json",
        status=200,
        content_type="application/json"
    )

    with pytest.raises(MochiAPIError):
        api_instance.list_decks()

@responses.activate
def test_field_level_errors_included(api_instance):
    """Field-level errors are included in exception message."""
    responses.add(
        responses.POST,
        "https://app.mochi.cards/api/decks",
        json={"errors": {"name": "Name is required"}},
        status=400
    )

    with pytest.raises(MochiAPIError) as exc_info:
        api_instance.create_deck(name="")

    error_msg = str(exc_info.value)
    assert "name" in error_msg.lower() or "required" in error_msg.lower()
```

---

## Phase 4: Unit Tests - Helpers & Validation (Tasks 17-21)

### Purpose
Test validation logic, helper functions, and error conditions.

### Tasks

#### TASK-017: Write tests/unit/test_validation.py - Prompt Quality
**Complexity:** M
**Dependencies:** TASK-009
**Description:** Test `validate_prompt_quality()` function with all validation rules.

**Acceptance Criteria:**
- [ ] Test: Focused validation (detects " and ", multiple commas)
- [ ] Test: Precise validation (detects vague words)
- [ ] Test: Consistent validation (detects variable prompts)
- [ ] Test: Binary validation (detects yes/no questions)
- [ ] Test: Pattern-matchable validation (checks question length)
- [ ] Test: Trivial validation (detects trivial indicators)
- [ ] Test: Valid prompt returns valid=true with no issues
- [ ] Test: Invalid prompt returns issues and suggestions
- [ ] Test: Strict mode raises PromptQualityError
- [ ] Test: Non-strict mode returns dict with issues

**Test Code (TDD):**
```python
import pytest
from scripts.mochi_api import validate_prompt_quality, PromptQualityError

def test_valid_prompt_returns_valid():
    """Well-formed prompt returns valid=true."""
    result = validate_prompt_quality(
        question="What is Python?",
        answer="A programming language"
    )

    assert result["valid"] is True
    assert len(result["issues"]) == 0

def test_unfocused_prompt_detected():
    """Prompt with 'and' is flagged as unfocused."""
    result = validate_prompt_quality(
        question="What is Python and how is it used?",
        answer="A language used for many purposes"
    )

    assert result["valid"] is False
    assert any("focused" in issue.lower() for issue in result["issues"])

def test_vague_words_detected():
    """Vague words like 'important' are flagged."""
    result = validate_prompt_quality(
        question="What is important about recursion?",
        answer="It allows functions to call themselves"
    )

    assert result["valid"] is False
    assert any("vague" in issue.lower() or "important" in issue.lower()
              for issue in result["issues"])

def test_binary_question_detected():
    """Yes/no questions are flagged."""
    result = validate_prompt_quality(
        question="Is Python a programming language?",
        answer="Yes"
    )

    assert result["valid"] is False
    assert any("binary" in issue.lower() or "yes/no" in issue.lower()
              for issue in result["issues"])

def test_strict_mode_raises_error():
    """Strict mode raises PromptQualityError."""
    with pytest.raises(PromptQualityError):
        validate_prompt_quality(
            question="Is Python a language?",
            answer="Yes",
            strict=True
        )

def test_suggestions_provided():
    """Invalid prompts include suggestions."""
    result = validate_prompt_quality(
        question="Tell me about Python",
        answer="Python is a language"
    )

    assert len(result["suggestions"]) > 0
    assert isinstance(result["suggestions"], list)
```

---

#### TASK-018: Write tests/unit/test_validation.py - Atomic Prompts
**Complexity:** M
**Dependencies:** TASK-009
**Description:** Test `break_into_atomic_prompts()` function.

**Acceptance Criteria:**
- [ ] Test: Complex prompt is broken into atomic prompts
- [ ] Test: Each atomic prompt is more focused
- [ ] Test: Returns list of dicts with 'question' and 'answer'
- [ ] Test: Handles empty input gracefully
- [ ] Test: Preserves original answer content

**Test Code (TDD):**
```python
from scripts.mochi_api import break_into_atomic_prompts

def test_complex_prompt_broken_into_atoms():
    """Complex prompt is decomposed into atomic prompts."""
    result = break_into_atomic_prompts(
        complex_prompt="What is Python and how is it used?",
        answer="Python is a general-purpose language used in web, data, and AI"
    )

    assert isinstance(result, list)
    assert len(result) > 1
    assert all("question" in item and "answer" in item for item in result)

def test_atomic_prompts_are_more_focused():
    """Each atomic prompt is more focused than original."""
    result = break_into_atomic_prompts(
        complex_prompt="What is Python and how is it used and why is it popular?",
        answer="Python is popular for data science and web development"
    )

    # Each question should be simpler
    for item in result:
        assert " and " not in item["question"]
```

---

#### TASK-019: Refactor helper functions for dependency injection
**Complexity:** M
**Dependencies:** None (code change)
**Description:** Modify helper functions to accept optional `api` parameter for testing.

**Acceptance Criteria:**
- [ ] `create_procedural_cards(prompt, deck_id, api=None, ...)` accepts api parameter
- [ ] `create_conceptual_lens_cards(concept, deck_id, api=None, ...)` accepts api parameter
- [ ] Default behavior unchanged (backward compatible)
- [ ] Helper functions can be tested with mocked API
- [ ] No breaking changes to existing usage

**Implementation Notes:**
Current usage: `create_procedural_cards(prompt, deck_id, ...)`
New signature: `create_procedural_cards(prompt, deck_id, api=None, ...)`

```python
def create_procedural_cards(prompt, deck_id, api=None, **kwargs):
    """Create procedural flashcards.

    Args:
        api: MochiAPI instance (optional, creates new if not provided)
    """
    if api is None:
        api = MochiAPI()

    # Original implementation
```

---

#### TASK-020: Write tests/unit/test_helpers.py - Procedural Cards
**Complexity:** L
**Dependencies:** TASK-019, TASK-009
**Description:** Test `create_procedural_cards()` with mocked API.

**Acceptance Criteria:**
- [ ] Test: Creates cards for transitions
- [ ] Test: Creates cards for rationales
- [ ] Test: Creates cards for timing
- [ ] Test: All created cards have correct deck_id
- [ ] Test: All created cards have base_tags
- [ ] Test: API errors are propagated
- [ ] Test: Works with mocked MochiAPI instance

**Test Code (TDD):**
```python
from unittest.mock import Mock
from scripts.mochi_api import create_procedural_cards

def test_create_procedural_cards_with_mocked_api():
    """create_procedural_cards works with mocked API."""
    mock_api = Mock()
    mock_api.create_card.return_value = {"id": "card123"}

    result = create_procedural_cards(
        procedure_name="Recursion",
        deck_id="deck123",
        api=mock_api,
        transitions=["Base case", "Recursive case"],
        rationales=["Why base case is needed"],
        timings=["~5 minutes"],
        base_tags=["recursion"]
    )

    assert mock_api.create_card.called
    assert len(result) >= 1  # At least one card created

def test_procedural_cards_have_base_tags():
    """Procedural cards include base_tags."""
    mock_api = Mock()
    mock_api.create_card.return_value = {"id": "card123"}

    create_procedural_cards(
        procedure_name="Test",
        deck_id="deck123",
        api=mock_api,
        transitions=["Step 1"],
        base_tags=["procedural", "test"]
    )

    call_args = mock_api.create_card.call_args
    tags = call_args[1]["manual_tags"] if "manual_tags" in call_args[1] else []
    assert "procedural" in tags
    assert "test" in tags
```

---

#### TASK-021: Write tests/unit/test_helpers.py - Conceptual Lens Cards
**Complexity:** L
**Dependencies:** TASK-019, TASK-009
**Description:** Test `create_conceptual_lens_cards()` with mocked API.

**Acceptance Criteria:**
- [ ] Test: Creates 5 cards (one for each lens)
- [ ] Test: Cards created for: attributes, similarities, parts, causes, significance
- [ ] Test: All cards have correct deck_id and base_tags
- [ ] Test: API errors are propagated
- [ ] Test: Works with mocked MochiAPI instance

**Test Code (TDD):**
```python
from unittest.mock import Mock
from scripts.mochi_api import create_conceptual_lens_cards

def test_create_conceptual_lens_cards():
    """create_conceptual_lens_cards creates 5 cards."""
    mock_api = Mock()
    mock_api.create_card.return_value = {"id": "card123"}

    result = create_conceptual_lens_cards(
        concept="Photosynthesis",
        deck_id="deck123",
        api=mock_api,
        lenses=["attributes", "similarities", "parts", "causes", "significance"],
        base_tags=["biology"]
    )

    # Should create 5 cards (one per lens)
    assert mock_api.create_card.call_count == 5
    assert len(result) == 5

def test_lens_cards_cover_five_lenses():
    """All 5 lenses are covered."""
    mock_api = Mock()
    created_cards = []

    def track_call(**kwargs):
        created_cards.append(kwargs)
        return {"id": "card123"}

    mock_api.create_card.side_effect = track_call

    create_conceptual_lens_cards(
        concept="Test",
        deck_id="deck123",
        api=mock_api
    )

    # Verify at least one card per lens
    assert len(created_cards) >= 5
```

---

## Phase 5: Integration Tests & CI/CD (Tasks 22-29)

### Purpose
Test complete workflows with real API interactions (recorded) and set up CI/CD.

### Tasks

#### TASK-022: Write tests/integration/test_card_workflows.py
**Complexity:** L
**Dependencies:** TASK-010
**Description:** Test end-to-end card workflows (create → update → soft delete → hard delete).

**Acceptance Criteria:**
- [ ] Test: Create simple card workflow
- [ ] Test: Create template-based card workflow
- [ ] Test: Update card content
- [ ] Test: Soft delete (trashed field)
- [ ] Test: Hard delete (permanent)
- [ ] Test: Card is retrievable after creation
- [ ] Test: Soft deleted card is marked as trashed
- [ ] All tests use VCR cassettes for reproducibility

**Test Code (TDD):**
```python
import pytest
import vcr

@pytest.mark.integration
@vcr.use_cassette("tests/integration/cassettes/test_card_workflows/create_simple_card.yaml")
def test_create_simple_card_workflow(integration_api, cleanup_cards):
    """Complete workflow: create simple card."""
    card = integration_api.create_card(
        content="# What is Python?\n---\nA programming language",
        deck_id="test-deck-id"
    )

    assert card["id"]
    assert card["content"] == "# What is Python?\n---\nA programming language"
    cleanup_cards.append(card["id"])

@pytest.mark.integration
@vcr.use_cassette("tests/integration/cassettes/test_card_workflows/create_and_update_card.yaml")
def test_create_and_update_card(integration_api, cleanup_cards):
    """Workflow: create card, then update content."""
    # Create
    card = integration_api.create_card(
        content="# Q\n---\nA",
        deck_id="test-deck-id"
    )
    cleanup_cards.append(card["id"])

    # Update
    updated = integration_api.update_card(
        card["id"],
        content="# Updated Q\n---\nUpdated A"
    )

    assert updated["content"] == "# Updated Q\n---\nUpdated A"

@pytest.mark.integration
@vcr.use_cassette("tests/integration/cassettes/test_card_workflows/soft_delete_card.yaml")
def test_soft_delete_card(integration_api, cleanup_cards):
    """Workflow: create card, soft delete (mark trashed)."""
    from datetime import datetime

    card = integration_api.create_card(
        content="# Delete me\n---\nI'm deleted",
        deck_id="test-deck-id"
    )
    cleanup_cards.append(card["id"])

    # Soft delete
    updated = integration_api.update_card(
        card["id"],
        trashed=datetime.utcnow().isoformat()
    )

    assert updated["trashed?"] is not None
```

---

#### TASK-023: Write tests/integration/test_deck_workflows.py
**Complexity:** L
**Dependencies:** TASK-010
**Description:** Test deck workflows including pagination and archiving.

**Acceptance Criteria:**
- [ ] Test: Create deck workflow
- [ ] Test: Create subdeck (with parent_id)
- [ ] Test: List cards in deck
- [ ] Test: Pagination with bookmark
- [ ] Test: Archive deck (soft delete)
- [ ] Test: Deck hierarchy is preserved
- [ ] All tests use VCR cassettes

**Test Code (TDD):**
```python
@pytest.mark.integration
@vcr.use_cassette("tests/integration/cassettes/test_deck_workflows/create_deck.yaml")
def test_create_deck_workflow(integration_api, cleanup_decks):
    """Workflow: create deck."""
    deck = integration_api.create_deck(name="Python Basics")

    assert deck["id"]
    assert deck["name"] == "Python Basics"
    cleanup_decks.append(deck["id"])

@pytest.mark.integration
@vcr.use_cassette("tests/integration/cassettes/test_deck_workflows/create_subdeck.yaml")
def test_create_subdeck_workflow(integration_api, cleanup_decks):
    """Workflow: create parent deck, then subdeck."""
    parent = integration_api.create_deck(name="Python")
    cleanup_decks.append(parent["id"])

    child = integration_api.create_deck(
        name="Advanced",
        parent_id=parent["id"]
    )
    cleanup_decks.append(child["id"])

    assert child["parent-id"] == parent["id"]

@pytest.mark.integration
@vcr.use_cassette("tests/integration/cassettes/test_deck_workflows/list_cards_pagination.yaml")
def test_list_cards_pagination(integration_api):
    """Workflow: list cards with pagination."""
    result = integration_api.list_cards(limit=10)

    assert "docs" in result
    assert isinstance(result["docs"], list)
    # Bookmark may be present or absent
```

---

#### TASK-024: Write tests/integration/test_template_workflows.py
**Complexity:** L
**Dependencies:** TASK-010
**Description:** Test template creation and template-based card workflows.

**Acceptance Criteria:**
- [ ] Test: Create template workflow
- [ ] Test: Create card using template
- [ ] Test: Update card with template fields
- [ ] Test: Template field structure preserved
- [ ] All tests use VCR cassettes

**Test Code (TDD):**
```python
@pytest.mark.integration
@vcr.use_cassette("tests/integration/cassettes/test_template_workflows/create_template.yaml")
def test_create_template_workflow(integration_api, cleanup_templates):
    """Workflow: create vocabulary template."""
    template = integration_api.create_template(
        name="Vocabulary",
        content="# << Word >>\n---\n<< Definition >>",
        fields={
            "word": {"id": "word", "name": "Word", "type": "text", "pos": "a"},
            "definition": {"id": "definition", "name": "Definition", "type": "text", "pos": "b"}
        }
    )

    assert template["id"]
    assert template["name"] == "Vocabulary"
    cleanup_templates.append(template["id"])

@pytest.mark.integration
@vcr.use_cassette("tests/integration/cassettes/test_template_workflows/create_card_with_template.yaml")
def test_create_card_with_template(integration_api, cleanup_templates, cleanup_cards):
    """Workflow: create template, then create card from template."""
    template = integration_api.create_template(
        name="Vocabulary",
        content="# << Word >>\n---\n<< Definition >>",
        fields={
            "word": {"id": "word", "name": "Word", "type": "text", "pos": "a"},
            "definition": {"id": "definition", "name": "Definition", "type": "text", "pos": "b"}
        }
    )
    cleanup_templates.append(template["id"])

    card = integration_api.create_card(
        content="",
        deck_id="test-deck-id",
        template_id=template["id"],
        fields={
            "word": {"id": "word", "value": "ephemeral"},
            "definition": {"id": "definition", "value": "Lasting a very short time"}
        }
    )
    cleanup_cards.append(card["id"])

    assert card["template-id"] == template["id"]
```

---

#### TASK-025: Record VCR cassettes for all integration tests
**Complexity:** M
**Dependencies:** TASK-022, TASK-023, TASK-024
**Description:** Run integration tests against real API to record VCR cassettes.

**Acceptance Criteria:**
- [ ] All integration tests have corresponding cassette files
- [ ] Cassettes are in `tests/integration/cassettes/` subdirectories
- [ ] Cassette files are in YAML format
- [ ] API key is redacted in cassettes (authorization header removed)
- [ ] Cassettes can be replayed (tests pass using cassettes)
- [ ] Cassette files are tracked in version control (except API key)

**Procedure:**
1. Set `MOCHI_API_KEY` environment variable with real API key
2. Run integration tests: `pytest tests/integration -m integration`
3. Verify cassette files created
4. Verify authorization headers are redacted
5. Commit cassette files

**Verification Tests:**
```bash
# Verify cassettes exist
ls -la tests/integration/cassettes/test_card_workflows/
ls -la tests/integration/cassettes/test_deck_workflows/
ls -la tests/integration/cassettes/test_template_workflows/

# Verify no API keys exposed
grep -r "MOCHI_API_KEY" tests/integration/cassettes/ || echo "✓ No API keys exposed"
```

---

#### TASK-026: Create .github/workflows/test.yml
**Complexity:** M
**Dependencies:** TASK-003
**Description:** Set up GitHub Actions CI/CD workflow for running tests.

**Acceptance Criteria:**
- [ ] Workflow runs on push to main and pull requests
- [ ] Tests run against Python 3.10, 3.11, 3.12
- [ ] Unit tests run on every push (use mock API key)
- [ ] Integration tests run only on main branch push (use real API key from secrets)
- [ ] Coverage report generated and uploaded to Codecov
- [ ] Workflow fails if coverage < 95%
- [ ] Job artifacts include coverage reports

**Test Code (Verify workflow structure):**
```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv python install ${{ matrix.python-version }}
      - run: uv python pin ${{ matrix.python-version }}
      - run: |
          cd plugins/mochi-creator
          uv sync --frozen --extra test
      - run: |
          cd plugins/mochi-creator
          uv run pytest tests/unit -m unit --cov
        env:
          MOCHI_API_KEY: test_key
      - run: |
          cd plugins/mochi-creator
          uv run pytest tests/integration -m integration --cov-append
        env:
          MOCHI_API_KEY: ${{ secrets.MOCHI_API_KEY }}
        if: github.event_name == 'push'
      - uses: codecov/codecov-action@v3
```

---

#### TASK-027: Set up Codecov integration and badge
**Complexity:** S
**Dependencies:** TASK-026
**Description:** Configure Codecov and add coverage badge to README.

**Acceptance Criteria:**
- [ ] Repository connected to Codecov
- [ ] Codecov action configured in workflow
- [ ] Coverage badge markdown created
- [ ] Badge added to plugin README
- [ ] Badge shows current coverage %

**Implementation:**
```markdown
# README section
## Testing

[![codecov](https://codecov.io/gh/joshuaoliphant/claude-plugins/branch/main/graph/badge.svg?token=ABC123)](https://codecov.io/gh/joshuaoliphant/claude-plugins)

**Coverage:** 95%+ for core mochi-creator plugin

Run tests locally:
```bash
cd plugins/mochi-creator
uv sync --extra test
uv run pytest --cov --cov-report=html
```

Coverage report: `htmlcov/index.html`
```

---

#### TASK-028: Add test architecture documentation to plugin README
**Complexity:** S
**Dependencies:** TASK-027
**Description:** Document testing strategy, how to run tests, how to add new tests.

**Acceptance Criteria:**
- [ ] README includes "Testing" section
- [ ] Documents how to run unit tests
- [ ] Documents how to run integration tests
- [ ] Explains unit vs integration test purpose
- [ ] Shows how to write new tests (with example)
- [ ] Links to test architecture details
- [ ] Shows coverage goals (95%+)

**Documentation Content (Example):**
```markdown
## Testing

This plugin has comprehensive test coverage (95%+) with both unit and integration tests.

### Run Tests

```bash
# All tests (unit + integration if cassettes available)
cd plugins/mochi-creator
uv run pytest

# Unit tests only (fast, mocked API)
uv run pytest tests/unit -m unit

# Integration tests (uses VCR cassettes)
uv run pytest tests/integration -m integration

# With coverage report
uv run pytest --cov --cov-report=html
```

### Test Structure

- **Unit Tests** (`tests/unit/`): Fast, isolated tests with mocked HTTP
  - API operations
  - Authentication
  - Error handling
  - Helper functions
  - Validation logic

- **Integration Tests** (`tests/integration/`): Complete workflows with VCR cassettes
  - Card creation workflows
  - Deck organization
  - Template-based cards

### Writing New Tests

Example unit test:

```python
import pytest
from scripts.mochi_api import MochiAPI

@responses.activate
def test_create_deck(api_instance):
    responses.add(
        responses.POST,
        "https://app.mochi.cards/api/decks",
        json={"id": "deck123", "name": "Python"},
        status=200
    )

    deck = api_instance.create_deck(name="Python")
    assert deck["id"] == "deck123"
```

See [`tests/unit/test_api_operations.py`](tests/unit/test_api_operations.py) for more examples.
```

---

#### TASK-029: Validate 95%+ coverage target achieved
**Complexity:** S
**Dependencies:** TASK-021, TASK-024
**Description:** Verify coverage metrics and celebrate completion.

**Acceptance Criteria:**
- [ ] Overall coverage is 95%+
- [ ] API operations coverage is 100%
- [ ] Helper functions coverage is 95%+
- [ ] All critical paths are tested
- [ ] Coverage report generated (HTML + JSON)
- [ ] CI/CD shows green checkmark
- [ ] No coverage degradation from previous runs

**Verification:**
```bash
cd plugins/mochi-creator
uv run pytest --cov --cov-report=term-missing

# Check HTML report
open htmlcov/index.html
```

Expected output:
```
Name                           Stmts   Miss  Cover   Missing
mochi_api.py                     400     20    95%    123,456,789
TOTAL                            400     20    95%
```

---

## Critical Path Analysis

### Core Dependencies (Cannot Parallelize)

```
TASK-001: Create directory structure
  ↓
TASK-002: Add dependencies
  ↓
TASK-003: pytest.ini
  ↓
TASK-004: .coveragerc
  ↓
TASK-005: Global conftest.py
  ↓
(TASK-006, TASK-007, TASK-008 can run in parallel)
  ↓
(TASK-009, TASK-010 can run in parallel)
  ↓
(TASK-011 through TASK-021 can run in parallel after fixtures ready)
  ↓
(TASK-022, TASK-023, TASK-024 can run in parallel)
  ↓
TASK-025: Record cassettes
  ↓
(TASK-026, TASK-027, TASK-028 can run in parallel)
  ↓
TASK-029: Validate coverage
```

### Parallel Execution Groups

**Group 1** (After TASK-005):
- TASK-006: Mock responses
- TASK-007: Builders
- TASK-008: Test data

**Group 2** (After Group 1):
- TASK-009: Unit conftest
- TASK-010: Integration conftest

**Group 3** (After Group 2):
- TASK-011: Authentication tests
- TASK-012: Deck operation tests
- TASK-013: Card operation tests
- TASK-014: Template operation tests
- TASK-015: Omitted cards tests
- TASK-016: Error handling tests
- TASK-017: Prompt validation tests
- TASK-018: Atomic prompts tests

**Group 4** (After Group 3):
- TASK-019: Refactor helpers for DI (code change)
- TASK-020: Procedural cards tests
- TASK-021: Conceptual lens tests

**Group 5** (After TASK-010):
- TASK-022: Card workflows
- TASK-023: Deck workflows
- TASK-024: Template workflows

**Group 6** (After Group 5):
- TASK-025: Record cassettes (requires real API key)

**Group 7** (After TASK-025):
- TASK-026: GitHub Actions workflow
- TASK-027: Codecov integration
- TASK-028: Documentation

**Final** (After Group 7):
- TASK-029: Validate coverage

---

## Coverage Map

### Operations Coverage

| Operation | Unit Test | Integration Test | Coverage |
|-----------|-----------|------------------|----------|
| `list_decks()` | TASK-012 | TASK-023 | 100% |
| `create_deck()` | TASK-012 | TASK-023 | 100% |
| `get_deck()` | TASK-012 | TASK-023 | 100% |
| `update_deck()` | TASK-012 | TASK-023 | 100% |
| `delete_deck()` | TASK-012 | TASK-023 | 100% |
| `list_cards()` | TASK-013 | TASK-022 | 100% |
| `create_card()` | TASK-013 | TASK-022 | 100% |
| `get_card()` | TASK-013 | TASK-022 | 100% |
| `update_card()` | TASK-013 | TASK-022 | 100% |
| `delete_card()` | TASK-013 | TASK-022 | 100% |
| `list_templates()` | TASK-014 | TASK-024 | 100% |
| `create_template()` | TASK-014 | TASK-024 | 100% |
| `get_template()` | TASK-014 | TASK-024 | 100% |
| `update_template()` | TASK-014 | TASK-024 | 100% |
| `delete_template()` | TASK-014 | TASK-024 | 100% |
| `list_omitted_cards()` | TASK-015 | - | TBD |

### Error Handling Coverage

| Scenario | Test Task | Coverage |
|----------|-----------|----------|
| Missing API key | TASK-011 | 100% |
| HTTP 400 | TASK-016 | 100% |
| HTTP 401 | TASK-016 | 100% |
| HTTP 404 | TASK-016 | 100% |
| HTTP 500 | TASK-016 | 100% |
| Network timeout | TASK-016 | 100% |
| Connection refused | TASK-016 | 100% |
| Invalid JSON | TASK-016 | 100% |

### Helper Functions Coverage

| Function | Unit Test | Integration Test | Coverage |
|----------|-----------|------------------|----------|
| `validate_prompt_quality()` | TASK-017 | - | 100% |
| `break_into_atomic_prompts()` | TASK-018 | - | 100% |
| `create_procedural_cards()` | TASK-020 | - | 95% |
| `create_conceptual_lens_cards()` | TASK-021 | - | 95% |

---

## Success Metrics

✅ **Completeness**: All 15 API operations tested + 4 helper functions + error handling
✅ **Coverage**: 95%+ overall, 100% for critical paths
✅ **Maintainability**: Clear test organization, reusable fixtures, well-documented
✅ **Performance**: Unit tests run in <10 seconds, integration tests <30 seconds
✅ **Reliability**: No flaky tests, deterministic (VCR cassettes), reproducible
✅ **Quality**: Follows TDD principles, comprehensive edge cases, good error messages

---

## Implementation Notes

### Technology Stack
- **pytest**: Test framework
- **pytest-cov**: Coverage reporting
- **responses**: HTTP mocking for unit tests
- **vcrpy**: Request recording for integration tests
- **pytest-mock**: Mocking utilities

### Best Practices
1. **TDD**: Write tests first, implementation second
2. **Isolation**: Each test is independent (no shared state)
3. **Clarity**: Test names describe what is being tested
4. **Fixtures**: Reusable test data via pytest fixtures
5. **Builders**: Fluent API for creating test data
6. **Mocking**: Deterministic tests with controlled dependencies

### Maintenance
- Regularly update VCR cassettes when API changes
- Monitor coverage metrics in CI/CD
- Add tests for new features before implementation
- Keep mock responses in sync with real API

---

## Deliverables Checklist

- [ ] 29 tasks completed in order
- [ ] `tests/` directory structure created
- [ ] `pyproject.toml` configured with dependencies
- [ ] `pytest.ini` and `.coveragerc` created
- [ ] All fixture modules created (conftest.py, builders, mock responses)
- [ ] All unit test modules created (6 test files, ~500+ test cases)
- [ ] All integration test modules created (3 test files)
- [ ] VCR cassettes recorded
- [ ] GitHub Actions workflow created
- [ ] Codecov integration configured
- [ ] README updated with testing documentation
- [ ] Coverage metrics verified (95%+)
- [ ] All tests passing (green checkmark in CI/CD)

---

**Plan created:** 2025-11-13
**Ready for implementation:** Yes
**Estimated total effort:** 6-10 working days
**Next step:** Begin with TASK-001 (Directory Structure)

La Boeuf, this comprehensive plan provides everything needed to implement a production-quality test suite for the mochi-creator plugin. The tasks are properly scoped, dependencies are clear, and success criteria are measurable. Ready to dive in?
