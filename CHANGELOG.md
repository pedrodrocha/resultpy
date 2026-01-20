# Change Log

## [v0.4.0] - yyyy-mm-dd

### Added

- Optional `should_retry` predicate in `RetryConfig` / `RetryConfigAsync` for `safe()` and `safe_async()`
  to control which errors trigger retries.

### Changed

### Fixed
--
## [v0.3.0] - 2026-01-19

### Added

- `Result.gen()` method for generator-based Result composition (do-notation).
- `Result.gen_async()` method for async generator-based Result composition (async do-notation).
- `Result.flatten()` method for flattening nested Results.
- `Result.partition()` method for partitioning an iterable of Results into separate lists of ok and err values.

### Changed

## Fixed

---

## [v0.2.0] - 2026-01-17
  
### Added

- `fn` helper for typed lambda expressions: `fn[int, int](lambda x: x * 2)`
- `Panic` exception class for signaling defects in user-provided callbacks
- Docstrings for all public APIs in `result.py`, `error.py`, and `safe.py`
 
### Changed

- User callback exceptions are now converted to `Panic` to distinguish defects from expected error handling
- Match handlers are now wrapped with try/panic to catch exceptions and signal defects
- All async transformation functions use proper `Awaitable` type hints for callbacks
- `is_ok()` and `is_err()` are now concrete implementations in the base `Result` class using the `status` property
- `TaggedError` subclasses require `TAG` class attribute instead of `tag` property
- `TaggedError.match()` and `match_partial()` now use type-based pattern matching with error classes as keys instead of string tags.
 
### Fixed
