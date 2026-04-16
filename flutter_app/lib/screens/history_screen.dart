import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../services/auth_service.dart';
import '../services/analysis_session_service.dart';
import '../widgets/glass_widgets.dart';
import 'home_screen.dart';

/// History Screen - Displays user's past transcript scans
/// ========================================================
/// Features:
/// - List of all past scans with metadata
/// - View detailed analysis for any scan
/// - Delete scans
/// - Pull-to-refresh

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<Map<String, dynamic>> _scans = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final scans = await authService.getHistory(limit: 100);
      if (mounted) {
        setState(() {
          _scans = scans;
          _isLoading = false;
        });
      }
    } on ApiException catch (e) {
      if (mounted) {
        setState(() {
          _error = e.message;
          _isLoading = false;
        });
        if (e.isAuthError) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: const Text('Session expired. Please sign in again.'),
              backgroundColor: Colors.orange,
              action: SnackBarAction(
                label: 'Sign In',
                onPressed: () async {
                  await authService.signInWithGoogle();
                  if (authService.isAuthenticated) _loadHistory();
                },
              ),
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString().replaceFirst('Exception: ', '');
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _deleteScan(String scanId, int index) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Scan'),
        content: const Text('Are you sure you want to delete this scan? This action cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        final success = await authService.deleteScan(scanId);
        if (success && mounted) {
          setState(() {
            _scans.removeAt(index);
          });
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Scan deleted successfully'),
              backgroundColor: Colors.green,
            ),
          );
        } else if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Failed to delete scan'),
              backgroundColor: Colors.red,
            ),
          );
        }
      } on ApiException catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(e.message),
              backgroundColor: e.isAuthError ? Colors.orange : Colors.red,
            ),
          );
        }
      }
    }
  }

  Future<void> _viewScanDetails(String scanId) async {
    // Show loading indicator
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(
        child: CircularProgressIndicator(),
      ),
    );

    try {
      final scanDetails = await authService.getScanDetails(scanId);
      if (mounted) {
        Navigator.pop(context); // Close loading dialog

        final analysisData = scanDetails?['analysis_data'];
        if (analysisData is Map) {
          analysisSessionService
              .setLatestAnalysis(analysisData.cast<String, dynamic>());
          Navigator.pushReplacement(
            context,
            MaterialPageRoute(
              builder: (context) => HomeScreen(
                initialData: analysisData.cast<String, dynamic>(),
              ),
            ),
          );
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Could not load scan details'),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    } on ApiException catch (e) {
      if (mounted) {
        Navigator.pop(context); // Close loading dialog
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(e.message),
            backgroundColor: e.isAuthError ? Colors.orange : Colors.red,
            action: e.isAuthError ? SnackBarAction(
              label: 'Sign In',
              onPressed: () async {
                await authService.signInWithGoogle();
              },
            ) : null,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        Navigator.pop(context); // Close loading dialog
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: ${e.toString().replaceFirst("Exception: ", "")}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  String _formatDate(String? dateStr) {
    if (dateStr == null) return 'Unknown date';
    try {
      final date = DateTime.parse(dateStr);
      final now = DateTime.now();
      final diff = now.difference(date);
      
      if (diff.inDays == 0) {
        return 'Today at ${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}';
      } else if (diff.inDays == 1) {
        return 'Yesterday';
      } else if (diff.inDays < 7) {
        return '${diff.inDays} days ago';
      } else {
        return '${date.day}/${date.month}/${date.year}';
      }
    } catch (e) {
      return dateStr;
    }
  }

  Color _getCgpaColor(double cgpa) {
    if (cgpa >= 3.5) return const Color(0xFF10B981);
    if (cgpa >= 3.0) return const Color(0xFF3B82F6);
    if (cgpa >= 2.5) return const Color(0xFFF59E0B);
    if (cgpa >= 2.0) return const Color(0xFFF97316);
    return const Color(0xFFEF4444);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBackground,
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded, color: kTextPrimary),
          onPressed: () => Navigator.pop(context),
        ),
        title: Text('Scan History', style: AppText.title3()),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            icon: const Icon(Icons.refresh_rounded, color: kTextSecondary),
            onPressed: _loadHistory,
          ),
        ],
      ),
      body: Stack(
        children: [
          const Positioned(
            top: -80,
            right: -60,
            child: AuroraBlob(color: kPrimary, size: 240),
          ),
          const Positioned(
            bottom: -100,
            left: -60,
            child: AuroraBlob(color: kSuccess, size: 220),
          ),
          SafeArea(child: _buildBody()),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const CircularProgressIndicator(strokeWidth: 2.4),
            const SizedBox(height: AppSpacing.md),
            Text(
              'Loading your scan history…',
              style: AppText.subheadline(),
            ),
          ],
        ),
      );
    }

    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline_rounded,
                  size: 56, color: kError),
              const SizedBox(height: AppSpacing.md),
              Text('Something went wrong',
                  style: AppText.title3(), textAlign: TextAlign.center),
              const SizedBox(height: AppSpacing.xs),
              Text(_error!,
                  textAlign: TextAlign.center,
                  style: AppText.subheadline()),
              const SizedBox(height: AppSpacing.lg),
              FilledButton.icon(
                onPressed: _loadHistory,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    if (!authService.isAuthenticated) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.lock_outline_rounded,
                  size: 56, color: kTextSecondary),
              const SizedBox(height: AppSpacing.md),
              Text('Sign in to view your scan history',
                  style: AppText.title3(), textAlign: TextAlign.center),
              const SizedBox(height: AppSpacing.sm),
              Text(
                'Your past transcript scans will appear here after you sign in with Google.',
                textAlign: TextAlign.center,
                style: AppText.subheadline(),
              ),
              const SizedBox(height: AppSpacing.lg),
              FilledButton.icon(
                onPressed: () async {
                  await authService.signInWithGoogle();
                  if (authService.isAuthenticated) _loadHistory();
                },
                icon: const Icon(Icons.login_rounded),
                label: const Text('Sign in with Google'),
              ),
            ],
          ),
        ),
      );
    }

    if (_scans.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.history_rounded,
                  size: 56, color: kTextSecondary),
              const SizedBox(height: AppSpacing.md),
              Text('No scans yet', style: AppText.title3()),
              const SizedBox(height: AppSpacing.sm),
              Text(
                'Upload your first transcript to see it here.',
                textAlign: TextAlign.center,
                style: AppText.subheadline(),
              ),
              const SizedBox(height: AppSpacing.lg),
              FilledButton.icon(
                onPressed: () => Navigator.pop(context),
                icon: const Icon(Icons.upload_file_rounded),
                label: const Text('Upload Transcript'),
              ),
            ],
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadHistory,
      color: kPrimary,
      backgroundColor: kSurface,
      child: ListView.builder(
        padding: const EdgeInsets.fromLTRB(
          AppSpacing.pageGutter,
          AppSpacing.md,
          AppSpacing.pageGutter,
          AppSpacing.xl,
        ),
        itemCount: _scans.length,
        itemBuilder: (context, index) {
          final scan = _scans[index];
          final cgpa = (scan['cgpa'] as num?)?.toDouble() ?? 0.0;
          final totalCourses = scan['total_courses'] ?? 0;
          final totalCredits = (scan['total_credits'] as num?)?.toDouble() ?? 0.0;
          final filename = scan['filename'] ?? 'Unknown file';
          final createdAt = scan['created_at'] as String?;
          final scanId = scan['id'] as String;
          final source = scan['source'] ?? 'web';

          final cgpaColor = _getCgpaColor(cgpa);
          return Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.sm + 4),
            child: GlassCard(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Header row
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: kPrimary.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(AppRadius.sm),
                          border: Border.all(
                              color: kPrimary.withValues(alpha: 0.18)),
                        ),
                        child: const Icon(Icons.description_rounded,
                            color: kPrimary, size: 22),
                      ),
                      const SizedBox(width: AppSpacing.sm + 4),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              filename,
                              style: AppText.headline(),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            const SizedBox(height: 2),
                            Row(
                              children: [
                                const Icon(Icons.access_time_rounded,
                                    size: 13, color: kTextTertiary),
                                const SizedBox(width: 4),
                                Flexible(
                                  child: Text(
                                    _formatDate(createdAt),
                                    style: AppText.footnote(),
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                                const SizedBox(width: AppSpacing.sm),
                                _buildSourceChip(source),
                              ],
                            ),
                          ],
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: AppSpacing.sm + 4, vertical: 6),
                        decoration: BoxDecoration(
                          color: cgpaColor.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(AppRadius.xs),
                          border: Border.all(
                              color: cgpaColor.withValues(alpha: 0.35)),
                        ),
                        child: Text(
                          cgpa.toStringAsFixed(2),
                          style: AppText.headline(color: cgpaColor)
                              .copyWith(fontWeight: FontWeight.w700),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.sm + 4),
                  Wrap(
                    spacing: AppSpacing.sm,
                    runSpacing: AppSpacing.sm,
                    children: [
                      _buildStatPill(
                          Icons.menu_book_rounded, '$totalCourses courses'),
                      _buildStatPill(Icons.school_rounded,
                          '${totalCredits.toStringAsFixed(0)} credits'),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.sm + 4),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () => _deleteScan(scanId, index),
                          icon: const Icon(Icons.delete_outline_rounded,
                              size: 18),
                          label: const Text('Delete'),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: kError,
                            side: BorderSide(
                                color: kError.withValues(alpha: 0.4)),
                            padding: const EdgeInsets.symmetric(vertical: 12),
                          ),
                        ),
                      ),
                      const SizedBox(width: AppSpacing.sm + 4),
                      Expanded(
                        flex: 2,
                        child: FilledButton.icon(
                          onPressed: () => _viewScanDetails(scanId),
                          icon: const Icon(Icons.visibility_rounded,
                              size: 18),
                          label: const Text('View Analysis'),
                          style: FilledButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 12),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ).animate().fadeIn(delay: (50 * index).ms).slideX(begin: 0.1);
        },
      ),
    );
  }

  Widget _buildSourceChip(String source) {
    IconData icon;
    Color color;
    
    switch (source.toLowerCase()) {
      case 'flutter':
      case 'mobile':
        icon = Icons.phone_android;
        color = const Color(0xFF8B5CF6);
        break;
      case 'cli':
        icon = Icons.terminal;
        color = const Color(0xFF10B981);
        break;
      default:
        icon = Icons.language;
        color = const Color(0xFF3B82F6);
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(AppRadius.xs / 2),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: color),
          const SizedBox(width: 3),
          Text(
            source,
            style: AppText.caption(color: color)
                .copyWith(fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }

  Widget _buildStatPill(IconData icon, String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: kSurfaceHigh,
        borderRadius: BorderRadius.circular(AppRadius.xs),
        border: Border.all(color: kBorder),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: kTextSecondary),
          const SizedBox(width: 4),
          Text(text, style: AppText.footnote(color: AppColors.textSecondary)),
        ],
      ),
    );
  }
}
