import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import '../services/api_service.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  PlatformFile? _policyFile;
  PlatformFile? _incidentFile;
  bool _isRunning = false;
  String? _error;

  Future<void> _pickFile({required bool isPolicy}) async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf'],
      withData: true,
    );
    if (result != null && result.files.isNotEmpty) {
      setState(() {
        if (isPolicy) {
          _policyFile = result.files.first;
        } else {
          _incidentFile = result.files.first;
        }
      });
    }
  }

  Future<void> _analyze() async {
    if (_policyFile?.bytes == null || _incidentFile?.bytes == null) {
      setState(() => _error = 'Please upload BOTH a Policy PDF and an Incident PDF.');
      return;
    }

    setState(() {
      _isRunning = true;
      _error = null;
    });

    try {
      final data = await ApiService.analyze(
        policyBytes: _policyFile!.bytes!,
        policyName: _policyFile!.name,
        incidentBytes: _incidentFile!.bytes!,
        incidentName: _incidentFile!.name,
      );

      if (!mounted) return;
      Navigator.pushNamed(context, '/results', arguments: data);
    } catch (e) {
      setState(() => _error = 'Error while analyzing: $e');
    } finally {
      if (mounted) setState(() => _isRunning = false);
    }
  }

  // ── Build ─────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Scaffold(
      body: SingleChildScrollView(
        child: Column(
          children: [
            _heroSection(cs),
            Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 980),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 40, horizontal: 18),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // Error banner
                      if (_error != null) ...[
                        _errorBanner(_error!),
                        const SizedBox(height: 16),
                      ],

                      // Upload panels – side-by-side on wide, stacked on narrow
                      LayoutBuilder(builder: (ctx, constraints) {
                        final wide = constraints.maxWidth > 640;
                        final panels = [
                          Expanded(
                            child: _uploadCard(
                              title: 'Upload Hospital Policy (PDF)',
                              subtitle: 'Examples: PHIPA, hospital privacy policy, staff conduct rules.',
                              file: _policyFile,
                              onPick: () => _pickFile(isPolicy: true),
                              onClear: () => setState(() => _policyFile = null),
                            ),
                          ),
                          if (wide) const SizedBox(width: 16),
                          Expanded(
                            child: _uploadCard(
                              title: 'Upload Incident Report (PDF)',
                              subtitle: 'A report describing what happened (staff actions, disclosure, access, etc.).',
                              file: _incidentFile,
                              onPick: () => _pickFile(isPolicy: false),
                              onClear: () => setState(() => _incidentFile = null),
                            ),
                          ),
                        ];
                        if (wide) {
                          return Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: panels,
                          );
                        }
                        return Column(children: [
                          _uploadCard(
                            title: 'Upload Hospital Policy (PDF)',
                            subtitle: 'Examples: PHIPA, hospital privacy policy, staff conduct rules.',
                            file: _policyFile,
                            onPick: () => _pickFile(isPolicy: true),
                            onClear: () => setState(() => _policyFile = null),
                          ),
                          const SizedBox(height: 16),
                          _uploadCard(
                            title: 'Upload Incident Report (PDF)',
                            subtitle: 'A report describing what happened (staff actions, disclosure, access, etc.).',
                            file: _incidentFile,
                            onPick: () => _pickFile(isPolicy: false),
                            onClear: () => setState(() => _incidentFile = null),
                          ),
                        ]);
                      }),

                      const SizedBox(height: 28),

                      // Analyze button
                      Center(
                        child: SizedBox(
                          width: 320,
                          height: 52,
                          child: FilledButton(
                            onPressed: _isRunning ? null : _analyze,
                            style: FilledButton.styleFrom(
                              backgroundColor: cs.primary,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(14),
                              ),
                            ),
                            child: _isRunning
                                ? const Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      SizedBox(
                                        width: 20, height: 20,
                                        child: CircularProgressIndicator(
                                          strokeWidth: 2,
                                          color: Colors.white,
                                        ),
                                      ),
                                      SizedBox(width: 12),
                                      Text('Analyzing…'),
                                    ],
                                  )
                                : const Text('Analyze Incident', style: TextStyle(fontSize: 16)),
                          ),
                        ),
                      ),

                      // Analyzing banner
                      if (_isRunning) ...[
                        const SizedBox(height: 24),
                        _analyzingBanner(),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ── Hero ───────────────────────────────────────────────────────────
  Widget _heroSection(ColorScheme cs) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 44, horizontal: 18),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0x2414B8A6), // teal 14%
            Color(0x1A3B82F6), // blue 10%
            Colors.white,
          ],
        ),
      ),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 980),
          child: Column(
            children: [
              Text(
                'Hospital Policy & Incident Compliance Checker',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 36,
                  fontWeight: FontWeight.bold,
                  color: cs.onSurface,
                ),
              ),
              const SizedBox(height: 14),
              ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 820),
                child: Text(
                  'Upload a hospital policy PDF and an incident report. '
                  'The agent retrieves the most relevant policy evidence and evaluates whether a violation occurred.',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 16, color: Colors.grey.shade700),
                ),
              ),
              const SizedBox(height: 28),
              Container(
                width: double.infinity,
                height: 220,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(24),
                  gradient: LinearGradient(
                    colors: [
                      Colors.teal.shade100,
                      Colors.blue.shade50,
                      Colors.white,
                    ],
                  ),
                ),
                child: Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.local_hospital_rounded,
                          size: 72, color: Colors.teal.shade400),
                      const SizedBox(height: 12),
                      Text(
                        'Policy & Incident Analysis',
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.w600,
                          color: Colors.teal.shade700,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ── Upload card ────────────────────────────────────────────────────
  Widget _uploadCard({
    required String title,
    required String subtitle,
    required PlatformFile? file,
    required VoidCallback onPick,
    required VoidCallback onClear,
  }) {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.description_outlined, size: 22),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                      Text(subtitle, style: TextStyle(fontSize: 13, color: Colors.grey.shade600)),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Drop zone
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                border: Border.all(color: Colors.grey.shade400, width: 2, style: BorderStyle.solid),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Column(
                children: [
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.tonal(
                      onPressed: onPick,
                      child: const Text('Choose PDF'),
                    ),
                  ),
                  if (file != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      'Selected: ${file.name}',
                      style: TextStyle(fontSize: 13, color: Colors.grey.shade600),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 12),

            Row(
              children: [
                Expanded(
                  child: FilledButton.tonal(
                    onPressed: onPick,
                    child: const Text('Upload'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: TextButton(
                    onPressed: onClear,
                    child: const Text('Clear'),
                  ),
                ),
              ],
            ),

            if (file != null) ...[
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.green.shade50,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  children: [
                    Icon(Icons.check_circle, color: Colors.green.shade700, size: 18),
                    const SizedBox(width: 8),
                    Text('Saved on client.', style: TextStyle(color: Colors.green.shade700)),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  // ── Analyzing banner ───────────────────────────────────────────────
  Widget _analyzingBanner() {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            const SizedBox(
              width: 28, height: 28,
              child: CircularProgressIndicator(strokeWidth: 3),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Analyzing documents…',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 4),
                  Text(
                    'Embedding policy chunks → retrieving evidence → evaluating violations. '
                    'This can take 30–90 seconds depending on PDF length.',
                    style: TextStyle(fontSize: 13, color: Colors.grey.shade600),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ── Error banner ──────────────────────────────────────────────────
  Widget _errorBanner(String msg) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.red.shade50,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Icon(Icons.warning_amber_rounded, color: Colors.red.shade700),
          const SizedBox(width: 10),
          Expanded(child: Text(msg, style: TextStyle(color: Colors.red.shade800))),
        ],
      ),
    );
  }
}
