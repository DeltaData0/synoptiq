# Run log

Record every pilot, data build, training, evaluation, and release run. Never replace a prior entry.

| Run ID | UTC started | Git commit | Manifest ID/hash | Command | Split / seed | Output path | Result / caveat | Reviewer |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| setup-fixture-v1 | 2026-09-26 | 5a3a9b2 | fixture-v1 | `make smoke` | n/a | `data/fixtures/` | Fixture-contract setup; no model claim | Pending |
| imd-pilot-2017-2018 | 2026-09-26 | 0c9360c | imd-2017-pilot; imd-2018-pilot | `curl POST RF25.php` + `xarray.open_dataset` | n/a / n-a | `data/raw/imd/` | ✅ D1-03 complete: both official annual files decoded; UTC observation-window semantics remain pending D1-04 | Pending |
| gefs-pilot-20180801-control | 2026-09-26 | 0c9360c | observed GEFS 2018-08-01 control key | S3 listing + `curl` + `cfgrib` + `eccodes` | 2018 00 UTC / n-a | `data/raw/gefs/apcp_sfc_2018080100_c00.grib2` | ⚠️ D1-02 in progress: control precipitation decoded; perturbed members and PWAT downloading; no model claim | Pending |
| gefs-pilot-20180801-members-pwat | 2026-09-26 | 7d1ac1e + uncommitted audit work | `gefs-20180801-*` | `curl` + `cfgrib` + `eccodes` | 2018 00 UTC / n-a | `data/raw/gefs/` | ✅ D1-02 complete: c00/p01–p04 precipitation plus c00 PWAT decoded; +240–+246 control accumulation observed; D1-04 remains blocked on IMD-window semantics | Pending |
| d1-01-roster-and-review | 2026-09-27 | 208c875 + uncommitted roster work | n/a | GitHub branch-protection API + documented team roster | n/a / n-a | `DECISIONS.md`, `AGENTS.md` | ✅ D1-01 acceptance evidence posted: six named A–F owners, source/manifest and ticket-ownership contracts, one-approval protection on `main`; GitHub invitations await exact usernames | Pending |
| d1-01-collaborator-invitations | 2026-09-27 | e9b3962 + uncommitted invitation work | n/a | GitHub collaborator-invitation API | n/a / n-a | GitHub repository invitations | ✅ D1-01: invitations sent to `@DeltaData0`, `@aanyavarshneyav`, `@Rudrakssh`, `@dhruvsded1`, and `@Triman01` with push permission; acceptance remains pending each member | Pending |
