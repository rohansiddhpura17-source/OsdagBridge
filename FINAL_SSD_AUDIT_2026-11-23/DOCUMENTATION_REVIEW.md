# Documentation Review

## Reviewed materials

Reviewed the Phase 21 hotfix report, Phase 22 engineering and numerical summaries, Phase 22.1 final technical report, submission reproduction guide, checklist, Git references, test evidence logs, relevant Markdown/CSV/JSON/text in the package, and historical project documentation inventory. Internal Markdown links in the final README and package Markdown were checked; the two external links in Phase 22 evidence point to the referenced FHWA and SciPy pages. The README distinguishes screening work through its author line and scope, and acknowledges FOSSEE/IIT Bombay.

## Findings

### P1 — Code-edition citations are inconsistent

The final diagnostic uses IRC 22:2014 and IRC 112:2011 in design discussion, while other report sections cite IRC 22:2015 and IRC 112:2020. See physical pages 24, 35 and 47 in `diagnostic.pdf`. Since standards year can affect requirements, identify the actual edition used for each check and align the applicable-code list, chapter text, notes and references.

### P2 — README points at missing workflow

`phase22.1-submission-polish/README.md:319` says CI runs via `.github/workflows/ci.yml`. The final commit contains `.github/workflows/conda-publish.yml`, but no `ci.yml`. Update the description or add only the correct workflow reference after verifying the actual CI setup.

### P2 — Source ZIP is not a complete repository snapshot

The nested `source.zip` contains exact final-commit contents for all tracked `src/` and `tests/` files, with zero hash mismatches, but omits 132 other tracked paths, including seven `docs/` files and 16 `examples/` fixtures. The packaged reproduction guide states its archive scope as application source/build metadata/license/web scaffold/test suite. This is not a code mismatch, but call the archive a source-and-test subset rather than a full tree, or include the omitted reference materials if a complete repository snapshot is required.

### P2 — Some design inputs are unavailable

The final report has N/A or blank braking, wind and temperature fields. This is honestly disclosed in the fixture but prevents use as a complete site-specific design report. Preserve as unavailable, not as zero load.

The Phase 22.1 technical report itself describes the unvalidated positive-overhang stiffness, skew self-weight deficit, failed diagnostic, and native CAD capture limitation. That disclosure is accurate and clear. Reproduction instructions include required environment and commands; exact `pytest` invocation is not runnable in this audit environment because pytest is absent.
