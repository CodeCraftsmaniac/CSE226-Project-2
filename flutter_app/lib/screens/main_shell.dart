import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../services/auth_service.dart';
import '../widgets/glass_widgets.dart';
import 'auth_screen.dart';
import 'courses_screen.dart';
import 'dashboard_screen.dart';
import 'health_screen.dart';
import 'history_screen.dart';
import 'upload_screen.dart';

// ═══════════════════════════════════════════════════════════════════════════════
// MainShell
// ---------------------------------------------------------------------------
// Hosts the four core pages and drives navigation via a modern, iOS-style
// floating pill navigation bar. The design system tokens in
// `design/app_design.dart` are the single source of truth for colors, radii
// and spacing used here.
// ═══════════════════════════════════════════════════════════════════════════════

class MainShell extends StatefulWidget {
  const MainShell({super.key, this.initialIndex = 0});

  final int initialIndex;

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  late int _currentIndex;
  late final PageController _pageController;

  // ── Navigation items ──────────────────────────────────────────────────────
  //
  // Only core user-facing flows occupy the pill bar. Health — a diagnostic /
  // admin surface — is accessible via the profile menu instead.
  static const List<_NavItem> _navItems = [
    _NavItem(
      label: 'Results',
      icon: Icons.space_dashboard_outlined,
      activeIcon: Icons.space_dashboard_rounded,
      accent: AppColors.primary,
    ),
    _NavItem(
      label: 'Upload',
      icon: Icons.upload_file_outlined,
      activeIcon: Icons.upload_file_rounded,
      accent: AppColors.success,
    ),
    _NavItem(
      label: 'Courses',
      icon: Icons.menu_book_outlined,
      activeIcon: Icons.menu_book_rounded,
      accent: AppColors.accent,
    ),
  ];

  static const List<Widget> _screens = [
    DashboardScreen(),
    UploadScreen(),
    CoursesScreen(),
  ];

