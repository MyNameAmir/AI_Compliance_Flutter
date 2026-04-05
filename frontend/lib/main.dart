import 'package:flutter/material.dart';
import 'screens/home_screen.dart';
import 'screens/results_screen.dart';

void main() => runApp(const ComplianceApp());

class ComplianceApp extends StatelessWidget {
  const ComplianceApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Hospital Compliance Checker',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFF0D9488),
        useMaterial3: true,
        brightness: Brightness.light,
      ),
      initialRoute: '/',
      onGenerateRoute: (settings) {
        if (settings.name == '/results') {
          final args = settings.arguments as Map<String, dynamic>;
          return MaterialPageRoute(
            builder: (_) => ResultsScreen(data: args),
          );
        }
        return MaterialPageRoute(builder: (_) => const HomeScreen());
      },
    );
  }
}