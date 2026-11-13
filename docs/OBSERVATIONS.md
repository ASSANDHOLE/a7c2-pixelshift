# Development observations

These milestones summarize saved private logs, offline analysis and the owner's
reports. They do not turn unsuccessful intermediate experiments into supported
features. Detailed original sessions are preserved privately.

| Stage | Observation | What it established / did not establish |
| --- | --- | --- |
| Firmware comparison | A7CR/C2 code and menu paths provided candidate locations | Similar firmware sizes alone did not establish IBIS compatibility |
| First read-only pass | Service snapshots were captured; selected-record stability/presence checks were initially false | Parse success alone was insufficient; Windows driver state was separate from camera state |
| First menu activation | Availability changes succeeded, but the expected menu item was absent | The first availability switch was not the whole activation path |
| Early four-frame trials | Four RAWs were saved; one transition produced a camera error cleared by restart | Metadata and frame count were not proof of physical pixel shift |
| Zero/inferred coefficient trials | Selecting PXS produced a large framing displacement, around 310 pixels in one study | Mode-entry offset was distinct from the intended one-pixel sequence |
| Processing-word override | Repeated sensor movement began only after the override; choosing Off stopped it | Removing that control was not a working way to unlock the sequence; later restoration was reported normal |
| Service capture/observation | Ordinary capture with service USB connected was demonstrated; bounded telemetry was then collected | Normal live view in service mode did not alone prove every concurrent inspection safe |
| Capture diagnostics | Internal target/output changes were seen, but early RAW groups lacked the square; some runs stopped on telemetry/cleanup guards | Digital target changes did not establish physical motion; stopped logs were retained and reviewed |
| Matched-feedback experiment | Four-frame optical pattern appeared with the changed feedback choice, without the previous mode-entry jump in that run | Supplied the decisive physical result beyond menu/metadata activation |
| Four/sixteen comparisons | Repeated groups, merged photos and longer-exposure controls were produced | Four-shot detail and sixteen-shot colour/noise benefits were observed; processing and exposure affect appearance |
| Initial persistent development installation | Offset installation, cold start, shooting and normal uninstall succeeded on the research body | Established a normal reversal path, not arbitrary failure recovery |
| Coefficient correction incorporated in public v1 | Three CP instruction windows updated; cold start and repeated four/sixteen patterns checked | Vertical scale moved close to one pixel on this body; the coefficient-update undo has offline tests but no recorded physical demonstration |
| Stability follow-up | Drift also appeared in ordinary electronic, remotely triggered, SS-Off shots with locked focus | PXS capture, physical shutter contact and repeated autofocus were not necessary causes |
| Short/long Off comparison | Short restarts returned about 0.31/0.16 pixel; an earlier long Off gap returned about 1.43 pixels | Supports a slow state/relaxation contribution; does not identify heat or firmware as the sole cause |

## Current interpretation

The feature works in the tested configuration, and the owner has not identified
a current operating fault. That is compatible with retaining specific unresolved
questions: cross-body parameter transfer, image-drift attribution, long-term use,
official updates, interactions with other modifications, and emergency recovery.

Earlier vibration and large mode-entry offsets are historical failures, not
descriptions of the current repeated working captures. Conversely, they should
not be omitted from a development record merely because the final configuration
improved.

No A7CR calibration dump was available. No direct measurement of coil current,
mechanical end stops, or an independently fixed sensor position was obtained.
The evidence is firmware analysis, sampled digital state, RAW registration and
the owner's physical observations.
