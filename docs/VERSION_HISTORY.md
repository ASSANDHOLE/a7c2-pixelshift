# One public version, with private history preserved

**Public v1 is the final optically adjusted configuration used in the repeated
and long-series measurements.** The earlier coefficient estimate was a
development starting point, not an intentionally different feature release.
There is one public source tree, `src/v1/`.

| Name in historical private files | Meaning in this public repository |
| --- | --- |
| `A7C2-PixelShift-v1` | Development installation with the initial coefficient estimate; retained privately for its original files, installer and owning session |
| `A7C2-PixelShift-v1.1-update` | The coefficient correction leading to **public v1** |
| `src/v1/` | Byte-preserved review source from that current private coefficient-update package |

The folder rename changes public presentation, not the camera, compiled helpers,
private package manifests or journals. Historical strings inside the preserved
source, including `v1`, still mean the earlier private baseline where that was
their original meaning. Source provenance records keep the actual source paths.

The retained `host/` and `native/` snapshot is the **CP-only coefficient updater**: it expects the
already-enabled historical baseline and leaves AP read-only. Renaming it does
not make it a stock-to-feature installer. Complete original and current private
packages remain available to the owner; the public export lacks their body-bound
build inputs and binaries.

For the owner's existing installation, normal stock restoration remains:

```text
public v1 (historical private v1.1)
    -> undo the private coefficient update; cold start and verify
initial development configuration (historical private v1)
    -> undo the original private installation; cold start and verify
stock 2.01 program files
```

Do not rename or merge the private sessions to match the public label. This
would obscure which source hashes and inverse each session owns. The old public
source copy was removed from this export but preserved in the owner's private
history. The later [offline reproduction workflow](REPRODUCE.md) adds the
coefficient-independent stock-transition helper as a component of public v1 and
generates complete desired files from caller-supplied inputs. It does not alter
the private journals or constitute a newly camera-tested combined installer.
