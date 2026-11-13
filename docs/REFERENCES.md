# References and upstream updates

Checked 14 November 2026. Upstream descriptions are attributed maintainer claims;
they do not extend this project's hardware validation. Machine-readable pins and
retrieved-text hashes are in [sources.json](../evidence/sources.json).

## Camera research and implementation

| Reference | Use here and distinction |
| --- | --- |
| [QAQLeonard/a7c2-tools](https://github.com/QAQLeonard/a7c2-tools), formerly `a7c2-fl23-research` | Main foundation for service/file-offset installation and startup-snapshot handling. Our implementation remains based on the [MIT revision 7827856](https://github.com/QAQLeonard/a7c2-tools/tree/782785641ca9f8b984940c7274b48706219e0da4), not the current runtime. |
| [Current upstream README, 68a08af](https://github.com/QAQLeonard/a7c2-tools/blob/68a08af8e55da76714a9127fed7f18bcdf0979d4/README.md) | The November 11 update distinguishes published v3.0.3 from the 3.10 development branch, with looks, sound and display work. It does not supply validation of our pixel-shift patch. Current licensing is PolyForm Noncommercial; see [notices](https://github.com/QAQLeonard/a7c2-tools/blob/68a08af8e55da76714a9127fed7f18bcdf0979d4/docs/en/notices.md). No current upstream code was imported into the tested private bundles. |
| [YuuLuo/a7c2-service-preload, 1619f93](https://github.com/YuuLuo/a7c2-service-preload/tree/1619f938663a36d41e72302a8cfee89a0f6acd1a) | Related service-authentication and loader-boundary research, documented for C2 2.01. CC BY-SA 4.0 documentation. Useful architectural context; this project uses its existing native helper route rather than adopting the preload procedure. |
| [injectiver/a7cr-creative-look-tools, 48f3cb6](https://github.com/injectiver/a7cr-creative-look-tools/tree/48f3cb6cb02a1ad1da29f12d7ca97bdad1cb310f) | A related source-only A7CR 2.01 project, with one-body/macOS evidence and private artifacts separated from public research. It concerns Creative Looks, not a source of known-good A7C II PXS coefficients. |
| [masterflai/pmca-re-reloaded, 1a5e2f6](https://github.com/masterflai/pmca-re-reloaded/tree/1a5e2f602d0be3779deed667f0ed4f8a2abf1f09) | Newer Rust desktop/CLI ecosystem reference for Sony USB, settings and firmware tools. Not used or launched here; its broad advertised device support does not validate this patch or an interchangeable undo path. |
| [lzh2016zzz/a7cr-fl23-research, 43ba744](https://github.com/lzh2016zzz/a7cr-fl23-research/tree/43ba74441c8f10459ade41e84a379ad8005e6ef4) | Earlier A7CR component/settings/snapshot comparison. No private A7CR calibration was obtained from it. |
| [ma1co/Sony-PMCA-RE](https://github.com/ma1co/Sony-PMCA-RE) | Protocol and backup-format foundations; historical pinned code and MIT notice retained in the private bundle. |
| [ma1co/fwtool.py](https://github.com/ma1co/fwtool.py) | Firmware container/extraction context. Public firmware was studied offline; no upstream desktop application was run as part of this export. |

Search found the related projects above, but did not establish which unnamed new
repository the owner had in mind or an independently validated public C2
pixel-shift implementation. This is not a claim that no such project exists.

## Official behavior and RAW processing

- [Sony A7CR Pixel Shift Multi Shoot guide](https://helpguide.sony.net/ilc/2370/v1/en/contents/0414M_pixel_shift_shooting.html): supported-camera four/sixteen RAW workflow, separate computer merging, and interval considerations. It is not Sony support for a modified C2.
- [Sony Imaging Edge pixel-shift instructions](https://support.d-imaging.sony.co.jp/app/imagingedge/en/instruction/1_2_about_psm.php): recommends Shortest; describes motion correction and capture-motion artifacts. No claim that Imaging Edge accepts all modified C2 groups.
- [ExifTool Sony tags](https://exiftool.org/TagNames/Sony.html): group/frame metadata interpretation, not optical displacement telemetry.
- [RawTherapee pixelshift.cc](https://github.com/RawTherapee/RawTherapee/blob/b2ee504c47e5e6d5e054395aa12bf1fe43bd1c3c/rtengine/pixelshift.cc) and [agriggio/make_arq](https://github.com/agriggio/make_arq): open-source reconstruction/container references. Linked rather than copied into this export.
- [Handheld Multi-Frame Super-Resolution](https://research.google/pubs/handheld-multi-frame-super-resolution/) and [IPOL reproducible implementation](https://www.ipol.im/pub/art/2023/460/): multi-frame registration/fusion references, not evidence of camera firmware compatibility.
- [PIXLS RAW repository](https://raw.pixls.us/): public Sony reference capture study used during development. The private owner's photos are not published here.

## Drift literature

- [Handel, 2009](https://www.jstage.jst.go.jp/article/ipsjtcva/1/0/1_0_12/_article), DOI 10.2197/ipsjtcva.1.12: camera warm-up image drift correlated with sensor-board temperature.
- [Adamczyk, Liberadzki and Sitnik, 2018](https://www.mdpi.com/1424-8220/18/11/3685), DOI 10.3390/s18113685: temperature-related drift and compensation in industrial-camera measurements, including rigidly mounted experiments.
- [Ferrer et al., 2025](https://www.sciencedirect.com/science/article/pii/S0143816625005147), DOI 10.1016/j.optlaseng.2025.109329: subpixel tracking of CMOS self-heating effects; abstract-level evidence was available in the earlier literature check.

These studies establish plausible mechanisms. They are not stock A7C II
prevalence studies or an acceptance specification for our measured drift rate.

## Dependencies

The private bundles preserve their actual Windows runtime and notices: CPython
3.12.14, PyUSB, libusb-package, Unicorn, pyelftools and Zig, plus image-analysis
libraries including NumPy, SciPy, scikit-image, rawpy/LibRaw, Pillow, tifffile and
Matplotlib. Exact recorded versions are in
[environment.json](../evidence/environment.json). The public export checker uses
only Python's standard library. Do not interpret every archived research library
as a requirement for everyday camera use.

## AI settings documentation

[OpenAI reasoning guide](https://developers.openai.com/api/docs/guides/reasoning)
and [Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
describe model/effort configuration. They do not verify a historical session;
the local record is separately attributed in [AI_RESEARCH.md](AI_RESEARCH.md).
