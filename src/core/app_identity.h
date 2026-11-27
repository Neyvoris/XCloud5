/* SPDX-License-Identifier: GPL-3.0-only */
#pragma once
#include "build_identity.h"

#if X4_PUBLIC
#define X4_DISPLAY_NAME "XCloud5"
#else
#define X4_DISPLAY_NAME "XCloud4"
#endif

/* The app presents the signed updater identity. The transport and
 * media keep their existing compatibility labels. */
#if !X4_VIDEO_PROBE
#undef X4_PRODUCT_VERSION
#undef X4_SOURCE_ID
#if X4_PUBLIC
#define X4_PRODUCT_VERSION "1.3.5"
#else
#define X4_PRODUCT_VERSION "0.7.111-lab"
#endif
#if X4_PUBLIC
#define X4_APP_VERSION "01.52"
#else
#define X4_APP_VERSION "01.79"
#endif
#if X4_PUBLIC
#define X4_SOURCE_ID "4d95830b7a380a8648b669fa200a051e3d6b7f75"
#else
#define X4_SOURCE_ID "3944c196936a584ea4254241be49a1766463975c"
#endif
#endif
