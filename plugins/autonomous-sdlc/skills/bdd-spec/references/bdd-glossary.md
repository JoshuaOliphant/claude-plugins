# BDD Glossary

Quick reference for Behavior-Driven Development terminology.

## Core Terms

**Feature**
A high-level capability of the system described from a stakeholder's perspective.
Example: "User Authentication" or "Shopping Cart Checkout"

**Scenario**
A concrete example of a feature's behavior in a specific situation.
Example: "Successful login with valid credentials"

**Given**
A precondition — the state of the system before the action. Establishes context.
Example: "Given a registered user with email alice@example.com"

**When**
The action or event that triggers the behavior. One action per scenario.
Example: "When the user submits the login form with valid credentials"

**Then**
The expected outcome — observable, verifiable, and measurable.
Example: "Then the user is redirected to the dashboard"

**And / But**
Continuation keywords for multi-line Given, When, or Then clauses.
Example: "Then the user is redirected to the dashboard / And a session cookie is set"

**Background**
Shared preconditions that apply to every scenario in a feature. Runs before each scenario.
Example: "Background: Given the application is running / And the database is seeded with test data"

**Scenario Outline**
A parameterized scenario template with an Examples table. Runs once per table row.
Example: "Scenario Outline: Login validation / When the user submits <input> / Then the system shows <error>"

**Examples**
The data table that drives a Scenario Outline. Each row is a separate test run.
Example: "| input | error | / | empty email | Email is required | / | bad format | Invalid email |"

## Structural Terms

**Acceptance Criteria (AC)**
A set of conditions that define when a feature is "done." Written in Given/When/Then format. Numbered AC-1, AC-2, etc. for traceability.

**Happy Path**
The primary success scenario — everything goes right. Always write this first.

**Sad Path / Error Path**
Scenarios where something goes wrong — invalid input, unauthorized access, system failure.

**Edge Case**
An unusual or boundary condition that might be overlooked — empty input, maximum values, concurrent access, network timeout.

## Process Terms

**Three Amigos**
A collaborative session between developer, tester, and business stakeholder to write acceptance criteria together. This skill simulates the process with AI as facilitator.

**Living Documentation**
Executable specifications (feature files) that serve as both tests and documentation. They stay in sync with the code because they *are* the tests.

**Specification by Example**
The practice of using concrete examples to drive out requirements. "Show me an example" is more productive than "describe the rule."

**Outside-In Development**
Starting from acceptance tests (outer loop, BDD) and working inward to unit tests (inner loop, TDD). BDD defines what to build; TDD defines how to build it.
