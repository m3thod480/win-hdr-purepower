# HDRFix

HDRFix generates one supported HDR tonal response:

**Pure Power 2.2 + fixed mild Shadow Stretch**

The curve was selected through direct visual comparison between SDR and HDR.
Identity looked too bright, while standard Pure Power matched the general SDR
appearance but compressed near-black detail slightly too much. The final Shadow
Stretch relaxes that correction only across the first 10 nits, by a fixed
strength of 25%, then returns exactly to Pure Power.

The fixed configuration is:

- Pure Power gamma: `2.2`
- Shadow end: `10.0` nits
- Shadow strength: `0.25`

These values are intentionally not configurable.

## Generate a profile

Use an ICC/ICM profile containing an MHC2 tag as the template:

```powershell
python -m hdrfix.generate_profile TEMPLATE.icm OUTPUT.icm
```

Optional arguments are limited to the SDR luminance range and overwrite safety:

```text
--sdr-white NITS
--sdr-black NITS
--force
```

The LUT entry count is read from the template. HDRFix writes the same generated
LUT to all three MHC2 channels, recalculates the ICC Profile ID, writes the
result safely, and reparses it for validation. Existing output files are not
overwritten unless `--force` is supplied, and the template itself is never
modified.

HDRFix does not install profiles or change Windows color settings.

## Analyze the curve

The numerical report compares the internal Pure Power base with the final fixed
Shadow Stretch:

```powershell
python -m hdrfix.analyze_curves
```

It reports representative luminance samples, deltas from identity, the
Shadow Stretch difference from Pure Power, the maximum difference and its input
luminance, and the number of quantized LUT entries that differ.

## Tests

```powershell
python -m pytest
```
