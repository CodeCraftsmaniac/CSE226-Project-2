import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

// ═══════════════════════════════════════════════════════════════════════════════
// NSU Degree Audit — Unified Design System
// ---------------------------------------------------------------------------
// Single source of truth for typography, colors, spacing, radii and shadows.
// All screens should consume these tokens rather than hard-coding values so
// the app stays visually consistent and premium across every surface.
// ═══════════════════════════════════════════════════════════════════════════════

// ── Colors ─────────────────────────────────────────────────────────────────────
//
// Re-exported as top-level `k*` constants in `glass_widgets.dart` to preserve
// backwards compatibility with the existing screens, but new code should
// prefer the [AppColors] class.

class AppColors {
  AppColors._();

  // Surfaces
  static const background = Color(0xFF0B1020);
  static const surface = Color(0xFF141B2E);
  static const surfaceHigh = Color(0xFF1B2338);
  static const surfaceMuted = Color(0xFF10172A);

  // Brand
  static const primary = Color(0xFF38BDF8);
  static const primaryDark = Color(0xFF0EA5E9);
  static const accent = Color(0xFF818CF8);
  static const success = Color(0xFF10B981);
  static const warning = Color(0xFFF59E0B);
  static const error = Color(0xFFEF4444);

  // Text
  static const textPrimary = Color(0xFFF4F7FB);
  static const textSecondary = Color(0xFF9AA7BD);
  static const textTertiary = Color(0xFF6A7690);
  static const textInverse = Color(0xFF0C1A2E);

  // Borders
  static const border = Color(0xFF29334A);
  static const borderSoft = Color(0xFF1E2740);
}

// ── Spacing (8pt scale) ────────────────────────────────────────────────────────

class AppSpacing {
  AppSpacing._();

  static const double xs = 4;
  static const double sm = 8;
  static const double md = 16;
  static const double lg = 24;
  static const double xl = 32;
  static const double xxl = 48;

  /// Default horizontal page gutters used by every screen.
  static const double pageGutter = 20;

  /// Safe bottom inset so content clears the floating pill nav.
  static const double bottomSafePad = 112;
}

// ── Radii ──────────────────────────────────────────────────────────────────────

class AppRadius {
  AppRadius._();

  static const double xs = 8;
  static const double sm = 12;
  static const double md = 16;
  static const double lg = 20;
  static const double xl = 24;
  static const double xxl = 28;
  static const double pill = 999;
}

// ── Shadows ────────────────────────────────────────────────────────────────────

class AppShadows {
  AppShadows._();

  static List<BoxShadow> card = [
    BoxShadow(
      color: Colors.black.withValues(alpha: 0.25),
      blurRadius: 24,
      offset: const Offset(0, 8),
    ),
  ];

  static List<BoxShadow> subtle = [
    BoxShadow(
      color: Colors.black.withValues(alpha: 0.18),
      blurRadius: 14,
      offset: const Offset(0, 4),
    ),
  ];

  static List<BoxShadow> nav = [
    BoxShadow(
      color: Colors.black.withValues(alpha: 0.35),
      blurRadius: 24,
      offset: const Offset(0, 10),
    ),
    BoxShadow(
      color: Colors.black.withValues(alpha: 0.18),
      blurRadius: 4,
      offset: const Offset(0, 2),
    ),
  ];
}

// ── Durations ──────────────────────────────────────────────────────────────────

class AppDurations {
  AppDurations._();

  static const Duration fast = Duration(milliseconds: 150);
  static const Duration base = Duration(milliseconds: 220);
  static const Duration slow = Duration(milliseconds: 360);
}

// ═══════════════════════════════════════════════════════════════════════════════
// Typography — Apple-style text scale (adapted to Outfit display face)
// ---------------------------------------------------------------------------
// Five canonical roles exposed via both the Material [TextTheme] and the
// [AppText] helper so screens can pick whichever is more readable in place:
//
//   Large Title · Title · Headline · Body · Caption
//
// The underlying Material slots are still populated so existing `Theme.of
// (context).textTheme.headlineSmall` etc. calls keep working — they're just
// normalised to the Apple-style scale below.
// ═══════════════════════════════════════════════════════════════════════════════

