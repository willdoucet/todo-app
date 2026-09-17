## Framework helpers (Python CLIs)

### Data & migrations
- A line-oriented reader and its writer agree on what a line boundary is: `json.dumps(ensure_ascii=False)` leaves U+2028, U+2029 and U+0085 raw and `str.splitlines()` honours them, so a value carrying one splits the record on read; escape them on write or split on `\n` only.
- Every value a reader orders or compares by (a timestamp, a sequence number) is validated on write for type and format and is never dated ahead of the clock that writes it; readers coerce rather than raise, because a fail-silent banner turns an exception into an open gate.
- A waiver or resolution record names the item it clears, and the reader checks that name against later failures instead of trusting the newest line; a union merge can put an older failure behind a newer resolution. The reader also applies the same resolver-eligibility rule the writer enforces, so a line the CLI would have rejected cannot open a gate.

### API & trust boundaries
- A CLI validates the merged input (flags, positional JSON, `--field`), never one source alone, and refuses fields that are computed on read or filled by the tool.
- Enumerated names (skills, tiers, statuses) are validated on write against the one list the readers use; a typo is refused with the valid names, never written silently.

### Testing
- Every rejection has a test in each input form, and each asserts the store is byte-identical afterwards.
- Fixtures give every entry an explicit, ordered timestamp so a real "now" cannot outrank a hand-dated later step.
