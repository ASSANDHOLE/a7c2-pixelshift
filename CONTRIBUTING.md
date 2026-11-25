# Contributing

Start with offline source review or sanitized observations. State model, firmware,
patch revision, lens/focal length, exposure, ISO, interval, trigger/timer,
stabilization and focus state. Distinguish actual stock from Pixel Shift Off.

For a measured pattern, include native-pixel positions, method, region agreement,
group/frame ordering and whether drift was subtracted. Do not label correlated
regions as independent cameras or report a formal confidence interval without a
defensible statistical model.

Do not upload serials, full backups, calibration, credentials, proprietary
programs, original private photos or absolute home-directory paths. Redact locally
and inspect the entire file before an issue or pull request. Public hashes of
per-body identity records are still identifiers and should stay private.

New device support needs its own firmware trace, per-body preparation, review and
physical evidence. Do not port offsets by model-name similarity. Keep changes small
and preserve an exact inverse. No camera access occurs in this repository's CI.

## Writing up a result

Lead with the reader’s question and the observation that answers it. For a photo
comparison, put the matched crops next to the answer. Identify the baseline,
exposure per frame, total shutter-open time and display magnification. Give an
interpretation readers can check against the picture, then explain what the
experiment leaves uncertain.

Put download links beside the result and list the archive contents before the
recipe that uses them. Introduce each technical term where it first matters.
For example, explain that a shift of 0.9 native pixels means that the same printed
feature moved 0.9 pixels on the original sensor grid between photos.

Use the README as the entry point. Link to an explanation for readers asking
why something works, to a procedure for readers doing a task, and to a reference
for readers looking up a number or file format. Keep the detailed measurement
in one place so other pages can link to it.

These practices draw on [Cornell’s guide to research software READMEs](https://data.research.cornell.edu/data-management/sharing/writing-readmes-for-research-code-software/),
[GitHub’s README guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes)
and the [Diátaxis introduction to documentation types](https://diataxis.fr/start-here/).

## Sentences and paragraphs

Use American English in prose, captions, and chart labels. Keep published titles, code identifiers, and file paths in their original form.

Give each sentence one main idea. Make the subject and verb easy to find. “The sensor moved between exposures” describes the action more directly than “Sensor movement took place between exposures.”

Open each paragraph with the point the reader needs. Follow it with a measurement, example, or explanation that supports that point. For example, a paragraph comparing paper grain can start with which exposure looks smoother, give the two measured percentages, and finish by explaining how paper texture affects the measurement. Start a new paragraph when you move on to color fringing.

For examples and exercises, use Google’s *Technical Writing One*. [Short sentences](https://developers.google.com/tech-writing/one/short-sentences) · [Paragraphs](https://developers.google.com/tech-writing/one/paragraphs)
