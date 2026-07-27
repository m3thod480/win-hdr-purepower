# Windows HDR Shadow Stretch

Windows HDR Shadow Stretch generates a fixed tonal response for the Windows 11
HDR output pipeline:

**Pure Power 2.2 with a mild near-black Shadow Stretch**

The generated ICC/ICM profile affects the final HDR signal sent to the display.
This includes:

- SDR content composed by Windows while HDR is enabled
- Native HDR content within the luminance range modified by the curve
- Desktop applications, games and video that use the affected HDR output path

HDR highlights above the configured SDR white level are left unchanged.

## Why this exists

An identity MHC2 curve appeared too bright when compared with SDR mode.

Standard Pure Power 2.2 produced a much closer overall tonal match, but it
compressed the lowest luminance levels slightly too much. In near-black
gradients, the image reached apparent black sooner than it did in SDR.

Windows HDR Shadow Stretch keeps Pure Power 2.2 as the base response and
partially relaxes its correction only in the first 10 nits.

The final curve was selected through direct visual comparison of near-black
gradient patterns in SDR and HDR display modes.

## Final tonal response

The supported configuration is fixed:

- Pure Power gamma: `2.2`
- Shadow Stretch end: `10.0` nits
- Shadow Stretch strength: `0.25`

The resulting behavior is:

| Input luminance | Applied response |
|---|---|
| `0–10 nits` | Pure Power 2.2 with mild Shadow Stretch |
| `10 nits–SDR white` | Standard Pure Power 2.2 |
| At SDR white | Returns to identity |
| Above SDR white | Identity; HDR highlights remain unchanged |

Shadow Stretch does not replace Pure Power. It is a localized adjustment applied
on top of Pure Power near black.

Both operations are combined into one final LUT. Windows does not apply two
separate profiles or two separate transformations.

The gamma, Shadow Stretch end and Shadow Stretch strength are intentionally not
configurable. The project provides one visually tested and reproducible tonal
response rather than multiple presets.

## Requirements

- Windows 11
- HDR enabled on the target display
- Python `3.12` or newer
- An ICC/ICM template containing an MHC2 tag
- Exactly `1024` LUT entries per MHC2 channel

No external runtime dependencies are required.

## Installation

Clone the repository and enter its directory:

```powershell
git clone https://github.com/m3thod480/win-hdr-shadow-stretch.git
cd win-hdr-shadow-stretch
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the project in editable mode:

```powershell
python -m pip install -e .
```

## Generate a profile

Use an ICC/ICM profile with a 1024-entry MHC2 tag as the template:

```powershell
python -m hdrfix.generate_profile `
  TEMPLATE.icm `
  output\HDR-Shadow-Stretch.icm
```

The default SDR luminance range is:

```text
SDR black: 0 nits
SDR white: 100 nits
```

Specify the SDR white level explicitly when required:

```powershell
python -m hdrfix.generate_profile `
  TEMPLATE.icm `
  output\HDR-Shadow-Stretch.icm `
  --sdr-white 100
```

Available optional arguments:

```text
--sdr-white NITS
--sdr-black NITS
--force
```

Use `--force` to overwrite an existing output file:

```powershell
python -m hdrfix.generate_profile `
  TEMPLATE.icm `
  output\HDR-Shadow-Stretch.icm `
  --force
```

The following parameters cannot be changed from the command line:

```text
Pure Power gamma:       2.2
Shadow Stretch end:     10.0 nits
Shadow Stretch strength: 0.25
```

## Template requirement

Windows HDR Shadow Stretch v0.1 requires an MHC2 template containing exactly
`1024` LUT entries per channel.

The current patcher replaces the LUT values already present in the MHC2 tag. It
does not resize or reconstruct the tag.

Two-entry identity profiles produced by Windows HDR Calibration are therefore
not suitable as templates. Two endpoints can describe an identity line, but
cannot represent the near-black transition of the final curve.

The LUT entry count is read directly from the template rather than selected on
the command line.

A compatible template can be inspected before use:

```powershell
python -m hdrfix.inspect TEMPLATE.icm
```

Confirm that the output reports:

```text
MHC2 present
LUT entries: 1024
```

## What the generator does

The profile generator:

1. Opens and validates the template ICC/ICM profile.
2. Reads the existing MHC2 structure.
3. Confirms that the template contains 1024 LUT entries.
4. Generates the fixed Pure Power 2.2 + Shadow Stretch curve.
5. Quantizes the curve to the numerical format used by MHC2.
6. Writes the same LUT to the red, green and blue channels.
7. Preserves the remaining profile structure.
8. Recalculates the ICC Profile ID.
9. Writes the result through a temporary file.
10. Reopens and reparses the generated profile for validation.

The original template is never modified.

Missing output directories are created automatically. Existing output files are
not overwritten unless `--force` is supplied.

The tool also rejects attempts to use the same file as both the template and
the output.

## Inspect a generated profile

Inspect the generated profile without modifying it:

```powershell
python -m hdrfix.inspect output\HDR-Shadow-Stretch.icm
```

The inspector can report information such as:

- Presence of the MHC2 tag
- Minimum and maximum luminance metadata
- Number of LUT entries
- Red, green and blue LUT data
- Whether the LUT is an identity transformation
- Whether all three channels use the same curve

## Compare profiles

Compare two ICC/ICM profiles:

```powershell
python -m hdrfix.compare `
  TEMPLATE.icm `
  output\HDR-Shadow-Stretch.icm
