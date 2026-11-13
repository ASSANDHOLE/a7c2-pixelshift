# Risks, causes and recovery limits

The current configuration has repeated working capture evidence on one body.
There is no basis here for assigning a numerical failure probability. The
following distinguishes observed problems from plausible mechanisms and untested
recovery assumptions.

| Situation | Mechanism / evidence | Mitigation and its limit |
| --- | --- | --- |
| Non-square pattern or merge artifacts | Imperfect inferred target scale; interframe drift; demosaic/registration errors; moving subjects | Measure actual RAW positions, align and use suitable intervals. Does not remove intraframe blur or all motion artifacts |
| Large framing change or vibration | Observed in earlier controller/processing configurations; feedback and target paths matter | Current scoped configuration avoids those reported symptoms in repeated trials. Choosing Off stopped the old vibration; this is not a universal recovery guarantee |
| Camera error during a mode/USB transition | Happened in an early trial and cleared on restart | Preserve evidence, stop the experiment, use the reviewed cleanup. A restart cleared that event, not every possible failure |
| Partial or incorrect program instructions | A file write interrupted between instruction windows or an incompatible source can leave code the loader/processor cannot use | Exact-source checks, bounded writes, complete readback, sync and recognized-range inverse reduce risk. Power-loss and arbitrary corruption recovery are not demonstrated |
| Old startup snapshot conflicts with edited files | Stored startup state can load old code/state after a file change | Separate snapshot finalization, full battery cycle and loaded/new-boot checks. An apparent write success alone is insufficient |
| USB service unavailable after a bad boot | Normal service access depends on enough camera software starting | A backup supplies original bytes, not an independent path for sending them. No claim of guaranteed PC-only repair |
| Mixing with another modification/update | Both tools can change AP/CP or expect different complete-file hashes | Return through the correct verified version chain before adopting unrelated changes. Coexistence has not been tested |
| Calibration or privacy exposure | Backups contain body identity and calibration-derived data | Keep private, preserve hashes, share sanitized measurements. This repository does not intentionally rewrite stored calibration |
| Windows photo transfer unavailable | A service-capable driver can replace the normal storage binding | PC driver management or a card reader addresses transfer; unplugging alone does not uninstall a Windows driver. This is separate from camera firmware recovery |

Preserving normal branches in scoped offline tests is useful evidence. It is not
a proof that every ordinary shooting path, accessory, lens, sleep/wake sequence,
temperature or long-duration workload is unaffected. The observed ordinary-shot
drift remains unattributed, not an identified modification defect.

## Disclaimer

This is independent experimental work, without Sony endorsement or a support
commitment. Use only an owned or explicitly authorized device. Assess whether
loss of operation, images, time or repair cost is acceptable before a persistent
change. Do not rely on this camera modification for irreplaceable work without
appropriate independent backups/equipment.

The project makes no promise of fitness, continued compatibility or recovery.
Firmware and third-party intellectual property remain with their owners; this
repository grants no right to redistribute Sony firmware or other people's
backups. Warranty/service consequences depend on the applicable terms and law;
no universal claim that a warranty is automatically void is made. Nothing in the
notice removes rights or liabilities that cannot lawfully be excluded. The
license governs the distributed source, not the camera or proprietary firmware.
