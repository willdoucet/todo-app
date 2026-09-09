## Pydantic

### Data & migrations
- A field whose name matches a type in its own annotation (`date: Optional[date]`) aliases the import (`from datetime import date as _Date`).
- Schemas follow Base / Create / Update / Read; Update has all-optional fields and omits immutable discriminators (a `type` column is not patchable).
- Cross-field rules (XOR, "one of A or B required", end after start) live in a `model_validator(mode="after")` AND a DB CHECK constraint.
- String fields carry `min_length` / `max_length` matching the column; numeric fields carry bounds; the same limits appear in APP_FLOW.md → Form Validation.
- Read models set `from_attributes=True`; nested detail models are `Optional` with `None` default so old rows still serialize.

### API & trust boundaries
- Read models never expose hashes, tokens, encrypted blobs, or internal flags; the ORM model is never the response type.
- Validator error messages are the exact strings the UI shows or maps; changing one updates APP_FLOW.md.
- Overlong inputs are rejected by length before any expensive work (hashing, parsing) runs on them.

### Testing
- One test per validator branch, including the message text.
- One test that an old row shape (missing optional fields) still passes the Read model.
