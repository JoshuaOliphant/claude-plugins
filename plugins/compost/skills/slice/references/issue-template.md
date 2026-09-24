# Issue template

One issue per tracer bullet. The title names the behavior it makes work, in the glossary's words
("Customer cancels a pending order"), not the layer it touches ("Add cancel endpoint").

````markdown
## Parent

#<parent issue number>: <parent title>

## What to build

<The end-to-end behavior this issue makes work, from the user's side. Two to four sentences, not a
layer-by-layer list.>

## Acceptance criteria

- [ ] **AC-1: <title>**
  **Given** <...>
  **When** <...>
  **Then** <...>
- [ ] **AC-3: <title>**
  ...

## Files

- Create: `src/orders/cancellation.py` (decides whether an order can be cancelled)
- Modify: `src/orders/routes.py:40-72` (cancel action on the order page)
- Modify: `src/emails/templates.py` (cancellation email)
- Test: `tests/orders/test_cancellation.py` (existing; the `pending_order` fixture fits)

## Interfaces

- Consumes:
  - `Order.status: OrderStatus` and `Order.lines: list[OrderLine]` (existing)
  - `refund(order_id: OrderId, amount: Money) -> RefundId` from #41
- Produces:
  - `can_cancel(order: Order) -> CancelDecision` where
    `CancelDecision = Allowed | Refused(reason: str)`
  - `cancel(order_id: OrderId, actor: ActorId) -> Order`, raising `CancellationRefused`

## Blocked by

- #41: Refunds can be issued for a whole order

<!-- or: None (can start immediately) -->
````

## Filling it in

- **Acceptance criteria** are copied word for word from the spec, AC numbers included, so the
  test names and verify's report line up with the spec. Each AC-N appears in exactly one issue.
- **Files** list every path the issue creates or changes, with a one-line responsibility for each.
  The Test line names the existing test module, fixture, or parametrized table the criteria will
  extend when one fits, so `compost:build` starts from the suite that is already there.
- **Interfaces** give exact names and types in the project's language. "Existing" marks names
  already in the code. Every consumed name is either existing or produced by an issue this one is
  blocked by. Leave the block out only when the issue neither consumes nor produces anything
  another issue touches.
- **Blocked by** lists genuine gates only. An issue with no blockers can start now.
- A prefactor issue says what it makes easier and which issues it unblocks.
- An expand-contract batch says which callers it migrates and that the old form must still work
  when it lands.

## Local tracker

With a local tracker, write one file per issue at `.scratch/<slug>/issues/<NN>-<issue-slug>.md`,
numbered from `01` in dependency order. Use the same sections, with a `Status: ready-for-agent`
line under the title and `Blocked by: 01, 03` using file numbers.
