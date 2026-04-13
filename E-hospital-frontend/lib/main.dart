import 'package:flutter/material.dart';
import 'screens/home_screen.dart';
import 'screens/results_screen.dart';

void main() => runApp(const EHospitalApp());

class EHospitalApp extends StatelessWidget {
  const EHospitalApp({super.key});

  @override
  Widget build(BuildContext context) {
    // Professional Medical/Corporate Theme based on e-hospital dashboard
    final primaryBlue = Color(0xFF1E40AF); // Deep Blue
    final surfaceBg = Color(0xFFF8FAFC); // Very light grey/white surface

    return MaterialApp(
      title: 'E-Hospital Compliance Dashboard',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: primaryBlue,
          primary: primaryBlue,
          secondary: Color(0xFF3B82F6),
          surface: Colors.white,
          background: surfaceBg,
        ),
        scaffoldBackgroundColor: surfaceBg,
        cardTheme: CardThemeData(
          color: Colors.white,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(color: Color(0xFFE2E8F0), width: 1),
          ),
        ),
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
            backgroundColor: primaryBlue,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
            ),
            padding: EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          ),
        ),
        textTheme: const TextTheme(
          headlineLarge: TextStyle(
            fontSize: 28,
            fontWeight: FontWeight.bold,
            color: Color(0xFF1E293B),
          ),
          headlineMedium: TextStyle(
            fontSize: 22,
            fontWeight: FontWeight.w600,
            color: Color(0xFF1E293B),
          ),
          bodyLarge: TextStyle(
            fontSize: 16,
            color: Color(0xFF475569),
          ),
        ),
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