class AppText {
  AppText._();

  // Large Title — hero screen headings
  static TextStyle largeTitle({Color? color}) => GoogleFonts.outfit(
        fontSize: 34,
        fontWeight: FontWeight.w800,
        letterSpacing: -0.6,
        height: 1.15,
        color: color ?? AppColors.textPrimary,
      );

  // Title 1 — major section header
  static TextStyle title1({Color? color}) => GoogleFonts.outfit(
        fontSize: 26,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.4,
        height: 1.2,
        color: color ?? AppColors.textPrimary,
      );

  // Title 2 — card / sub-section header
  static TextStyle title2({Color? color}) => GoogleFonts.outfit(
        fontSize: 20,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.2,
        height: 1.25,
        color: color ?? AppColors.textPrimary,
      );

  // Title 3 — compact header / dialog title
  static TextStyle title3({Color? color}) => GoogleFonts.outfit(
        fontSize: 17,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.1,
        height: 1.3,
        color: color ?? AppColors.textPrimary,
      );

  // Headline — emphasised body copy
  static TextStyle headline({Color? color}) => GoogleFonts.outfit(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.1,
        height: 1.35,
        color: color ?? AppColors.textPrimary,
      );

  // Body — default reading text
  static TextStyle body({Color? color}) => GoogleFonts.outfit(
        fontSize: 15,
        fontWeight: FontWeight.w400,
        height: 1.45,
        color: color ?? AppColors.textPrimary,
      );

  // Callout — slightly smaller emphasised body
  static TextStyle callout({Color? color}) => GoogleFonts.outfit(
        fontSize: 14,
        fontWeight: FontWeight.w500,
        height: 1.4,
        color: color ?? AppColors.textSecondary,
      );

  // Subheadline — secondary metadata
  static TextStyle subheadline({Color? color}) => GoogleFonts.outfit(
        fontSize: 13,
        fontWeight: FontWeight.w400,
        height: 1.4,
        color: color ?? AppColors.textSecondary,
      );

  // Footnote — small supporting text
  static TextStyle footnote({Color? color}) => GoogleFonts.outfit(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        height: 1.4,
        color: color ?? AppColors.textTertiary,
      );

  // Caption — compact label / metadata
  static TextStyle caption({Color? color}) => GoogleFonts.outfit(
        fontSize: 11,
        fontWeight: FontWeight.w500,
        letterSpacing: 0.2,
        height: 1.35,
        color: color ?? AppColors.textTertiary,
      );

  // Eyebrow — uppercase label used above titles
  static TextStyle eyebrow({Color? color}) => GoogleFonts.outfit(
        fontSize: 11,
        fontWeight: FontWeight.w700,
        letterSpacing: 1.6,
        height: 1.2,
        color: color ?? AppColors.primary,
      );
}

/// Convenience getters bound to a [BuildContext]. Rarely needed — prefer
/// `Theme.of(context).textTheme.*` or [AppText] directly.
extension AppTextX on BuildContext {
  TextStyle? get largeTitle => Theme.of(this).textTheme.displaySmall;
  TextStyle? get title1 => Theme.of(this).textTheme.headlineMedium;
  TextStyle? get title2 => Theme.of(this).textTheme.headlineSmall;
  TextStyle? get title3 => Theme.of(this).textTheme.titleLarge;
  TextStyle? get headline => Theme.of(this).textTheme.titleMedium;
  TextStyle? get body => Theme.of(this).textTheme.bodyLarge;
  TextStyle? get callout => Theme.of(this).textTheme.bodyMedium;
  TextStyle? get caption => Theme.of(this).textTheme.bodySmall;
}
