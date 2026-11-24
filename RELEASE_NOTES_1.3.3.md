# XCloud5 v1.3.3 — Russian UI & Update Fix

**Stable PlayStation 4 / GoldHEN package.** This release corrects public update routing and adds Russian localization.

## Changes

- The **public** GitHub release check is now `api.github.com/repos/Neyvoris/XCloud5/releases/latest`; downloadable release assets are requested only from `github.com/Neyvoris/XCloud5/releases/download/...`. Lab keeps its separate upstream XCloud4 channel.
- Added **Русский** in Settings → Interface → Language. The selection is saved alongside previous languages, with the existing numeric language preference codes preserved. A PS4 set to Russian (system language ID 8) defaults to Russian UI.
- Generated and checked **every Russian UI translation slot** and the game/auth/network stage-message translation map. Format placeholders (for example `%u` and `%s`) are checked to prevent crashes.
- Expanded embedded Noto Sans/Inter font atlases for Cyrillic, including Ё/ё and №, with a strict 4 MiB memory budget check. Previous six languages stay available.
- Updated public About screen metadata and GitHub source link to the current XCloud5 project.
- Public version **1.3.3**; PS4 `APP_VER=01.50`; Title ID **`XCLD00003`** unchanged for upgrade compatibility.

## Install

1. Download `XCloud5-1.3.3-PS4.pkg` and optionally `SHA256SUMS.txt` from this release.
2. Install the PKG using GoldHEN's Package Installer.
3. In XCloud5, open Settings → Interface → Language → **Русский**, then save.

**Important security/verification notes:** The release check now points at the correct repository, but automatic in-app installation remains restricted to releases with cryptographically signed update manifests. A bare PKG and checksum text file are **not** an authenticated automatic update; use the manual install path. The installer never bypasses TLS, package identity, signature or SHA-256 checks. Build success does not prove full Microsoft authentication or gameplay compatibility on a real PS4; please report console observations without sharing account secrets.

The full GPL-licensed source is available in the automatically generated Source code archives for this tag.
