# Offline build input specification

Start from [build-inputs.template.json](../examples/build-inputs.template.json).
The six keys below are required; unknown keys are refused.

| Key | Accepted input |
| --- | --- |
| `schema` | Integer `1` |
| `model` | Exactly `ILCE-7CM2` |
| `firmware` | Exactly `2.01` |
| `ap_file` | Path to stock `appFw.so`, absolute or relative to the input JSON |
| `cp_file` | Path to stock `cpapp-b.bin`, absolute or relative to the input JSON |
| `coefficients` | Three explicitly supplied nonzero integers in C0, C1, C2 order; `1..255`, with no physical-safety claim for that entire range |

The exact accepted stock components are:

| Component | Bytes | SHA-256 |
| --- | ---: | --- |
| AP | 99,960,744 | `2ea02f7ecbc5bb917316fe8ef4ce5ffd87eb66efaae78ba2ce11420552df539b` |
| CP | 18,090,880 | `f5a477588698ef965748903b8959a39ce4f59ffd4aee4d4234ef1670f56a1428` |

These are hashes of the generic stock firmware components, cross-checked against
the public-firmware extraction. They are not the owner's body identifier or
calibration hashes. A different firmware version or modified input is refused;
no model-porting heuristic is used.

The historical acquisition reference is
[Sony's ILCE-7CM2 firmware support page](https://support.d-imaging.sony.co.jp/www/cscs/firm/?area=jp&lang=jp&mdl=ILCE-7CM2).
The studied 2.01 `BODYDATA.DAT` had SHA-256
`eb4943e6099754d64deaef5047942e9bfe258f232d0b7bc39fa23b3cd10e1e31`.
This is a provenance reference, not a claim that the site's current download
still serves that version. The extracted AP/CP hashes above are the build inputs.

The profile publishes the fixed file offsets, expected generic preimage windows,
AP callback/menu replacements, CP encoder selection, coefficient-load mapping,
loaded-AP fields and relocation anchors. The input example now contains the
owner-authorized **[116, 119, 112]** triplet (C0/C1/C2, decimal). This is the final
one-body setting used for the reported results, offered as an experimental
starting point. The caller can explicitly choose different reviewed values;
the code does not assume a universal camera calibration. Firmware images and
original body calibration records are not published.

`build` always derives the requested configuration **from stock originals**.
For a later retune, a changed triplet yields another complete desired image and
its stock inverse; it does not automatically produce a live current-to-new
update or change the existing camera journal. Those transitions require their
own exact input-state review.

Generated manifests and binaries contain the supplied coefficients and are
private artifacts. They are intentionally written outside the public repository.
The template's values are a real measured example, not a fictional placeholder.
Review their one-body scope before using them; missing or invalid coefficients
are still refused, with no implicit fallback values.
