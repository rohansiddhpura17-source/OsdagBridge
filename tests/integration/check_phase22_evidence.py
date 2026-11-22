"""Check measured Phase 22 evidence after running the documented matrix."""
import json
from pathlib import Path
from math import isclose

root = Path("evidence/phase22")
for i in range(6):
    row = json.loads((root / f"validation-{i}.json").read_text())
    physical = [f"G{n+1}" for n in range(row["case"]["girders"])]
    assert row["physical"] == physical
    assert list(row["sw_peak_kNm"]) == (physical if i == 5 else ["EB1", *physical, "EB2"])
    assert row["rho"] == 1000 * row["case"]["density"]
    assert abs(row["force_balance_kN"]) < 1e-7
    assert abs(row["moment_balance_about_z_kNm"]) < 1e-6
    left, right = map(sum, zip(*row["sw_reactions_kN"].values()))
    for key, value in (("left_kN", left), ("right_kN", right)):
        assert abs(row["report_sw_reactions"][key] - value) <= 0.00051
    if row["case"]["skew"]:
        repeat = json.loads((root / f"validation-{i}-repeat.json").read_text())
        assert row == repeat
        assert not any(w.startswith("RuntimeWarning") for w in row["warnings"])
        print("Skew weight difference (kN)", row["residual_kN"])
    else:
        assert abs(row["residual_kN"]) < 1e-7
    if i == 5:
        sampled = row["sw_peak_kNm"].values()
        for moment, reference in zip(sampled, row["simple_span_kNm"]):
            assert isclose(moment, reference, rel_tol=0.005)
pdf = (root / "pdf/diagnostic.txt").read_text()
backend = json.loads((root / "pdf/backend.json").read_text())
assert "placeholder" not in pdf.lower()
assert backend["design"]["overall_status"] == "FAIL" and "Overall Design Status           Fail" in pdf
assert f'{backend["design"]["max_dcr"]:.2f} (Girder)' in pdf
assert f'{backend["envelope"]["max_bm"]:.3f}' in pdf
assert "85.0 kN/m3" in pdf and "-76.118" in pdf
print("Six numerical records, two repeats and diagnostic PDF checked.")
