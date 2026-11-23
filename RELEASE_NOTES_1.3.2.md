# XCloud5 v1.3.2 — New Icon

**Release type:** public release (not pre-release).

## What's changed
- Replaced the public PS4 launcher image with the new **clean Xbox-green XCloud5 logo** (white cloud, Xbox emblem, minimal PlayStation 4 controller with PS mark, XCloud5 lettering and lime-green **5**).
- Cleaned up the artwork to use uniform fills without unwanted background streaks or uneven shading, with a **512×512 PNG** included as `sce_sys/icon0.png` in the PS4 package.
- Kept the Lab edition's separate icon unchanged.
- Updated the packaged application to **XCloud5 1.3.2**, PS4 `APP_VER=01.49`, retaining the public Title ID **XCLD00003** for compatible upgrades.
- Updated the English README and building instructions.
- Retained all previous **v1.3.1** bug fixes, including the Microsoft sign-in TCP timeout update, and previous Xbox Home UI work.

## Download and install

Download `XCloud5-1.3.2-PS4.pkg` from the release **Assets** section. Transfer the package to a GoldHEN-enabled PS4 by USB or FTP and install it using GoldHEN Package Installer. `SHA256SUMS.txt` provides the checksum for the PS4 installer. The automatic *Source code* downloads are source archives, not installable PKG files.

## Validation

The GitHub Actions workflow compiles and packages the app with OpenOrbis v0.5.4 and pinned native dependencies, checks executable safety gates, validates PS4 package metadata and the icon hash, and uploads the installer after confirming the release tag matches its build commit.

**Hardware status:** This new package and its account-login behavior have not yet been independently tested on physical PS4 hardware. This release focuses on the new icon and documentation, not new streaming features.

The project is independent open-source homebrew, not affiliated with Microsoft/Xbox or Sony/PlayStation; the GPL-3.0-only and third-party notices remain in the source tree.