  @override
  void initState() {
    super.initState();
    _currentIndex = widget.initialIndex.clamp(0, _navItems.length - 1);
    _pageController = PageController(initialPage: _currentIndex);
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _onNavTap(int index) {
    if (_currentIndex == index) return;
    HapticFeedback.selectionClick();
    setState(() => _currentIndex = index);
    _pageController.animateToPage(
      index,
      duration: AppDurations.slow,
      curve: Curves.easeOutCubic,
    );
  }

  Future<void> _handleLogout() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Sign Out'),
        content: const Text('Are you sure you want to sign out?'),
        actionsPadding: const EdgeInsets.fromLTRB(
          AppSpacing.md,
          0,
          AppSpacing.md,
          AppSpacing.sm,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: kError),
            child: const Text('Sign Out'),
          ),
        ],
      ),
    );

    if (confirm == true && mounted) {
      await authService.logout();
      if (!mounted) return;
      _navigateToAuthScreen();
    }
  }

  Future<void> _handleExitGuestMode() async {
    await authService.exitGuestMode();
    if (!mounted) return;
    _navigateToAuthScreen();
  }

  void _navigateToAuthScreen() {
    Navigator.of(context).pushAndRemoveUntil(
      PageRouteBuilder(
        pageBuilder: (context, animation, secondaryAnimation) =>
            const AuthScreen(),
        transitionsBuilder: (context, animation, secondaryAnimation, child) =>
            FadeTransition(opacity: animation, child: child),
        transitionDuration: const Duration(milliseconds: 400),
      ),
      (_) => false,
    );
  }

  void _handleMenuSelection(String value) {
    switch (value) {
      case 'logout':
        _handleLogout();
        break;
      case 'history':
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const HistoryScreen()),
        );
        break;
      case 'health':
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const HealthScreen()),
        );
        break;
      case 'signin':
        _navigateToAuthScreen();
        break;
      case 'exit_guest':
        _handleExitGuestMode();
        break;
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = authService.currentUser;
    final isGuest = authService.isGuestMode;
    final activeItem = _navItems[_currentIndex];

    return ChangeNotifierProvider.value(
      value: authService,
      child: Scaffold(
        backgroundColor: kBackground,
        extendBody: true,
        appBar: _buildAppBar(
          context: context,
          activeItem: activeItem,
          isGuest: isGuest,
          displayName: user?.displayName,
          email: user?.email,
        ),
        body: PageView(
          controller: _pageController,
          physics: const NeverScrollableScrollPhysics(),
          children: _screens,
        ),
        bottomNavigationBar: _PillNavBar(
          items: _navItems,
          currentIndex: _currentIndex,
          onTap: _onNavTap,
        ),
      ),
    );
  }

  // ── App Bar ────────────────────────────────────────────────────────────────

  PreferredSizeWidget _buildAppBar({
    required BuildContext context,
    required _NavItem activeItem,
    required bool isGuest,
    required String? displayName,
    required String? email,
  }) {
    return AppBar(
      backgroundColor: Colors.transparent,
      elevation: 0,
      scrolledUnderElevation: 0,
      systemOverlayStyle: SystemUiOverlayStyle.light,
      titleSpacing: AppSpacing.pageGutter,
      toolbarHeight: 64,
      title:
          _BrandRow(activeLabel: activeItem.label, accent: activeItem.accent),
      actions: [
        Padding(
          padding: const EdgeInsets.only(right: AppSpacing.pageGutter),
          child: _ProfileMenu(
            name: isGuest ? 'Guest' : (displayName ?? 'Student'),
            email: isGuest ? null : email,
            isGuest: isGuest,
            onSelected: _handleMenuSelection,
          ),
        ),
      ],
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Branding row shown in the top app bar.
// ═══════════════════════════════════════════════════════════════════════════════

class _BrandRow extends StatelessWidget {
  const _BrandRow({required this.activeLabel, required this.accent});

  final String activeLabel;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(AppRadius.sm),
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Color(0xFF38BDF8), Color(0xFF0052CC)],
            ),
          ),
          child: const Icon(
            Icons.account_balance_rounded,
            size: 19,
            color: Colors.white,
          ),
        ),
        const SizedBox(width: AppSpacing.sm + 2),
        Expanded(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'NSU Audit',
                style: AppText.headline(),
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 1),
              AnimatedSwitcher(
                duration: AppDurations.base,
                transitionBuilder: (child, animation) => FadeTransition(
                  opacity: animation,
                  child: child,
                ),
                child: Text(
                  activeLabel,
                  key: ValueKey(activeLabel),
                  style: AppText.footnote(color: accent),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Profile button — avatar with dropdown menu.
// ═══════════════════════════════════════════════════════════════════════════════

class _ProfileMenu extends StatelessWidget {
  const _ProfileMenu({
    required this.name,
    required this.email,
    required this.isGuest,
    required this.onSelected,
  });

  final String name;
  final String? email;
  final bool isGuest;
  final void Function(String value) onSelected;

  @override
  Widget build(BuildContext context) {
    return PopupMenuButton<String>(
      tooltip: 'Profile',
      offset: const Offset(0, 52),
      padding: EdgeInsets.zero,
      onSelected: onSelected,
      itemBuilder: (ctx) {
        if (isGuest) {
          return [
            PopupMenuItem<String>(
              enabled: false,
              child: _MenuHeader(title: 'Guest Mode', subtitle: email),
            ),
            const PopupMenuDivider(),
            const PopupMenuItem<String>(
              value: 'health',
              child: _MenuRow(
                icon: Icons.monitor_heart_outlined,
                label: 'System Health',
                color: AppColors.warning,
              ),
            ),
            const PopupMenuDivider(),
            const PopupMenuItem<String>(
              value: 'signin',
              child: _MenuRow(
                icon: Icons.login_rounded,
                label: 'Sign in with Google',
                color: AppColors.primary,
              ),
            ),
            const PopupMenuItem<String>(
              value: 'exit_guest',
              child: _MenuRow(
                icon: Icons.logout_rounded,
                label: 'Exit Guest Mode',
                color: AppColors.error,
              ),
            ),
          ];
        }
        return [
          PopupMenuItem<String>(
            enabled: false,
            child: _MenuHeader(title: name, subtitle: email),
          ),
          const PopupMenuDivider(),
          const PopupMenuItem<String>(
            value: 'history',
            child: _MenuRow(
              icon: Icons.history_rounded,
              label: 'Scan History',
              color: AppColors.primary,
            ),
          ),
          const PopupMenuItem<String>(
            value: 'health',
            child: _MenuRow(
              icon: Icons.monitor_heart_outlined,
              label: 'System Health',
              color: AppColors.warning,
            ),
          ),
          const PopupMenuDivider(),
          const PopupMenuItem<String>(
            value: 'logout',
            child: _MenuRow(
              icon: Icons.logout_rounded,
              label: 'Sign Out',
              color: AppColors.error,
            ),
          ),
        ];
      },
      child: _UserAvatar(name: name),
    );
  }
}

class _MenuHeader extends StatelessWidget {
  const _MenuHeader({required this.title, required this.subtitle});

  final String title;
  final String? subtitle;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          title,
          style: AppText.headline(),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        if ((subtitle ?? '').isNotEmpty) ...[
          const SizedBox(height: 2),
          Text(
            subtitle!,
            style: AppText.footnote(color: AppColors.textSecondary),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ],
    );
  }
}

class _MenuRow extends StatelessWidget {
  const _MenuRow({
    required this.icon,
    required this.label,
    required this.color,
  });

  final IconData icon;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, color: color, size: 18),
        const SizedBox(width: AppSpacing.sm + 4),
        Text(label, style: AppText.body()),
      ],
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// User avatar — gradient initials pill.
// ═══════════════════════════════════════════════════════════════════════════════

