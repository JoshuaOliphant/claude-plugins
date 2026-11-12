# Changelog

All notable changes to the compound-knowledge plugin. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions are `plugin.json` versions.

## [0.10.3] - 2026-11-12

### Added

- CHANGELOG.md, with a section per released version backfilled from git history.

## [0.10.2] - 2026-10-17

### Changed

- test(compound-knowledge): detect corpus readers beyond path="{write_path}" (#157)

### Removed

- test(compound-knowledge): unit-test the corpus-reader detector, drop redundant verbs (#157)

## [0.10.1] - 2026-10-17

### Changed

- test(compound-knowledge): every corpus reader must skip _archive/ (#141)

## [0.10.0] - 2026-10-17

### Added

- Add the garden face to compound-graduate (#60)

### Changed

- Move directory normalization into the shared config loader (#106)
- Keep archived solutions out of every reader (#60)
- Leave archived solutions out of the registry's component list (#60)

## [0.9.0] - 2026-10-17

### Removed

- Retire the feedback skill in favour of auto memory

## [0.8.8] - 2026-10-17

### Changed

- compound-knowledge: make the solution schema and the captured corpus agree (#73)
- compound-retrieve: ship fixture KBs with the evals so they measure the skill (#116)

## [0.8.7] - 2026-10-17

### Added

- First version tracked in this repository.
