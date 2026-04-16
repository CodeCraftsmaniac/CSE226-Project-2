import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../widgets/glass_widgets.dart';
import 'auth_screen.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final PageController _pageController = PageController();
  int _currentPage = 0;

  final List<OnboardingPage> _pages = [
    OnboardingPage(
      icon: Icons.document_scanner_rounded,
      iconColor: const Color(0xFF38BDF8),
      title: 'Smart Transcript Analysis',
      subtitle: 'Upload your NSU transcript PDF or photo and let our AI-powered OCR engine extract all your course data instantly.',
      features: [
        OnboardingFeature(icon: Icons.auto_awesome, label: 'AI-powered OCR'),
        OnboardingFeature(icon: Icons.flash_on, label: 'Instant extraction'),
        OnboardingFeature(icon: Icons.lock_outline, label: 'Secure processing'),
      ],
    ),
    OnboardingPage(
      icon: Icons.insights_rounded,
      iconColor: const Color(0xFF80FFBD),
      title: 'Complete Degree Audit',
      subtitle: 'Get a comprehensive 3-level analysis: credit tally, CGPA calculation with waiver eligibility, and graduation readiness check.',
      features: [
        OnboardingFeature(icon: Icons.calculate, label: 'CGPA analysis'),
        OnboardingFeature(icon: Icons.card_giftcard, label: 'Waiver check'),
        OnboardingFeature(icon: Icons.school, label: 'Graduation audit'),
      ],
    ),
  ];

  Future<void> _completeOnboarding() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('onboarding_complete', true);

    if (!mounted) return;

    // Navigate to auth screen after onboarding
    Navigator.of(context).pushReplacement(
      PageRouteBuilder(
        pageBuilder: (context, animation, secondaryAnimation) => const AuthScreen(),
        transitionsBuilder: (context, animation, secondaryAnimation, child) {
          return FadeTransition(opacity: animation, child: child);
        },
        transitionDuration: const Duration(milliseconds: 500),
      ),
    );
  }

  void _nextPage() {
    if (_currentPage < _pages.length - 1) {
      _pageController.nextPage(
        duration: const Duration(milliseconds: 400),
        curve: Curves.easeInOut,
      );
    } else {
      _completeOnboarding();
    }
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: GradientBackground(
        child: Stack(
          children: [
            // Aurora blobs
            const Positioned(
              top: -80,
              right: -60,
              child: AuroraBlob(color: Color(0xFF0FA3FF), size: 250),
            ),
            const Positioned(
              bottom: -100,
              left: -80,
              child: AuroraBlob(color: Color(0xFFF6B75D), size: 280),
            ),

            // Main content
            SafeArea(
              child: Column(
                children: [
                  // Header with skip button
                  Padding(
                    padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        // Logo badge
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.06),
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Container(
                                width: 24,
                                height: 24,
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(8),
                                  gradient: const LinearGradient(
                                    colors: [Color(0xFF38BDF8), Color(0xFF0052CC)],
                                  ),
                                ),
                                child: const Icon(Icons.account_balance, size: 14, color: Colors.white),
                              ),
                              const SizedBox(width: 8),
                              Text(
                                'NSU Audit',
                                style: AppText.callout(color: Colors.white)
                                    .copyWith(fontWeight: FontWeight.w600),
                              ),
                            ],
                          ),
                        ),

                        // Skip button
                        TextButton(
                          onPressed: _completeOnboarding,
                          child: Text(
                            'Skip',
                            style: AppText.callout(
                              color: AppColors.textSecondary,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),

                  // Page content
                  Expanded(
                    child: PageView.builder(
                      controller: _pageController,
                      onPageChanged: (index) => setState(() => _currentPage = index),
                      itemCount: _pages.length,
                      itemBuilder: (context, index) {
                        final page = _pages[index];
                        return _buildPage(page, index);
                      },
                    ),
                  ),

                  // Bottom section with indicators and button
                  Padding(
                    padding: const EdgeInsets.fromLTRB(
                      AppSpacing.lg,
                      AppSpacing.md,
                      AppSpacing.lg,
                      AppSpacing.xl,
                    ),
                    child: Column(
                      children: [
                        // Page indicators
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: List.generate(
                            _pages.length,
                            (index) => AnimatedContainer(
                              duration: const Duration(milliseconds: 300),
                              margin: const EdgeInsets.symmetric(horizontal: 4),
                              width: _currentPage == index ? 32 : 10,
                              height: 10,
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(999),
                                color: _currentPage == index
                                    ? const Color(0xFF57C5FF)
                                    : Colors.white.withValues(alpha: 0.2),
                              ),
                            ),
                          ),
                        ),

                        const SizedBox(height: 28),

                        // Action button
                        SizedBox(
                          width: double.infinity,
                          child: FilledButton(
                            onPressed: _nextPage,
                            style: FilledButton.styleFrom(
                              padding: const EdgeInsets.symmetric(vertical: 16),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(
                                    AppRadius.md),
                              ),
                              backgroundColor: AppColors.primary,
                            ),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Text(
                                  _currentPage == _pages.length - 1
                                      ? 'Get Started'
                                      : 'Continue',
                                  style: AppText.headline(
                                    color: AppColors.textInverse,
                                  ).copyWith(fontWeight: FontWeight.w700),
                                ),
                                const SizedBox(width: AppSpacing.sm),
                                const Icon(
                                  Icons.arrow_forward_rounded,
                                  color: AppColors.textInverse,
                                  size: 20,
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPage(OnboardingPage page, int index) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 28),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Spacer(flex: 1),

          // Icon container with glow
          Container(
            width: 140,
            height: 140,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                colors: [
                  page.iconColor.withValues(alpha: 0.25),
                  page.iconColor.withValues(alpha: 0.05),
                  Colors.transparent,
                ],
                stops: const [0.3, 0.6, 1.0],
              ),
            ),
            child: Center(
              child: Container(
                width: 100,
                height: 100,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: page.iconColor.withValues(alpha: 0.15),
                  border: Border.all(
                    color: page.iconColor.withValues(alpha: 0.3),
                    width: 2,
                  ),
                ),
                child: Icon(
                  page.icon,
                  size: 48,
                  color: page.iconColor,
                ),
              ),
            ),
          )
              .animate(key: ValueKey('icon_$index'))
              .scale(
                begin: const Offset(0.8, 0.8),
                end: const Offset(1.0, 1.0),
                duration: 500.ms,
                curve: Curves.easeOut,
              )
              .fadeIn(duration: 400.ms),

          const SizedBox(height: 48),

          // Title
          Text(
            page.title,
            textAlign: TextAlign.center,
            style: AppText.title1(),
          )
              .animate(key: ValueKey('title_$index'))
              .fadeIn(delay: 150.ms, duration: 400.ms)
              .slideY(begin: 0.2, end: 0, duration: 400.ms),

          const SizedBox(height: 16),

          // Subtitle
          Text(
            page.subtitle,
            textAlign: TextAlign.center,
            style: AppText.body(color: AppColors.textSecondary)
                .copyWith(height: 1.5),
          )
              .animate(key: ValueKey('subtitle_$index'))
              .fadeIn(delay: 250.ms, duration: 400.ms)
              .slideY(begin: 0.2, end: 0, duration: 400.ms),

          const SizedBox(height: 40),

          // Feature chips
          Wrap(
            spacing: 12,
            runSpacing: 12,
            alignment: WrapAlignment.center,
            children: page.features.asMap().entries.map((entry) {
              final i = entry.key;
              final feature = entry.value;
              return Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.md, vertical: 10),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.06),
                  borderRadius: BorderRadius.circular(AppRadius.pill),
                  border: Border.all(
                      color: Colors.white.withValues(alpha: 0.08)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(feature.icon, size: 16, color: page.iconColor),
                    const SizedBox(width: AppSpacing.sm),
                    Text(
                      feature.label,
                      style: AppText.subheadline(color: Colors.white),
                    ),
                  ],
                ),
              )
                  .animate(key: ValueKey('feature_${index}_$i'))
                  .fadeIn(delay: (350 + i * 80).ms, duration: 400.ms)
                  .scale(
                    begin: const Offset(0.9, 0.9),
                    end: const Offset(1.0, 1.0),
                    duration: 400.ms,
                  );
            }).toList(),
          ),

          const Spacer(flex: 2),
        ],
      ),
    );
  }
}

class OnboardingPage {
  final IconData icon;
  final Color iconColor;
  final String title;
  final String subtitle;
  final List<OnboardingFeature> features;

  const OnboardingPage({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.subtitle,
    required this.features,
  });
}

class OnboardingFeature {
  final IconData icon;
  final String label;

  const OnboardingFeature({required this.icon, required this.label});
}
