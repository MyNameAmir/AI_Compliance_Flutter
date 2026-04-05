import 'package:flutter/material.dart';

class ResultsScreen extends StatefulWidget {
  final Map<String, dynamic> data;
  const ResultsScreen({super.key, required this.data});

  @override
  State<ResultsScreen> createState() => _ResultsScreenState();
}

class _ResultsScreenState extends State<ResultsScreen> {
  bool _showChunks = false;

  Map<String, dynamic> get d => widget.data;
  String get decision => (d['decision'] ?? '').toString();
  String get report => (d['report'] ?? '').toString();
  String get personId => (d['person_id'] ?? 'unknown').toString();
  String get personRole => (d['person_role'] ?? 'unknown').toString();
  String get finalText => (d['final_text'] ?? '').toString();
  int get previousViolations => (d['previous_violations'] ?? 0) as int;
  List<dynamic> get chunks => (d['top_chunks'] ?? []) as List<dynamic>;

  // Severity
  String get severity => _nested('severity', 'severity');
  String get harmLevel => _nested('severity', 'harm_level');
  String get intentLevel => _nested('severity', 'intent_level');
  String get severityReason => _nested('severity', 'reason');

  // Sanction
  String get sanctionLevel => _nested('sanction', 'sanction_level');
  String get recommendedAction => _nested('sanction', 'recommended_action');
  String get sanctionReason => _nested('sanction', 'reason');

