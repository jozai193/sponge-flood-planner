# Verify comparison exports

After a completed comparison, download evidence, report, costs, GeoJSON and manifest from the same comparison. Keep the original filenames together in one directory. The manifest covers the exact UTF-8 bytes of four files; avoid editing or reformatting them first.

Run from the SPONGE project directory:

```powershell
.venv/Scripts/python.exe -m scripts.verify_export "C:/path/to/downloads/sponge-export-manifest.json"
```

A successful verification reports four matching files. A missing, changed or renamed file fails verification. The verifier rejects duplicate names and filenames that escape the export directory.

The manifest includes baseline/planned input hashes, the engine label, storm, bundle identifier and source metadata. The scenario file contains numerical arrays and selected design parameters. GeoJSON describes simulated intervention cells, not surveyed construction boundaries; installation cost appears once per design in its design catalogue.

Checksums compare files with this manifest. They do not authenticate the publisher, independently validate the simulation, or prove source accuracy. Original provider files and model source code are not bundled. Source metadata hashes and engine labels must not be described as a complete reproducible source archive. PDF export and full source/model packaging remain outstanding.
