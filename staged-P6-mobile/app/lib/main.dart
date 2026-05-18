/// main.dart — entrypoint do app nox-mem mobile (Phase 1 kickoff).
///
/// Wireframe Phase 1:
///   - SplashScreen (boot + DB unlock via biometria)
///   - MainScreen com BottomNavigation (Captures / Settings)
///   - CaptureScreen (paste + share intent target)
///
/// Phase 2+3 deferidas: SearchScreen, AnswerScreen, ConflictTriageScreen.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'ui/screens/main_screen.dart';

void main() {
  // O runZonedGuarded vai ser adicionado em Phase 3 quando integrarmos
  // crashlytics + telemetria de sync. No kickoff mantemos main() linear.
  runApp(const ProviderScope(child: NoxMemApp()));
}

class NoxMemApp extends StatelessWidget {
  const NoxMemApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'nox-mem',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.indigo),
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.indigo,
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      themeMode: ThemeMode.system,
      home: const MainScreen(),
    );
  }
}
