# Reproduce the screening diagnostic

The source archive contains the tracked application source, build metadata, license, web scaffold and test suite from the commit in GIT_REFERENCES.txt. Unpack source.zip in an empty working directory. The commands below start in that extracted directory. Keep the package evidence intact and regenerate into the working copy.

Use the project's Osdag environment with Python 3.12, PySide6, OpenSeesPy, SciPy, the Osdag libraries and pythonocc-core installed. The verified run used Python 3.12.16, PySide6 6.9.3, OpenSeesPy 3.8.0, pythonocc-core 8.0.1.2, SciPy 1.18.1 and Tectonic 0.17.0 on macOS. The source includes environment.yml. Tectonic must be on PATH or supplied through the TECTONIC environment variable. Poppler supplies pdftotext, pdfimages and pdftoppm. Select the Qt Cocoa plugin associated with the active PySide6 installation on macOS. Other platforms were not exercised in this phase.

```sh
export PYTHONPATH=src MPLBACKEND=Agg
# macOS, after activating the Osdag environment
export QT_QPA_PLATFORM=cocoa
export QT_QPA_PLATFORM_PLUGIN_PATH="$(python -c 'from PySide6.QtCore import QLibraryInfo; print(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath) + "/platforms")')"
python -m unittest discover -s tests/unit -p 'test*.py' -v
python tests/phase20/test_phase20_bug25_to_30_conda.py src
python tests/integration/phase22_pdf.py
pdftotext -layout evidence/phase22/pdf/diagnostic.pdf evidence/phase22/pdf/diagnostic.txt
pdfimages -list evidence/phase22/pdf/diagnostic.pdf
```

Copy the eight validation-*.json files from the submission's evidence/phase22 directory into the working copy's evidence/phase22, or regenerate them using the following loop. Then run the acceptance check.

```sh
for i in 0 1 2 3 4 5 3-repeat 4-repeat; do
  python tests/integration/phase22_probe.py "${i%%-*}" "evidence/phase22/validation-$i.json"
done
python tests/integration/check_phase22_evidence.py
```

Expected results are 32 unit tests and six legacy regressions passing, three physical girders in the diagnostic, 85.0 kN/m³ in the PDF, and a FAIL verdict with utilization 2.16. Physical pages 3 and 9 contain the corrected plan and Table 2.7. Physical page 6 records the engineering limitations. Numerical fields can be compared across runs. Timestamps in the generated text, the PDF metadata and table order can change.

Run `shasum -a 256 -c SHA256SUMS` from the submission directory to verify the supplied files. The manifest covers every deliverable except itself. The source patch applies to the preserved Phase 22 commit; from a clean checkout of that commit run `git apply --check /path/to/phase22.1-source.patch` before applying it.
