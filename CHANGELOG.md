# Change Log

## [v0.2.0] - yyyy-mm-dd
  
### Added

- `Panic` exception class for signaling defects in user-provided callbacks
- Comprehensive error handling for all transformation functions that accept user callbacks
- All top-level functions (`map`, `map_err`, `tap`, `tap_async`, `and_then`, `and_then_async`, `match`) now wrap user callbacks with error handling
- Instance methods now properly catch and convert callback exceptions to `Panic`
- Extensive test coverage for `Panic` scenarios across all transformation functions
 
### Changed

- User callback exceptions are now converted to `Panic` to distinguish defects from expected error handling
- Match handlers are now wrapped with try/panic to catch exceptions and signal defects
- All async transformation functions use proper `Awaitable` type hints for callbacks
 
### Fixed

- Type preservation in curried function forms using wrapper functions instead of lambdas
