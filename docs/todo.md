# DesignIt - Future Improvements and Postponed Decisions

This document tracks ideas and decisions that have been postponed for future consideration.

## Postponed Refactoring

### Flow Name vs Type Name Clarification

**Context:** With the introduction of named datadicts and qualified type references (REQ-GRAM-051, REQ-GRAM-052), flow "names" are now explicitly type references rather than just flow identifiers.

**Proposal:** Consider renaming `name` to `type_name` in flow models (`DataFlow`, `SCDFlow`) for semantic clarity.

**Files affected:**
- `src/designit/model/dfd.py` - `DataFlow.name` → `DataFlow.type_name`
- `src/designit/model/scd.py` - `SCDFlow.name` → `SCDFlow.type_name`
- All code referencing these fields

**Decision:** Postponed as it's a larger refactor with no functional impact. The current `name` field works correctly; this is purely a naming/documentation improvement.

**Date:** 2026-02-01

---

## Ideas for Future Consideration

### Request/Response Pairing

**Context:** In interactions with external systems, there are often request/response pairs. The current data-flow model treats these as separate, unrelated flows.

**Possible approaches discussed:**
1. **Paired flow syntax** - `flow Login: Customer -> System { request: LoginRequest, response: LoginResponse }`
2. **Request/response markers** - Annotations linking flows together
3. **Interface construct** - New `interface` keyword with `operation` definitions

**Decision:** Decided to stay with pure Structured Analysis data-flow semantics. The named datadict feature (namespacing) addresses the practical issue of name collisions across different external interfaces without changing the fundamental model.

**Date:** 2026-02-01
