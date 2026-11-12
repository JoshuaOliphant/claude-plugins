# Changelog

All notable changes to the compost plugin. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions are `plugin.json` versions.

## [0.32.5] - 2026-11-12

### Added

- CHANGELOG.md, with a section per released version backfilled from git history.

## [0.32.4] - 2026-11-09

### Changed

- compost 0.32.4: canon essay on when to codify a multi-agent job as a workflow

## [0.32.3] - 2026-11-09

### Changed

- compost stop-guard: let a message's origin decide whether the user sent it (#206)
- compost stop-guard: name the sender check sent_by_user (#206 review)
- compost stop-guard: treat a null or non-dict origin as not the user's, explicitly (#207 review)

## [0.32.2] - 2026-11-08

### Changed

- compost:setup: verify the tracker has issues enabled before recording it (#204)

### Removed

- compost:setup: order the issues check before labels, name the settings path, drop template notes (#204)

## [0.32.1] - 2026-11-06

### Fixed

- fix(compost): skill-drift writes a digest on no-pattern runs and lists sub-threshold hits

## [0.32.0] - 2026-11-05

### Changed

- compost: run the Jev tools on Ollaya when the TypeSafe SDK variables say so
- compost: settle review findings on the Ollaya backend
- compost: hold an exported key back from plain-HTTP servers; keep old cache hits
- compost: explain a refused placeholder; rewrap the edited doc lines
- compost: a keyed Ollaya needs a key; say Ollaya support is untested on a real server

## [0.31.0] - 2026-10-30

### Changed

- compost 0.25.1, above main's 0.25.0 after #190
- compost:verify builds and keeps a repo verify command (#196)
- compost 0.31.0, above main's 0.30.0 after #192
- verify: name the timestamp the cache staleness check compares

### Removed

- verify: retire superseded AC rows on record; read AC tables in bulk
- verify: keep the AC-table cache fresh on retirement; show the table shape

## [0.30.0] - 2026-10-30

### Changed

- Mutate wiring in verify's hand walk, and don't count a mutant that fails to build (#191)
- Say verify checks build's walk on uncovered lines; keep the skip sentence next to its referent (#191)

## [0.29.0] - 2026-10-30

### Changed

- compost: review-changes fails a reviewer with no record of what it checked (#193)
- compost: pin the AC-N word boundary and the Standards checked prompt in the workflow suite
- compost: an unchecked review keeps its findings; AC-N maps by name
- compost: an AC-N maps only through a cited entry or a finding
- compost: an AC-N maps through a finding only when its claim names it

## [0.27.0] - 2026-10-29

### Changed

- compost:thin: say where the AC remap lands and what to run without a verify command

### Removed

- compost:thin: remap AC tables when it folds or deletes a test

## [0.25.0] - 2026-10-29

### Changed

- compost: implement spawns a lane only when it outweighs the handoff; review runs code-review only on executable code (#184)
- compost 0.25.0
- compost: deepen picks two to four designer stances per problem; fan-out judges only diverging attempts (#185)
- compost: README and review intro say code-review runs on executable code (#184 review)
- compost: name check.md for both its uses; state the map's subagent rule once (#186 review)
- compost: fan-out keeps the judge when converging attempts match a favoured frame (#185 review)
- compost: map-issue names which step 5 sends research to subagents (#186 re-review)

### Removed

- compost: prune and slice fan out only when it pays; builder check drops its persona line (#186)

## [0.24.3] - 2026-10-29

### Changed

- feat(compost): thin.py survivors runs thin's own operators by default (#94)

## [0.24.2] - 2026-10-29

### Added

- compost: address review on the tracker-id and stop-guard fixes

### Changed

- compost: fetch the Spec issue by the tracker's own id; let deploy and people-facing stops through

## [0.24.1] - 2026-10-24

### Changed

- compost: cite lines from per-file reads, not cat -n over several files

## [0.24.0] - 2026-10-22

### Changed

- feat(compost): opt-in lane routing table for implement (#138)

### Fixed

- fix(compost): tighten lane routing after review (#138)
- fix(compost): close lane routing's second-round review gaps (#138)
- fix(compost): last lane routing review round (#138)
- fix(compost): address PR #175 review on lane routing (#138)

## [0.23.3] - 2026-10-20

### Fixed

- fix(compost): spec fires on rules and limits added to existing code (#176)
- fix(compost): keep spec description under the 1024 limit (#176)

## [0.23.2] - 2026-10-19

### Fixed

- fix(compost): spec fires on Sonnet for "acceptance criteria" asks; README says compost targets Opus (#135)
- fix(compost): drop 'answer inline' from spec's new trigger sentence so it can't read as covering questions (#135)

## [0.23.1] - 2026-10-19

### Added

- Address review: state green rule, tighten evidence claims, headless wording

### Changed

- compost:diagnose: require the failing output of the check before the first edit

## [0.23.0] - 2026-10-18

### Added

- feat(compost): add a deeper-ask step to spec (#156)

### Changed

- docs(compost): deeper ask on the settled-issue path, no escape hatch (#156)
- docs(compost): make spec's deeper ask observable in the parent issue (#156)
- docs(compost): spec's closing message repeats the deeper-ask answers (#156)
- feat(compost): make the deeper ask its own skill, compost:deeper-ask (#156)

## [0.22.1] - 2026-10-18

### Changed

- docs(compost): a denied workflow call falls back to the full by-hand review (#164)
- docs(compost): tighten the denied-workflow fallback after review (#164)

## [0.22.0] - 2026-10-18

### Changed

- feat(compost): every change is reviewed; a small diff gets one reviewer on both axes (#161)
- test(compost): a null line count runs the full review path (#161)
- test(compost): a small diff Jev never ranked runs the full review path (#161)

### Fixed

- fix(compost): light review proves itself small, not structural, and checked on every axis (#161)
- fix(compost): light review keeps stray-tagged findings and names a missing risk ranking (#161)

## [0.21.4] - 2026-10-18

### Changed

- feat(compost): thin.py survivors reports a mutation score (#114)

## [0.21.3] - 2026-10-17

### Fixed

- fix(compost): Jev scripts re-run under uv when typesafe-sdk is missing (#167)
- fix(compost): a failed uv install exits 3, and the re-exec marker stops at the child (#167)

### Removed

- docs(compost): needs_uv's header and docstring say uv installs first and the marker drops (#167)

## [0.21.1] - 2026-10-17

### Changed

- docs(compost): finish closes PRs through REST and names the cloud ready path (#153)

### Fixed

- fix(compost): finish uses gh api REST for PR commands (#153)

## [0.21.0] - 2026-10-17

### Changed

- docs(compost): use gh REST for tracker commands, since cloud sessions block GraphQL (#144)
- feat(compost): journal thin.py matrix rows and resume a killed run (#143)
- test(compost): shut each review server down inside its test (#147)
- test(compost): pin a resumed crash row and the resume and progress logs (#143)
- docs(compost): collect test-value's coverage report with the fail-under gate off (#147)
- docs(compost): setup's Jev check says what an exit 3 from a client that can't start means (#145)

### Fixed

- fix(compost): collect coverage contexts with the fail-under gate off (#147)
- fix(compost): jev.py says Jev is unavailable in one line when TypeSafe is unreachable (#145)
- fix(compost): rename the resume journal into place so a kill mid-rewrite keeps its rows (#143)
- fix(compost): keep a killed matrix run's journal and children safe (#143)
- fix(compost): jev.py status builds the client, so a key or proxy it can't use exits 3 (#145)
- fix(compost): a finished matrix run deletes its journal, so only a killed run's blocks a fresh one (#143)

## [0.20.1] - 2026-10-17

### Fixed

- fix(compost): give spec/slice descriptions margin on the disk-access routing case

## [0.20.0] - 2026-10-17

### Changed

- feat(compost): thin's own mutation operators for the breaks cosmic-ray can't make (#124)
- chore: ignore coverage's per-process data files
- Record thin's own operators and the AC-6 measurement in the kill-matrix reference
- feat(compost): report and uninstall installs their marketplace no longer lists (#85)
- test(compost): kill the orphan diff's surviving mutants (#85)
- style(compost): space in skill-drift test constant (#97)
- refactor(compost): find_active decides which superseded plugins to disable (#85)

### Fixed

- fix(compost): thin's operators after review (#124)
- fix(compost): thin's operators after the Standards review; docs; compost 0.19.0 (#124)
- fix(compost): thin reaps what a run's escaped sessions leave behind (#128)
- fix(compost): /drift shows the open hits skill_drift.py counts, and survives a bad log line (#97)
- fix(compost): count a wrong-typed skill-drift log line as unreadable (#97)
- fix(compost): validate marketplace catalogs and name orphans one way (#85)
- fix(compost): /drift names the exception a crashed skill_drift.py ends on, and its test pins the argv (#97)
- fix(compost): skip unreadable catalogs and uninstall rather than disable orphans (#85)

## [0.19.0] - 2026-10-17

### Changed

- refactor(compost): the answer-read check flags reads past the view, not any dict keyed 'score' (#105)

### Fixed

- fix(compost): narrow skips a group that would pass the cap and keeps smaller likely ones (#105)
- fix(compost): classify-change always sends a change feeding a mechanism to be read (#70)
- fix(compost): list plugins lazily, from the same claude dir, keeping local installs local (#104)

## [0.18.0] - 2026-10-17

### Changed

- feat(compost): thin.py survivors, diff-scoped mutation testing for verify (#123)

## [0.17.4] - 2026-10-17

### Changed

- test(compost): thin's children keep every sys.path entry but compost's scripts

## [0.17.3] - 2026-10-17

### Changed

- test: fold tests that no mutant needed

## [0.17.2] - 2026-10-17

### Added

- First version tracked in this repository.