```

This can be used to confirm that the output profile contains a different MHC2
curve while preserving the expected profile metadata.

## Analyze the tonal curve

Run the numerical curve analysis:

```powershell
python -m hdrfix.analyze_curves
```

The report compares:

- The internal Pure Power 2.2 base
- The final Pure Power 2.2 + Shadow Stretch response

It reports:

- Representative input luminances
- Pure Power output luminance
- Final Shadow Stretch output luminance
- Delta from identity for each curve
- Shadow Stretch difference from Pure Power
- Maximum difference between both responses
- Input luminance where the maximum difference occurs
- Number of quantized MHC2 LUT entries that differ

The analysis is intended to verify the implementation and quantify the
near-black adjustment. It is not a measurement of the physical display output.

## Profile installation

Profile installation and display assignment remain manual.

Windows HDR Shadow Stretch does not:

- Install ICC/ICM profiles automatically
- Assign profiles to a monitor
- Change Windows color-management settings
- Enable or disable HDR
- Request administrator privileges
- Modify the source template

Generate and inspect the profile before installing it through the appropriate
Windows color-management interface.

Keep a known-good profile available so the original configuration can be
restored.

## Native HDR behavior

This profile is not limited to SDR content displayed while HDR is enabled.

The MHC2 LUT affects the HDR output response, so native HDR values inside the
modified luminance range are affected as well.

With the default `100-nit` SDR white level:

- Native HDR shadows below 10 nits receive Pure Power with Shadow Stretch.
- Values between 10 and 100 nits receive standard Pure Power 2.2.
- Values above 100 nits remain unchanged.

This preserves HDR highlights while changing the lower part of the HDR tonal
response.

## Tests

Run the complete test suite:

```powershell
python -m pytest
```

The tests cover:

- ST.2084 PQ-to-nits conversion
- Nits-to-PQ conversion
- Pure Power 2.2 generation
- Fixed Shadow Stretch behavior
- LUT monotonicity and valid range
- MHC2 quantization
- ICC/MHC2 parsing
- Replacement of all three LUT channels
- ICC Profile ID calculation
- Atomic profile writing
- Output-path validation
- Command-line behavior
- Generated-profile reparsing

## Project scope

Windows HDR Shadow Stretch provides one visually selected tonal correction for
the Windows HDR output pipeline.

It is intended to improve the relationship between:

- An identity MHC2 response that appears too bright
- Standard Pure Power 2.2, which provides stronger contrast but may compress
  near-black separation
- A mildly relaxed near-black response that more closely resembles the tested
  SDR appearance

This project is not a replacement for instrument-based display calibration.

Results may vary depending on:

- Display technology
- Monitor firmware
- HDR mode
- Peak luminance
- Black-level behavior
- GPU driver
- Windows version
- Application color-management path
- Content mastering

The fixed configuration was selected through visual testing on a specific HDR
display and should be treated as a reproducible tonal adjustment rather than a
universal scientific calibration.

## Current limitations

Version `0.1` currently:

- Requires a 1024-entry MHC2 template
- Cannot resize a two-entry MHC2 tag
- Does not build a complete ICC profile from scratch
- Does not install or assign profiles automatically
- Uses the same tonal LUT for all three RGB channels
- Does not implement dithering
- Does not alter display gamut or color primaries

Dithering and MHC2 tonal correction are separate concerns. This project
currently addresses only the tonal response stored in the profile.

## Development status

The current implementation includes:

- ICC/MHC2 inspection
- Profile comparison
- ST.2084 conversion
- Verified Pure Power 2.2 reproduction
- Fixed mild Shadow Stretch
- Full LUT generation
- Numerical curve analysis
- Safe ICC/ICM patching
- ICC Profile ID recalculation
- Command-line profile generation
- Automated tests

The next major improvements may include:

- Building a 1024-entry MHC2 tag from scratch
- Supporting two-entry Windows HDR Calibration profiles as source templates
- Optional Windows profile installation and assignment
- Display detection
- A graphical user interface
- Additional validation across different HDR displays

## Disclaimer

Use generated profiles at your own risk.

Always keep the original template and a known-good display configuration.
Incorrect color-profile assignment can produce unexpected brightness, contrast
or color behavior, but generated files can be removed and the previous profile
restored through Windows color-management settings.