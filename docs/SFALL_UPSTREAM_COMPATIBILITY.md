# Proposing first-class Korean executable compatibility in official sfall

## Verified upstream behavior (as of October 16, 2026)

Source: [sfall-team/sfall](https://github.com/sfall-team/sfall)

- [`sfall/CRC.cpp`](https://github.com/sfall-team/sfall/blob/master/sfall/CRC.cpp) currently accepts fixed CRC32C values `0xE1680293` (US 1.02d) and `0xEF34F989` (US 1.02d with Mash HRP). Other builds require `ddraw.ini` `[Debugging] ExtraCRC`.
- [`sfall/main.cpp`](https://github.com/sfall-team/sfall/blob/master/sfall/main.cpp) already detects CJK-patched executables by `*(DWORD*)0x4CAF23 == 0x225559` and routes them to existing `versionCHI` compatibility behavior.
- The current Korean text engine reconstructs a specific CJK-derived Korean EXE and validates the corresponding CJK signature. Its attached font DLL is not an sfall fork.
- Official sfall changelogs explicitly mention Chinese/Japanese modified executable compatibility fixes. We should preserve those existing fixes.

## sfall translations do not require `ddraw.ini` modification

Source: [`sfall/Translate.cpp`](https://github.com/sfall-team/sfall/blob/master/sfall/Translate.cpp).

Official sfall's `MakeLangTranslationPath` reads the game's `[system] language` setting and its `master_patches` root, then looks for the translation INI at:

```text
<master_patches>/text/<language>/<TranslationsINI filename>
```

With the default `TranslationsINI=.\\Translations.ini`, `language=korean`, and `master_patches=data`, this becomes:

```text
data/text/korean/Translations.ini
```

**Practical consequence:** ship a Korean sfall-message translation at `data/text/korean/Translations.ini` in the separate language pack. Neither `TranslationsINI` nor other sections of `ddraw.ini` need changing to enable sfall's own translated strings on this default path. Existing mods with a non-default `TranslationsINI` or `master_patches` may require their own path layouts; preserve their settings.

The only sfall configuration obstacle for the *fixed modified Korean EXE* is its checksum acceptance. That is what the upstream CRC whitelist request solves. This does not replace the game's normal `fallout2.cfg` `language=korean` selection, Korean font DLL, or separate translated `.msg` files.

## Smallest upstream change

The canonical Korean-patched US 1.02d EXE has sfall CRC32C **`0xFCDC75E0`** in `runtime-manifest.json`, and verified SHA-256 **`151e99194ac403bd8cc188a2f10b5ef994ffe496fb925b1a4c1b7f8fa73f634e`**.

A one-line addition to the `ExpectedCRC` table is proposed in [`upstream/sfall-korean-crc.patch`](../upstream/sfall-korean-crc.patch). This is only for one reproducible Korean executable build, **not arbitrary CRC skipping**.

The same canonical executable is used in the current stock, RPU, Et Tu and Resurrection profiles. It should continue to match the existing `versionCHI` marker, so the initial proposal needs **no new language-specific hooking logic** in upstream sfall.

### Other profiles: separately evaluated

| Korean engine profile | CRC32C | Upstream recommendation |
| --- | --- | --- |
| stock / rpu / ettu / resurrection | `0xFCDC75E0` | First upstream candidate |
| sonora | `0xFF51969F` | Candidate only after mod-owner compatibility testing |
| nevada | `0xE5BF456F` | Candidate only after mod-owner compatibility testing |
| olympus | `0xE81550F3` | Candidate only after mod-owner compatibility testing |
| sonora-dev | `0xFC345277` | Development snapshot: **do not upstream** as a stable supported build |

This whitelist does **not** make incompatible mod EXEs safe, fix CP949 text layout by itself, or remove required mod runtime dependencies.

## Read-only evidence generation

At the repository root, with a **user-owned** Korean-patched executable:

```powershell
python tools/sfall_upstream_evidence.py --list
python tools/sfall_upstream_evidence.py --exe "D:\\Fallout2-Test\\fallout2.exe" --profile stock --output korean-crc-evidence.json
```

The tool refuses an unrecognized file hash and validates CRC32C and the Chinese/Japanese compatibility signature. The generated JSON contains no EXE bytes. Do not upload retail game executables or nonredistributable legacy CJK files to issues.

## Proposed upstream GitHub issue/PR description (English)

**Title: Support the Korean CJK-compatible Fallout 2 executable CRC without requiring ExtraCRC**

Hello sfall maintainers,

We maintain a Korean text-output project for classic Fallout 2. The Korean edition uses a reproducible, CJK-derived Fallout 2 executable plus a standalone Korean font DLL. We intentionally preserve the official sfall `ddraw.dll`, and would like to avoid modifying end users' `ddraw.ini` just to register a known fixed executable.

From your current sources, the relevant paths appear to be `sfall/CRC.cpp` (`ExpectedCRC` whitelist) and `sfall/main.cpp` (existing `versionCHI` signature at `0x4CAF23`). Our Korean build retains the CJK signature, so the existing Chinese/Japanese compatibility handling seems applicable.

For the exact Korean US 1.02d executable:
- SHA-256: `151e99194ac403bd8cc188a2f10b5ef994ffe496fb925b1a4c1b7f8fa73f634e`
- CRC32C: `0xFCDC75E0`
- Binary basis: fixed, verified CJK-compatible executable; not an arbitrary modded EXE
- Text output: standalone Korean `fallout2font.dll`, with CP949 and font-width handling
- Goal: recognize this executable without asking users to set `ExtraCRC`

Would you be willing to include this exact CRC in the upstream accepted executable list, assuming we provide gameplay test results with an unchanged official sfall DLL? A minimal one-line patch is ready. We will provide reproducible hash/CRC evidence rather than distribute the retail or third-party executable.

We also have mod-specific builds with other CRCs, but we suggest discussing those separately after compatibility testing rather than adding all of them without review.\n\nAs an additional packaging improvement, the existing Translate.cpp already automatically resolves `data/text/korean/Translations.ini` for `language=korean` when its filename is left at the default. We will use that language-pack layout instead of changing `TranslationsINI`.

Thank you for supporting Chinese/Japanese modified EXEs already; we'd like Korean support to follow the same approach.

## Before sending or merging upstream

1. Confirm the source-built Korean canonical EXE's SHA/CRC and `versionCHI` signature on the owner's PC.
2. Run the game with an **unmodified** official sfall (no `ExtraCRC`) built with the single-line CRC patch, and confirm Korean menu, dialogues, fonts, saves and interaction.
3. Confirm sfall existing CJK special handling and HRP behavior remain intact.
4. Ask upstream maintainers whether they accept a fixed checksum in `ExpectedCRC`, or prefer a separate explicit version identifier. Their choice determines the final change.
5. **Do not label this as officially supported until upstream maintainers accept and release it.**

This file is a proposal; it has **not** been submitted to sfall-team.
