# Quality Criteria

Empty by design. Add a criterion when a review catches a *real* failure, not
preemptively. Each entry records the failure that produced it.

Format:

## Category: area — e.g. API design, error handling, tests

### Criteria
- specific, testable check

### Severity: blocking | warning
### Source: where this came from
### Last triggered: date, or "never"

Promote a criterion triggered 3+ times to "always check". Suggest pruning one
never triggered after 10+ evaluations.
