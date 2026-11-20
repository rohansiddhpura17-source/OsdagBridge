# Local Draft Issue — NOT POSTED

## Title
[Bug] 3D CAD viewport remains black/empty after same-instance redesign until a component toggle forces redraw

**Status:** LOCAL DRAFT (DO NOT PUBLISH WITHOUT EXPLICIT APPROVAL)  
**Defect ID:** BUG-10 / P8-003 (`CAD-003`, `CAD-005`)  
**Related Existing Issue:** `#85`

## Reproduction
1. In one OsdagBridge instance on commit `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3`, complete a 30 m baseline design.
2. Switch to Plots view (or unlock), change span to 32 m, and click **Design**; then unlock, restore 30 m, and click **Design**.
3. Immediate post-run CAD views (`Retry04` `RUN-05-cad.png`, `RUN-06-cad.png`) show a black/empty viewport while overlay dimension labels update. Toggling any component checkbox triggers geometry redraw (`RUN-04-after-toggle-1.png`).

## Root Cause
1. `src/osdagbridge/desktop/ui/template_page.py` (`_on_design_done`, lines 751–755) called `self.cad_3d_widget.render_3d_cad(...)` **before** `self.cad_3d_view_toggle(force_show=True)`, so OpenCASCADE computed `FitAll()` against an unshown/unsized widget.
2. `src/osdagbridge/desktop/ui/cad_3d.py` (`CAD3DWindow`) and `src/osdagbridge/desktop/ui/utils/custom_3dviewer.py` (`CustomViewer3d`) lacked explicit `MustBeResized()` + `FitAll()` + `Repaint()` + `update()` synchronization when transitioning from hidden to visible.

## Candidate Fix & Verification
- `template_page.py`: call `self.cad_3d_view_toggle(force_show=True)` and `QApplication.processEvents()` prior to `render_3d_cad()`, followed by `self.cad_3d_widget.refresh_viewport(fit=True)`.
- `cad_3d.py`: track `_pending_fit_on_show` and add `refresh_viewport(fit=True)` invoking `MustBeResized()`, `FitAll()`, `Repaint()`, and `viewer.update()`.
- `custom_3dviewer.py`: schedule `_deferred_occ_refresh()` on show/resize when AIS objects exist.
- **Verification:** `test_cad_viewport_refresh_api_and_show_ordering` PASS; `phase12-cad-fix` 3-step observations PASS; `phase12-candidate-integration` 6/6 consecutive runs produce full-size (`871x676`), non-blank OCC dumps (`>2700` center non-background samples, 27+ AIS objects) without any manual toggle.
