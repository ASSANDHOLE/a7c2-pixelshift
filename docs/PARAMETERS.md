# Parameters: what the numbers do and what is inferred

**All coefficient choices in this project come from one camera.** No A7CR
owner's pixel-shift calibration was obtained. The initial values were inferred
from the research body's ordinary stabilization calibration; a later optical
measurement motivated an approximately 9.3% paired vertical increase.

The native target expression is approximately:

```text
target_channels = 8192 * [C0 * A, C1 * A, C2 * B]
first four (A, B) = (0,0), (2,0), (2,2), (0,2)
sixteen = four related quartets with native half-step base offsets
```

| Parameter | Interpretation supported here | Caution |
| --- | --- | --- |
| C0 and C1 | Paired coefficients for the A target; mainly vertical image displacement in native RAW coordinates in these tests | They are not proven literal sensor X/Y actuator labels; changing their ratio may introduce coupling |
| C2 | B target; mainly horizontal image displacement here | It is not a universal horizontal-pixels-per-unit calibration |
| Scale exponent 13 | Multiplication by 8192 | Incrementing the exponent doubles the target; unsuitable for a small geometric correction |
| Profile 6 | Choice of controller configuration on the PXS path | A mode selector, not a fine adjustment |
| Feedback pair `(3,1)` | Selection used by the physically working trials | Must not be confused with the three step magnitudes |
| Native interval | Time scheduling between captures | Shortest is the nominal 0.5-second entry; actual timestamps also reflect exposure and camera operation |

## Published starting values

With the owner's explicit permission, the final optically adjusted values are:

```json
"coefficients": [116, 119, 112]
```

The order is **C0, C1, C2**, all decimal. These are the values behind the reported
public-v1 measurements and are included in the build input example as a starting
point for other researchers. They are inferred/tuned on one body, not Sony's
factory PXS calibration. Suitability and optical accuracy on other bodies have
not been established; keep the one-body and environmental limits in view.

Only this final three-value triplet is authorized for publication. Original
calibration records, camera identity, backups, credentials and photos remain
private. The generic builder still takes explicitly supplied values rather than
silently selecting a triplet.

## Why the original result was not a perfect square

The initial development estimate gave a vertical step of about 0.92 native pixel
in a repeated study. Two inference
methods agreeing on the initial triplet did not validate the conversion to actual
optical displacement. Public v1 incorporates the correction of that measured
scale discrepancy on this body.
Image drift, perspective/registration effects and cross-axis coupling remain
mixed in small residual skew; a camera pointing downward does not by itself
explain a repeatable image-plane sensor-step scale error.

The horizontal slant cannot be assigned to C0/C1 simply because they are unequal:
a left-to-right target transition changes B/C2 while A can remain fixed. No
independent rotation calibration knob was established.

## How further tuning should be assessed

Use multiple four- and sixteen-shot groups, several textured image regions and
both CFA and demosaiced registration. Keep exposure, focus and support conditions
recorded. Compare short intervals first so gradual image drift is less mixed
with the step. Report region agreement and repeatability, without treating
correlated regions or processing methods as independent cameras.

A roughly 0.006-pixel mean residual after that correction was not a reason to tune again.
The observed spread and setup changes are larger. Ordinary-shot controls and
actual-stock controls answer different questions: PXS Off does not uninstall
the persistent modification.

The later [long series](LONG_SERIES.md), reported at about 21 °C / 50% RH, keeps
the same coefficients. Its interval comparison supports Shortest as a practical
default for static ambient-lit scenes, especially sixteen-shot capture, with
exceptions and measurement uncertainty. No cross-temperature calibration or
universal warm-up time is established; results in other conditions may differ.

For the concrete scaling formula, integer rounding, worked example and private
package preparation steps, see [How to tune the parameters](TUNING.md).
