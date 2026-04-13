import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:desktop_drop/desktop_drop.dart';
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

  bool _isDraggingPolicy = false;
  bool _isDraggingIncident = false;

  Future<void> _pickFile({required bool isPolicy}) async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf'],
      withData: true,
    );
    if (result != null && result.files.isNotEmpty) {
      _setFile(result.files.first, isPolicy);
    }
  }

  void _setFile(PlatformFile file, bool isPolicy) {
    setState(() {
      if (isPolicy) {
        _policyFile = file;
      } else {
        _incidentFile = file;
      }
    });
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
      final data = await EHospitalApiService.analyze(
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: _buildTopNav(),
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(32.0),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1100),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildHeader(),
                  const SizedBox(height: 32),
                  if (_error != null) ...[
                    _errorBanner(_error!),
                    const SizedBox(height: 24),
                  ],
                  _buildUploadSection(),
                  const SizedBox(height: 40),
                  _buildActionSection(),
                  if (_isRunning) ...[
                    const SizedBox(height: 32),
                    _analyzingBanner(),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  PreferredSizeWidget _buildTopNav() {
    return AppBar(
      backgroundColor: Colors.white,
      elevation: 0,
      centerTitle: false,
      title: Row(
        children: [
          const Icon(Icons.medical_services, color: Color(0xFF1E40AF), size: 28),
          const SizedBox(width: 12),
          Text(
            'E-HOSPITAL',
            style: TextStyle(
              color: Color(0xFF1E40AF),
              fontWeight: FontWeight.w900,
              letterSpacing: 1.2,
              fontSize: 20,
            ),
          ),
          const SizedBox(width: 8),
          Text(
            'PHARMACEUTICALS',
            style: TextStyle(
              color: Colors.grey.shade600,
              fontWeight: FontWeight.w400,
              fontSize: 14,
            ),
          ),
        ],
      ),
      bottom: PreferredSize(
        preferredSize: const Size.fromHeight(1),
        child: Container(color: Colors.grey.shade200, height: 1),
      ),
      actions: [
        Padding(
          padding: const EdgeInsets.only(right: 20.0),
          child: CircleAvatar(
            backgroundColor: Colors.grey.shade100,
            child: Icon(Icons.person_outline, color: Colors.grey.shade600),
          ),
        ),
      ],
    );
  }

  Widget _buildHeader() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Hero Image Section
        ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: Stack(
            children: [
              Image.asset(
                'assets/images/loginhome.png',
                height: 240,
                width: double.infinity,
                fit: BoxFit.cover,
              ),
              Container(
                height: 240,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.bottomCenter,
                    end: Alignment.topCenter,
                    colors: [
                      const Color(0xFF1E40AF).withOpacity(0.8),
                      const Color(0xFF1E40AF).withOpacity(0.1),
                    ],
                  ),
                ),
              ),
              Positioned(
                bottom: 24,
                left: 24,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.medical_services, color: Colors.white, size: 40),
                    const SizedBox(height: 12),
                    const Text(
                      'E-HOSPITAL PHARMACEUTICALS',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 28,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 1.5,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Compliance Audit & Automated Policy Alignment System',
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.9),
                        fontSize: 16,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 32),
        Text(
          'Compliance Audit Dashboard',
          style: Theme.of(context).textTheme.headlineLarge,
        ),
        const SizedBox(height: 8),
        Text(
          'Automated policy alignment and incident investigation system.',
          style: Theme.of(context).textTheme.bodyLarge,
        ),
      ],
    );
  }

  Widget _buildUploadSection() {
    return LayoutBuilder(builder: (context, constraints) {
      final bool isWide = constraints.maxWidth > 700;
      return Flex(
        direction: isWide ? Axis.horizontal : Axis.vertical,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            flex: isWide ? 1 : 0,
            child: _uploadCard(
              title: 'Hospital Policy',
              subtitle: 'Upload the relevant rulebook or privacy policy (PDF)',
              file: _policyFile,
              isDragging: _isDraggingPolicy,
              onDragEntered: () => setState(() => _isDraggingPolicy = true),
              onDragExited: () => setState(() => _isDraggingPolicy = false),
              onFileDropped: (file) => _setFile(file, true),
              onPick: () => _pickFile(isPolicy: true),
              onClear: () => setState(() => _policyFile = null),
            ),
          ),
          SizedBox(width: isWide ? 24 : 0, height: isWide ? 0 : 24),
          Expanded(
            flex: isWide ? 1 : 0,
            child: _uploadCard(
              title: 'Incident Report',
              subtitle: 'Upload the factual report of the event (PDF)',
              file: _incidentFile,
              isDragging: _isDraggingIncident,
              onDragEntered: () => setState(() => _isDraggingIncident = true),
              onDragExited: () => setState(() => _isDraggingIncident = false),
              onFileDropped: (file) => _setFile(file, false),
              onPick: () => _pickFile(isPolicy: false),
              onClear: () => setState(() => _incidentFile = null),
            ),
          ),
        ],
      );
    });
  }

  Widget _uploadCard({
    required String title,
    required String subtitle,
    required PlatformFile? file,
    required bool isDragging,
    required VoidCallback onDragEntered,
    required VoidCallback onDragExited,
    required Function(PlatformFile) onFileDropped,
    required VoidCallback onPick,
    required VoidCallback onClear,
  }) {
    return DropTarget(
      onDragDone: (detail) async {
        if (detail.files.isNotEmpty) {
          final file = detail.files.first;
          final bytes = await file.readAsBytes();
          onFileDropped(PlatformFile(
            name: file.name,
            size: bytes.length,
            bytes: bytes,
          ));
        }
      },
      onDragEntered: (detail) => onDragEntered(),
      onDragExited: (detail) => onDragExited(),
      child: Card(
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.all(24.0),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            color: isDragging ? const Color(0xFFEFF6FF) : Colors.white,
            border: Border.all(
              color: isDragging ? const Color(0xFF1E40AF) : const Color(0xFFE2E8F0),
              width: isDragging ? 2 : 1,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0xFFEFF6FF),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.upload_file, color: Color(0xFF1E40AF)),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                        Text(subtitle, style: TextStyle(fontSize: 13, color: Colors.grey.shade600)),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              InkWell(
                onTap: onPick,
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(vertical: 32),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade50,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.grey.shade200, width: 2, style: BorderStyle.solid),
                  ),
                  child: Column(
                    children: [
                      Icon(
                        isDragging ? Icons.add_circle_outline : Icons.cloud_upload_outlined,
                        size: 40,
                        color: isDragging ? const Color(0xFF1E40AF) : Colors.grey.shade400,
                      ),
                      const SizedBox(height: 12),
                      Text(
                        isDragging
                            ? 'Drop File Here'
                            : (file == null ? 'Drag & Drop or Click to select PDF' : file.name),
                        style: TextStyle(
                          color: (file == null && !isDragging) ? Colors.grey.shade600 : const Color(0xFF1E40AF),
                          fontWeight: (file == null && !isDragging) ? FontWeight.normal : FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              if (file != null) ...[
                const SizedBox(height: 16),
                Row(
                  children: [
                    const Icon(Icons.check_circle, color: Colors.green, size: 16),
                    const SizedBox(width: 8),
                    const Text('Document Ready', style: TextStyle(color: Colors.green, fontSize: 13)),
                    const Spacer(),
                    TextButton(
                      onPressed: onClear,
                      child: const Text('Remove', style: TextStyle(color: Colors.red)),
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildActionSection() {
    return Center(
      child: SizedBox(
        width: 400,
        height: 56,
        child: FilledButton(
          onPressed: _isRunning ? null : _analyze,
          child: _isRunning
              ? const SizedBox(
                  width: 24,
                  height: 24,
                  child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                )
              : const Text(
                  'RUN COMPLIANCE ANALYSIS',
                  style: TextStyle(letterSpacing: 1.1, fontWeight: FontWeight.bold),
                ),
        ),
      ),
    );
  }

  Widget _analyzingBanner() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.blue.shade50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.blue.shade100),
      ),
      child: Row(
        children: [
          const Icon(Icons.auto_awesome, color: Color(0xFF1E40AF)),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Agent Pipeline Executing',
                  style: TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF1E40AF)),
                ),
                const SizedBox(height: 4),
                Text(
                  'Processing semantic layers, assessing severity, and generating recommendations...',
                  style: TextStyle(color: Colors.blue.shade900, fontSize: 13),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _errorBanner(String msg) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.red.shade50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.red.shade100),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: Colors.red),
          const SizedBox(width: 12),
          Expanded(child: Text(msg, style: const TextStyle(color: Colors.red))),
        ],
      ),
    );
  }
}
