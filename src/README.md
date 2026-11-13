# Source snapshot scope

`v1/` is the single public source tree for the current configuration. Its `host/`
and `native/` directories preserve the historical private coefficient-update
source byte-for-byte. The added `offline/native/install_writer.c` is the
coefficient-independent full-range writer used by the new offline build recipe;
it is an implementation component, not another public feature version.

The existing `host/` + `native/` review snapshot is CP-only and requires the already-enabled development baseline;
its AP reference is immutable. It is not a newly combined stock installer. The
old `v1` names inside source messages refer to that historical private baseline,
not the renamed public release. See [version mapping](../docs/VERSION_HISTORY.md).
Do not run that host entry point from this export or substitute the newly built
full-install helper into it.

The original private application expects generated body-bound files under
`data/private/device`, a reviewed integrity manifest, the original/candidate
programs, vendor transport material, runtime/SDK dependencies and its saved
sessions. Those remain absent. The new public `tools/build_offline.py` generates
the full-stock-transition `persistent_manifest.h`, candidates, inverse and
fixtures from explicit local inputs. It does not fabricate the private
application's body binding, credentials, review seal or owning journal.

The useful review entry points are:

- `v1/host/a7c2_persistent.py`: version-bound state machine, preparation, write,
  snapshot finalization, new-boot checks and undo.
- `v1/host/check_persistent_package.py`: recognize stock/candidate/known mixed
  bytes, refuse unowned changes, reconstruct the original locally.
- `v1/host/persistent_writer_protocol.py`: fixed allowed operations and reports.
- `v1/native/persistent_writer.c`: exact-file checks, bounded write/inverse order,
  synchronization and cleanup.
- `v1/native/persistent_maps.inc` and `a7c2_linux_abi.h`: mapping parser and target
  ABI assumptions retained from the reviewed implementation.
- `v1/offline/native/install_writer.c`: preserved full-range helper source,
  compiled only by the separate offline workflow.
- `../tools/build_offline.py` and `../profiles/ilce7cm2-2.01.json`: complete fixed
  transformations, input hashes and generated native layout.
- `../tools/test_offline.py`: existing simulated native and actual-ELF tests
  adapted to the generated artifact directory; no USB module is imported.

The source provenance index identifies copied files. With caller-supplied stock
components and coefficients, the public tree can now reproduce the complete
program candidates and helper offline. It includes the owner-authorized example
triplet but does not ship firmware, original body records or a self-contained
live installer. The new build's generated
direct-transition helper was tested offline; historical physical observations
belong to the owner's separate staged workflow.
