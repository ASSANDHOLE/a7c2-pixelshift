# How measured displacement is calculated

**The displacement comes from matching image content in the RAWs.** Sony's group
ID, frame number and frame count identify a sequence; they do not provide the
optical motion values used in these plots. No physical position encoder, coil
current or actuator-travel measurement is claimed.

## Coordinate convention and reference

Coordinates are native RAW sensor pixels, before rotating the image for display:
`dy > 0` means scene content moved down, and `dx > 0` means it moved right.
Sensor motion relative to a fixed optical image has the opposite sign. The
measured scene movement can also arise from the body, lens, support or subject.

A common first ordinary image is used to retain long-term framing drift across
the series. Each PXS group is also registered directly against its own first
frame for within-group geometry. These are separate comparisons; differences
between compressed ordinary RAWs and uncompressed PXS RAWs can affect registration.
The reference position is defined to be zero, not independently measured as zero.

## Coarse-to-fine matching

1. **Decode without changing the source.** Read the visible RAW mosaic and Bayer
   layout with rawpy/LibRaw. Subtract the appropriate black levels and normalize
   signal levels. Extract the two green CFA phases. Separately create linear
   demosaiced RGB with unity white balance, no automatic brightening and no
   display rotation; its green channel is a cross-check.
2. **Locate large displacement first.** A filtered, downsampled green overview
   estimates whole-frame translation. It has one sample per eight native pixels.
   No one-pixel bound or ideal PXS pattern is imposed. Round this coarse result
   to an even native-pixel crop offset so Bayer phases remain consistent.
3. **Match textured regions.** Use 512×512-native-pixel regions. The long series
   uses four printed-text regions; no images of those regions are published.
   CFA planes have half the sampling resolution of the RGB green regions.
4. **Filter and correlate.** Subtract a Gaussian blur at 12 native pixels from
   a narrower blur at either 1.5 or 3 native pixels, subtract the mean and apply
   a Hann window. The existing implementation calls scikit-image's
   `phase_cross_correlation` with `normalization=None` and `upsample_factor=100`:
   FFT cross-correlation with subpixel refinement, not phase-only whitening.
5. **Convert to scene displacement.** The correlation returns the shift that
   aligns the moving crop to the reference. Negate that shift, multiply by the
   sampling scale (1 for RGB, 2 for CFA), then add the difference between the
   even-integer crop offsets.
6. **Check and summarize.** Regions require finite coordinates, matched
   correlation above 0.9 and filtered texture above 0.001 in the normalized
   units. Report the coordinate-wise median of usable regions, their spread,
   and agreement between CFA/RGB and the two filtering scales. The primary
   summary is linear RGB green at the 3-native-pixel filtering scale.

In abbreviated form:

```text
scene_displacement(region) = crop_offset_difference - sample_scale * alignment_shift
reported_frame_position   = coordinate_wise_median(usable_region_displacements)
```

The refinement grid corresponds to about 0.01 native pixel for RGB and 0.02 for
CFA. **That is numerical resolution, not demonstrated measurement accuracy.**
The region thresholds likewise are screening rules, not an uncertainty estimate.
Common texture, filtering and demosaic biases can survive method agreement.

## Deriving step size, shape error and drift

For each quartet, an affine fit maps the nominal square coordinates to measured
positions. The lengths of the fitted horizontal and vertical basis vectors are
reported as H/V step sizes. This is a summary of measured positions; it does not
replace those positions with a square. Unequal edges, skew and within-quartet
deviation are retained in the underlying numerical data.

For an entire sixteen-shot group, let `p_i` be the measured position and `q_i`
the corresponding ideal one-/half-pixel position. A framing-independent error is:

```text
e_i = (p_i - q_i) - mean(p - q)
RMS = sqrt(mean(dot(e_i, e_i)))
worst_point = max(length(e_i))
```

This removes only a common translation. The square-regularity comparison fits
translation, rotation and one uniform scale; it does not fit shear. The separate
linear-drift comparison uses actual elapsed capture times:

```text
p_i = q_i + translation + velocity * time_i + residual_i
```

Ordinary least squares estimates the translation and two-component velocity.
The corrected plot removes that fitted velocity and recenters the sequence.
It does not independently move every frame to its ideal location. A secondary
model also allows one fixed affine grid, explicitly reported separately.

These fits can absorb sequence-dependent placement effects as well as real
movement. Native pattern order and time are linked. Reduced residual error on
the same samples is not proof that the fitted velocity is thermal or mechanical
drift, nor proof that a reconstructed photograph has gained the expected resolution.

## Reproducibility and limitations

The public [long-series data](../evidence/long-series.json) contain anonymous
frame indices, relative timestamps, measured positions and fit summaries, allowing
the numerical summaries to be inspected or recomputed. Original RAWs remain
private, so the public export alone cannot independently repeat image registration.
There are no original photos, region crops or image previews in this report.

The existing analysis-workspace functions are `load`/`compare` in
`analyze_coefficient_trial_images.py`, `estimate` in
`capture_registration_scales.py`, and `fit` in `check_persistent_pose.py`.
The nominal sixteen-position sequence comes from `reconstruct_test7.py`.
Their source hashes are recorded with the numerical evidence; these analysis
modules are not part of the public camera-writer source snapshots.

Spatial regions, Bayer phases and processing methods are correlated; their
spread is descriptive, not a formal 95% confidence interval. Global image
translation also does not identify which physical component moved. Small
rotation, scale change, lighting change, blur and scene movement can affect
different regions differently. Between-frame alignment cannot remove blur
within an exposure.
