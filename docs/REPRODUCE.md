# Reproduce the current AP/CP files offline

The public builder now contains the missing transformation logic and fixed
firmware layout. Given the exact stock C2 2.01 components and a caller-supplied
coefficient triplet, it builds the complete current AP/CP candidate, the inverse,
a generated native manifest and synthetic test fixtures. Optional commands compile
and exercise the full stock-transition helper locally.

**There is no camera connection or deployment command in this workflow.** It
does not download firmware, extract keys, select a coefficient triplet, bind a
camera identity or create an installation session. The generated program files
are not a signed Sony update package. See [inputs](BUILD_INPUTS.md) and the
[tested environment](TESTED_ENVIRONMENT.md) before reproducing the build.

## 1. Prepare local inputs outside the public clone

Use Python 3.12. The program-file builder and its refusal tests use the standard
library only. Open PowerShell at this repository's root:

```powershell
$Repo = (Get-Location).Path
$Private = Join-Path (Split-Path $Repo -Parent) 'pixelshift-private'
New-Item -ItemType Directory -Force -Path (Join-Path $Private 'stock') | Out-Null
Copy-Item -LiteralPath .\examples\build-inputs.template.json -Destination (Join-Path $Private 'inputs.json')
```

Place your lawfully obtained, already-extracted stock `appFw.so` and
`cpapp-b.bin` in that `stock` folder. The builder checks their complete sizes and
hashes against the [fixed profile](../profiles/ilce7cm2-2.01.json). Firmware
container extraction is outside this builder; the [fwtool reference](REFERENCES.md)
provides format context. A whole firmware download cannot be substituted directly
for these extracted components.

Review the copied `inputs.json`. Its **[116, 119, 112]** coefficients are the
owner-authorized final example, in C0/C1/C2 order. They are a starting point
supported by one camera's measurements, not a universally validated calibration.
Keep them deliberately or substitute your reviewed integers; see [tuning](TUNING.md).
Do not substitute another body's complete ordinary calibration records.

Keep this private directory separate from the public repository. The build
refuses an output directory inside the public clone and refuses to overwrite an
existing output directory. On Windows, prefer a short directory path.

## 2. Build and verify

```powershell
python -B .\tests\test_offline_builder.py
python -B .\tools\build_offline.py build --inputs (Join-Path $Private 'inputs.json') --output (Join-Path $Private 'build-01')
python -B .\tools\build_offline.py verify --output (Join-Path $Private 'build-01')
```

Require exit code zero and `OFFLINE_BUILD_OK` / `OFFLINE_VERIFY_OK` before
continuing. Output contains:

| Output | Meaning |
| --- | --- |
| `AP.stock.bin`, `CP.stock.bin` | Copies of the exact caller-supplied originals |
| `AP.candidate.bin`, `CP.candidate.bin` | Full desired program images, generated locally |
| `AP.reversed.bin`, `CP.reversed.bin` | Inverse-applied images, byte-equal to the originals |
| `manifest.json` | Exact ranges, hashes, supplied coefficients and artifact integrity inventory |
| `writer/persistent_manifest.h` | Generated windows and loaded-AP checks for the full transition |
| `writer/fixture/` | Reduced synthetic files and target-ABI test data |
| `native/persistent_writer.c` | Preserved coefficient-independent full-range helper source |

No input file is modified. The profile's AP changes expose native callbacks/menu
choices. CP changes encode the existing profile/feedback behavior and all five
coefficient-load sites. Complete-file input checks are required: the builder does
not search approximately for offsets in a different firmware or another mod.

## 3. Optional native build and execution tests

These steps were checked on the single Windows x64 host described in the
environment record. They require Zig 0.13.0, pyelftools 0.33 and Unicorn 2.1.4.
Use an existing verified installation or install the pinned packages into a
private virtual environment. Package installation is the network-using setup
step; the subsequent build/test commands do not use the network.

```powershell
python -m venv (Join-Path $Private 'env')
$Py = Join-Path $Private 'env\Scripts\python.exe'
& $Py -m pip install -r .\requirements-offline.txt
$Zig = & $Py -c "import pathlib, ziglang; print(pathlib.Path(ziglang.__file__).parent / 'zig.exe')"
& $Py -B .\tools\build_offline.py compile --output (Join-Path $Private 'build-01') --zig $Zig
& $Py -B .\tools\test_offline.py --output (Join-Path $Private 'build-01')
```

Alternatively, set `$Zig` to an existing Zig 0.13.0 executable. Keep its adjacent
`lib` directory; the build uses the target Linux headers and verifies AArch64
open-flag constants. It never substitutes Windows/x86 flags for the target ABI.

Compilation creates an AArch64 ELF helper and a Windows x64 test DLL. The tests
run the DLL with simulated syscalls and execute the actual ELF under Unicorn.
They do not load either binary into a camera. Results are under
`build-01/tests/results/`. The generated native helper is checked for target,
unresolved symbols, external-library dependencies and size.

If compilation fails, retain its output; the already-verified candidate files
remain local. A partially compiled directory is not automatically cleaned or
silently reused. Generate a fresh build directory for a new compile attempt.

## 4. Check reproducibility

Build again into `build-02` using the same input JSON, then compare the complete
candidate files and generated headers. With the same compiler and sources, the
native binaries can be compared too. The recorded reproduction check on this
host produced identical AP/CP candidates and manifests in two output directories,
and the candidates matched the existing working configuration exactly. The actual
AArch64 helper was also byte-identical. The Windows test DLL differed only in
PE timestamps/CodeView debug metadata, so no byte-identical DLL claim is made.
Current validation details are in [offline-reproduction.json](../evidence/offline-reproduction.json).

## What remains before any real installation

The new artifacts have **`body_binding: false`**. A real installer still needs
the owner's own identity/calibration baselines, full-file pre/post-readbacks,
an owning journal, source-state checks, controlled helper staging, snapshot
handling and new-boot verification. Credentials and these private records are
not shipped. Firmware hashes identify a program version, not a physical camera.

The existing `src/v1/host` snapshot is a **CP-only historical updater** with
different state assumptions and write limits. Do not drop the full-install
helper into it or relax its checks. The original private camera workflow remains
unchanged. A capable reviewer now has the full byte-generation logic and helper
source, without having to rediscover the missing patch locations, but adapting
a live installation workflow is still a separate review and authorization task.

The program bytes have matching historical capture evidence on one body. The
newly generated direct stock-to-current helper has offline execution evidence,
not a fresh physical install, boot or interrupted-power recovery demonstration.
