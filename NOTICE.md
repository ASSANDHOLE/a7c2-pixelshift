# Attribution and redistribution boundaries

The persistent writer is adapted from the camera-side offset-installer example
in QAQLeonard's A7C II research at commit
`782785641ca9f8b984940c7274b48706219e0da4`. That revision's MIT license is
preserved in [licenses/A7C2-upstream-MIT.txt](licenses/A7C2-upstream-MIT.txt).
Protocol/backup work also draws on Sony-PMCA-RE; its MIT notice is preserved in
[licenses/Sony-PMCA-RE-MIT.txt](licenses/Sony-PMCA-RE-MIT.txt).

The current QAQLeonard repository has a different license, PolyForm Noncommercial
1.0.0. This export does not relabel its new code as MIT or incorporate the current
runtime. References to other repositories grant no license to their content.
The service-preload documentation is CC BY-SA 4.0 and is linked as a reference;
its text is not vendored into the public export. RawTherapee and other processing
implementations likewise remain references with their own licenses.

Project-authored analysis, modifications and documentation use the root MIT
license. Original code notices remain intact. Public source snapshots are copied
byte-for-byte from the private release source files; provenance records their
hashes. The fixed build profile includes the minimal generic preimage windows,
offsets and runtime anchors needed to describe the transformation; no complete
Sony program/firmware image is included. Body-specific generated manifests,
private calibration and service credentials are omitted. The private distributions retain their
third-party runtime licenses and are not relicensed as a single public archive.

Sony names identify the studied device. This project has no Sony affiliation.
No license for redistributing Sony firmware, signed updates, original camera
programs or another owner's backups is asserted.

`tools/build_offline.py` adapts the project's existing patch encoders/header
generation to explicit local inputs. `src/v1/offline/native/install_writer.c`
and `tests/support/` retain the earlier reviewed full-range writer/test sources
and their upstream attribution. The profile was cross-checked against the
generic public-firmware extraction, with all body-specific coefficient values
replaced by explicit caller input. No new rights to Sony's generic firmware
windows are asserted by this project's MIT license.