  String _nested(String outer, String inner) {
    final m = d[outer];
    if (m is Map) return (m[inner] ?? '').toString();
    return '';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SingleChildScrollView(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 980),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 40, horizontal: 18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Top bar
                  Row(
                    children: [
                      TextButton.icon(
                        onPressed: () => Navigator.pushReplacementNamed(context, '/'),
                        icon: const Icon(Icons.arrow_back),
                        label: const Text('New Analysis'),
                      ),
                      const Spacer(),
                      _badge(decision),
                    ],
                  ),
                  const SizedBox(height: 16),

                  Text('Results',
                      style: TextStyle(
                        fontSize: 32, fontWeight: FontWeight.bold,
                        color: Colors.teal.shade800,
                      )),
                  const SizedBox(height: 20),

                  // Decision hero
                  _decisionHero(),
                  const SizedBox(height: 20),

                  // Person info
                  _sectionCard(
                    icon: Icons.person_outline,
                    title: 'Person Identified',
                    children: [
                      _kvRow('Person ID', personId),
                      _kvRow('Role', personRole),
                      _kvRow('Previous violations', previousViolations.toString()),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // Final decision report
                  _sectionCard(
                    icon: Icons.find_in_page_outlined,
                    title: 'Final Decision Report',
                    subtitle: 'Generated from retrieved policy evidence.',
                    children: [
                      SelectableText(report, style: const TextStyle(height: 1.5)),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // Severity
                  _sectionCard(
                    icon: Icons.warning_amber_outlined,
                    title: 'Severity Assessment',
                    children: [
                      _kvRow('Severity', severity),
                      _kvRow('Harm level', harmLevel),
                      _kvRow('Intent', intentLevel),
                      if (severityReason.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.only(top: 8),
                          child: Text(severityReason,
                              style: TextStyle(color: Colors.grey.shade700)),
                        ),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // Sanction
                  _sectionCard(
                    icon: Icons.gavel_outlined,
                    title: 'Sanction Recommendation',
                    children: [
                      _kvRow('Sanction level', sanctionLevel),
                      _kvRow('Recommended action', recommendedAction),
                      if (sanctionReason.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.only(top: 8),
                          child: Text(sanctionReason,
                              style: TextStyle(color: Colors.grey.shade700)),
                        ),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // User-friendly summary
                  if (finalText.isNotEmpty) ...[
                    _sectionCard(
                      icon: Icons.summarize_outlined,
                      title: 'User-Friendly Summary',
                      children: [
                        SelectableText(finalText, style: const TextStyle(height: 1.5)),
                      ],
                    ),
                    const SizedBox(height: 16),
                  ],

                  // Toggle chunks button
                  Center(
                    child: SizedBox(
                      width: 340,
                      child: FilledButton.tonal(
                        onPressed: () => setState(() => _showChunks = !_showChunks),
                        child: Text(
                          _showChunks
                              ? 'Hide Policy Evidence'
                              : 'Show Policy Evidence (Top ${chunks.length} Chunks)',
                        ),
                      ),
                    ),
                  ),

                  if (_showChunks) ...[
                    const SizedBox(height: 20),
                    Text('Top Policy Chunks',
                        style: TextStyle(
                          fontSize: 22, fontWeight: FontWeight.w600,
                          color: Colors.teal.shade800,
                        )),
                    const SizedBox(height: 4),
                    Text('These are the top retrieved excerpts used as evidence.',
                        style: TextStyle(color: Colors.grey.shade600)),
                    const SizedBox(height: 12),
                    ...List.generate(chunks.length, (i) {
                      final c = chunks[i] as Map<String, dynamic>;
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: Card(
                          elevation: 3,
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(18)),
                          child: Padding(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    _badge('Rank ${i + 1}'),
                                    const Spacer(),
                                    Text('Score: ${c['score']}',
                                        style: TextStyle(
                                            fontSize: 13,
                                            color: Colors.grey.shade600)),
                                  ],
                                ),
                                const SizedBox(height: 10),
                                SelectableText(
                                  (c['chunk'] ?? '').toString(),
                                  style: const TextStyle(height: 1.5),
                                ),
                              ],
                            ),
                          ),
                        ),
                      );
                    }),
                  ],

                  const SizedBox(height: 40),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  // ── Decision hero card ────────────────────────────────────────────
  Widget _decisionHero() {
    final bool violation = decision == 'Violation';
    final bool noViolation = decision == 'No Violation';

    String symbol;
    Color bgStart, bgEnd, textColor;
    String heading, sub;

    if (violation) {
      symbol = '✖';
      bgStart = const Color(0xFFEF4444);
      bgEnd = const Color(0xFFB91C1C);
      textColor = const Color(0xFF7F1D1D);
      heading = 'Violation Detected';
      sub = 'The incident is supported by at least one policy rule in the retrieved evidence.';
    } else if (noViolation) {
      symbol = '✓';
      bgStart = const Color(0xFF22C55E);
      bgEnd = const Color(0xFF15803D);
      textColor = const Color(0xFF14532D);
      heading = 'No Violation Found';
      sub = 'No policy-backed violation was found based on the retrieved evidence.';
    } else {
      symbol = '!';
      bgStart = const Color(0xFF64748B);
      bgEnd = const Color(0xFF334155);
      textColor = const Color(0xFF0F172A);
      heading = 'Not Enough Policy Evidence';
      sub = 'The retrieved policy excerpts do not contain an exact rule that matches the incident.';
    }

    return Card(
      elevation: 6,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            Container(
              width: 72, height: 72,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(18),
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [bgStart, bgEnd],
                ),
              ),
              alignment: Alignment.center,
              child: Text(symbol,
                  style: const TextStyle(fontSize: 40, color: Colors.white)),
            ),
            const SizedBox(width: 18),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(heading,
                      style: TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.bold,
                          color: textColor)),
                  const SizedBox(height: 4),
                  Text(sub, style: TextStyle(color: Colors.grey.shade600)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ── Section card ──────────────────────────────────────────────────
  Widget _sectionCard({
    required IconData icon,
    required String title,
    String? subtitle,
    required List<Widget> children,
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
                Icon(icon, size: 22),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(title,
                          style: const TextStyle(
                              fontWeight: FontWeight.w600, fontSize: 15)),
                      if (subtitle != null)
                        Text(subtitle,
                            style: TextStyle(
                                fontSize: 13, color: Colors.grey.shade600)),
                    ],
                  ),
                ),
              ],
            ),
            const Divider(height: 24),
            ...children,
          ],
        ),
      ),
    );
  }

  // ── Key-value row ─────────────────────────────────────────────────
  Widget _kvRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 180,
            child: Text('$label:',
                style: const TextStyle(fontWeight: FontWeight.w500)),
          ),
          Expanded(child: SelectableText(value)),
        ],
      ),
    );
  }

  // ── Badge chip ────────────────────────────────────────────────────
  Widget _badge(String label) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.teal.shade50,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(label,
          style: TextStyle(
              color: Colors.teal.shade800,
              fontWeight: FontWeight.w500,
              fontSize: 13)),
    );
  }
}
