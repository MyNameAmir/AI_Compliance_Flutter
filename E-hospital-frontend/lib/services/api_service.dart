import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;

class EHospitalApiService {
  // Use the same base URL as the existing backend
  static const String _baseUrl = 'http://127.0.0.1:8002';

  /// Upload policy + incident PDFs and return the full analysis result.
  static Future<Map<String, dynamic>> analyze({
    required Uint8List policyBytes,
    required String policyName,
    required Uint8List incidentBytes,
    required String incidentName,
  }) async {
    final uri = Uri.parse('$_baseUrl/analyze');
    final request = http.MultipartRequest('POST', uri)
      ..files.add(http.MultipartFile.fromBytes(
        'policy',
        policyBytes,
        filename: policyName,
      ))
      ..files.add(http.MultipartFile.fromBytes(
        'incident',
        incidentBytes,
        filename: incidentName,
      ));

    final streamed = await request.send();
    final body = await streamed.stream.bytesToString();

    if (streamed.statusCode != 200) {
      final err = jsonDecode(body);
      throw Exception(err['error'] ?? 'Server error ${streamed.statusCode}');
    }

    return jsonDecode(body) as Map<String, dynamic>;
  }

  /// Get all violations for the dashboard history
  static Future<List<dynamic>> getViolations() async {
    final uri = Uri.parse('$_baseUrl/violations');
    final response = await http.get(uri);
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as List<dynamic>;
    } else {
      throw Exception('Failed to load violations');
    }
  }
}
