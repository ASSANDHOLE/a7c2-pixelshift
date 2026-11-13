# How to tune the three step coefficients

The current public v1 values already give approximately one-pixel H/V steps on
the research body. This guide explains how to derive a **small local correction
from a working configuration**, not how to initialize an untested camera from
zero or guess another body's calibration. The owner-authorized starting triplet
is **[116, 119, 112]**, in C0/C1/C2 order. It is the measured one-body example,
not a guarantee that another body's response is identical.

## What to change

The native target generator is approximately:

```text
target = 8192 * [C0 * A, C1 * A, C2 * B]
```

On this body, C0/C1 together primarily set the vertical image step and C2 primarily
sets the horizontal image step. This is an empirical coordinate relationship,
not proof that these are literal actuator X/Y labels.

For a scale correction, **change C0 and C1 by the same multiplier**, keeping their
ratio as close as integer rounding allows. Change C2 only for a repeatable
horizontal scale error. Keep profile 6, feedback selection `(3,1)`, the binary
scale exponent, native timing and saved ordinary calibration unchanged. They
are not additional fine-tuning knobs for this procedure.

## 1. Decide whether the error is a scale error

Use several short-interval four- and sixteen-shot groups from the same setup,
with recorded focus, exposure, trigger, stabilization and environmental conditions.
Measure positions using the [image-registration method](MEASUREMENT_METHOD.md),
then fit the quartet axes. Estimate representative H/V step lengths from the
repeatable groups and retain regional and between-group spreads.

Do not tune from one unusually skewed square, a group-average length alone, a
long-exposure trajectory, or a small residual comparable to measurement scatter.
Check the sixteen-shot half-step placements too: a correct mean one-pixel edge
does not establish that all sixteen positions are correct.

A stable undersized vertical step across groups can motivate a paired scale
correction. Irregular corners, between-quartet offsets or a changing slant may
come from drift, coupling or measurement error and cannot generally be repaired
with one scalar. A fitted drift on the same data is descriptive, not proof that
all remaining error is calibration. There is no established rotation-tuning knob.

## 2. Calculate a candidate

Let `V` and `H` be representative measured step magnitudes in native RAW pixels.
The intended full-step magnitudes are one pixel. A first-order local estimate is:

```text
vertical_multiplier   = 1 / V
horizontal_multiplier = 1 / H

C0_candidate = round(C0_current * vertical_multiplier)
C1_candidate = round(C1_current * vertical_multiplier)
C2_candidate = round(C2_current * horizontal_multiplier)
```

For an axis whose error is not repeatable or exceeds neither measurement nor
repeatability uncertainty, use multiplier **1** instead of adjusting it.

**Example:** a consistently measured vertical step of 0.92 px suggests a paired
multiplier of about 1.087, or an 8.7% increase. Leave C2 alone if the horizontal
step is already acceptable. This example uses a rounded measurement; the
historical correction used the more precise measured vertical scale and was
about 9.3%. It was not a three-axis redesign.

The approximation assumes locally proportional optical response. It does not
prove that large changes, another camera or a different controller state follow
the same relation. If H or V is missing, near zero, or not a clear repeatable
pattern, division by it is not a valid way to invent a candidate.

## 3. Account for integer rounding

The stored candidate values are integers. The original reviewed builder restricts
them to nonzero values in `1..255`; that is an input/representation constraint,
**not evidence that the whole range is safe or useful**. Do not silently clamp
an out-of-range candidate and call it calibrated.

One count represents about `1 / C` of that channel's current target scale.
For the vertical pair, calculate both actual multipliers after rounding:

```text
actual_multiplier_0 = C0_candidate / C0_current
actual_multiplier_1 = C1_candidate / C1_current
```

They should remain close for the paired-scale approximation to hold. Report
their difference instead of hiding it with an average. If rounding leaves the
candidate unchanged, no finer adjustment has occurred. If it would introduce
a significant ratio change relative to the intended correction, retain the
working values rather than claiming a precise scalar correction.

## 4. Prepare the private patch, not a menu edit

The persistent implementation embeds the coefficients in CP instructions; it
does not read an editable public JSON setting each time a photo is taken.
Changing a working-RAM calibration record is not equivalent to updating these
embedded values.

The native pattern has five reviewed coefficient-load sites: C0 appears once,
C1 twice, and C2 twice. Update every site for a changed coefficient, preserving
the intended register and instruction width. The historical paired-vertical
change therefore needed three four-byte instruction windows; changing C2 as
well would alter the required window set and invalidate the old fixed counts.

The offline preparation workflow is:

1. Bind the candidate to the exact current program files, body and saved session
   state. Preserve the complete originals and the current working configuration.
2. Record the proposed triplet and its measurement rationale in a private plan.
   Generate exact before/after CP instruction windows against that known input.
3. Produce the full candidate locally and verify that no unrelated bytes change,
   AP remains identical for this coefficient-only update, and the local inverse
   restores the complete input exactly.
4. Regenerate the private manifest, native header/helper, expected hashes, write
   counts and tests for that specific candidate. The fixed source is not a generic
   arbitrary-value uploader. Editing values in an old manifest without rebuilding
   and reviewing its dependent artifacts is not supported.
5. Review/test the package offline, including mismatched input, interrupted-write
   cases and inverse behavior, before an owner-operated camera stage is considered.

For target-file generation, the public [offline builder](REPRODUCE.md) now accepts
an explicit triplet in a local input file through the documented [input schema](BUILD_INPUTS.md).
It generates the complete desired files from exact stock inputs, including all
five coefficient-load sites, and verifies a complete stock inverse. It does not
generate an automatic live retune for an already-modified camera. A current-to-new
transition still needs its own source-state, journal and write-limit review.

The historical workspace updater is `tools/prepare_pixelshift_v11.py`. Its name
is historical; it is pinned to one private plan and package transition, refuses
to overwrite the existing package and assumes the known three-window change.
It is **not** a public `--set-coefficients` uploader. Do not simply rerun it with
arbitrary values or relax its checks. The new offline builder supplies the formerly
missing generic transformation/header logic; firmware inputs, chosen coefficients,
identity data and live installation sessions must still be supplied or prepared
privately by the responsible owner/reviewer.

## 5. Judge an applied candidate by new measurements

If an owner later elects to test a reviewed candidate, compare repeated groups
under matched conditions after the required cold start and verification. Check
both axis scales, all sixteen sampling positions, ordinary shooting, mode entry/
exit and restoration behavior. Keep the previous working files and the correct
owning journal. An inverse needs an available service path; it is not an
independent emergency boot mechanism.

Stop tuning when the remaining discrepancy is within useful measurement and
repeatability limits. The present approximately 0.006-pixel vertical mean
residual and the later irregular per-frame residuals did not justify another
coefficient change. The owner considers the current performance sufficient.

The approximately 21 °C / 50% RH long series is one operating condition, not a
temperature calibration. A hotter environment may behave differently or similarly.
Use Shortest as the practical starting choice supported by these measurements,
with the documented exceptions and capture constraints. Your mileage may vary.

This documentation update does not schedule a new camera test or change any
installed value, private tool or source snapshot.