class _UserAvatar extends StatelessWidget {
  const _UserAvatar({required this.name});

  final String name;

  @override
  Widget build(BuildContext context) {
    final initials = name.trim().isEmpty
        ? '?'
        : name
            .trim()
            .split(RegExp(r'\s+'))
            .where((w) => w.isNotEmpty)
            .take(2)
            .map((w) => w.characters.first.toUpperCase())
            .join();

    return Container(
      width: 38,
      height: 38,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF38BDF8), Color(0xFF6366F1)],
        ),
        boxShadow: [
          BoxShadow(
            color: kPrimary.withValues(alpha: 0.28),
            blurRadius: 14,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      alignment: Alignment.center,
      child: Text(
        initials,
        style: AppText.headline(color: Colors.white)
            .copyWith(fontSize: 13, fontWeight: FontWeight.w700),
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Nav item model.
// ═══════════════════════════════════════════════════════════════════════════════

class _NavItem {
  const _NavItem({
    required this.label,
    required this.icon,
    required this.activeIcon,
    required this.accent,
  });

  final String label;
  final IconData icon;
  final IconData activeIcon;
  final Color accent;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Pill-style floating navigation bar.
// ═══════════════════════════════════════════════════════════════════════════════

class _PillNavBar extends StatelessWidget {
  const _PillNavBar({
    required this.items,
    required this.currentIndex,
    required this.onTap,
  });

  final List<_NavItem> items;
  final int currentIndex;
  final ValueChanged<int> onTap;

  @override
  Widget build(BuildContext context) {
    final active = items[currentIndex];
    return SafeArea(
      minimum: const EdgeInsets.fromLTRB(
        AppSpacing.md,
        0,
        AppSpacing.md,
        AppSpacing.sm + 4,
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final maxWidth = constraints.maxWidth;
          final itemWidth = maxWidth / items.length;
          return ClipRRect(
            borderRadius: BorderRadius.circular(AppRadius.pill),
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 24, sigmaY: 24),
              child: Container(
                height: 64,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(AppRadius.pill),
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      Colors.white.withValues(alpha: 0.08),
                      Colors.white.withValues(alpha: 0.03),
                    ],
                  ),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.10),
                  ),
                  boxShadow: AppShadows.nav,
                ),
                child: Stack(
                  children: [
                    // ── Animated selection indicator ──
                    AnimatedPositioned(
                      duration: AppDurations.slow,
                      curve: Curves.easeOutCubic,
                      left: itemWidth * currentIndex + 6,
                      top: 6,
                      bottom: 6,
                      width: itemWidth - 12,
                      child: AnimatedContainer(
                        duration: AppDurations.base,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(AppRadius.pill),
                          gradient: LinearGradient(
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                            colors: [
                              active.accent.withValues(alpha: 0.22),
                              active.accent.withValues(alpha: 0.10),
                            ],
                          ),
                          border: Border.all(
                            color: active.accent.withValues(alpha: 0.32),
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: active.accent.withValues(alpha: 0.22),
                              blurRadius: 18,
                              offset: const Offset(0, 6),
                            ),
                          ],
                        ),
                      ),
                    ),
                    // ── Items ──
                    Row(
                      children: List.generate(items.length, (index) {
                        final item = items[index];
                        final isSelected = index == currentIndex;
                        return Expanded(
                          child: _PillNavItem(
                            item: item,
                            isSelected: isSelected,
                            onTap: () => onTap(index),
                          ),
                        );
                      }),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _PillNavItem extends StatelessWidget {
  const _PillNavItem({
    required this.item,
    required this.isSelected,
    required this.onTap,
  });

  final _NavItem item;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = isSelected ? item.accent : kTextTertiary;
    return Semantics(
      button: true,
      label: item.label,
      selected: isSelected,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(AppRadius.pill),
          splashColor: item.accent.withValues(alpha: 0.10),
          highlightColor: Colors.transparent,
          child: AnimatedContainer(
            duration: AppDurations.base,
            curve: Curves.easeOut,
            padding: const EdgeInsets.symmetric(vertical: 10),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              mainAxisSize: MainAxisSize.min,
              children: [
                AnimatedSwitcher(
                  duration: AppDurations.base,
                  transitionBuilder: (child, animation) => ScaleTransition(
                    scale: animation,
                    child: child,
                  ),
                  child: Icon(
                    isSelected ? item.activeIcon : item.icon,
                    key: ValueKey('${item.label}-$isSelected'),
                    size: 22,
                    color: color,
                  ),
                ),
                const SizedBox(height: 4),
                AnimatedDefaultTextStyle(
                  duration: AppDurations.base,
                  style: AppText.caption(color: color).copyWith(
                    fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                  ),
                  child: Text(
                    item.label,
                    overflow: TextOverflow.ellipsis,
                    maxLines: 1,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
