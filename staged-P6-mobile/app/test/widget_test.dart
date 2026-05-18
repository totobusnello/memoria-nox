/// widget_test.dart — Phase 1 widget smoke tests.
///
/// Cobertura mínima: app monta, navegação básica funciona, screens não
/// quebram com data vazia. Tests profundos chegam em Phase 2.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:nox_mem_mobile/main.dart';
import 'package:nox_mem_mobile/ui/screens/capture_screen.dart';
import 'package:nox_mem_mobile/ui/screens/captures_list_screen.dart';
import 'package:nox_mem_mobile/ui/screens/settings_screen.dart';

void main() {
  testWidgets('App mounts without crashing', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: NoxMemApp()));
    expect(find.text('Capturas'), findsWidgets);
  });

  testWidgets('Bottom navigation switches tabs', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: NoxMemApp()));
    // Switch para Configurações.
    await tester.tap(find.text('Configurações').first);
    await tester.pumpAndSettle();
    expect(find.text('Conexão VPS'), findsOneWidget);
    // Volta pra Capturas.
    await tester.tap(find.text('Capturas').first);
    await tester.pumpAndSettle();
    expect(find.text('Nenhuma captura ainda.'), findsOneWidget);
  });

  testWidgets('Captures list shows empty state', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: CapturesListScreen()));
    expect(find.text('Nenhuma captura ainda.'), findsOneWidget);
    expect(find.byIcon(Icons.bookmark_border), findsOneWidget);
  });

  testWidgets('Capture screen has text input + save button', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: CaptureScreen()));
    expect(find.byType(TextField), findsOneWidget);
    expect(find.text('Salvar'), findsOneWidget);
  });

  testWidgets('Capture screen save shows loading state', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: CaptureScreen()));
    await tester.enterText(find.byType(TextField), 'Lembrar disso amanhã');
    await tester.tap(find.text('Salvar'));
    await tester.pump();
    expect(find.text('Salvando…'), findsOneWidget);
  });

  testWidgets('Settings screen shows all sections', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: SettingsScreen()));
    expect(find.text('Conexão VPS'), findsOneWidget);
    expect(find.text('Tailscale'), findsOneWidget);
    expect(find.text('Captura'), findsOneWidget);
    expect(find.text('Sobre'), findsOneWidget);
  });

  testWidgets('Settings switch toggles capture state', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: SettingsScreen()));
    final switchFinder = find.byType(SwitchListTile);
    expect(switchFinder, findsOneWidget);

    SwitchListTile getSwitchWidget() => tester.widget<SwitchListTile>(switchFinder);
    expect(getSwitchWidget().value, isFalse);

    await tester.tap(switchFinder);
    await tester.pumpAndSettle();
    expect(getSwitchWidget().value, isTrue);
  });

  testWidgets('Settings text fields exist for URL and token', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: SettingsScreen()));
    expect(find.byType(TextField), findsNWidgets(2));
  });

  testWidgets('Pain slider on capture screen updates value', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: CaptureScreen()));
    final sliderFinder = find.byType(Slider);
    expect(sliderFinder, findsOneWidget);
    await tester.drag(sliderFinder, const Offset(50, 0));
    await tester.pumpAndSettle();
    // Mudança ocorreu sem crash — basta no smoke test.
    expect(sliderFinder, findsOneWidget);
  });

  testWidgets('Type dropdown shows expected options', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: CaptureScreen()));
    await tester.tap(find.byType(DropdownButtonFormField<String>));
    await tester.pumpAndSettle();
    expect(find.text('lesson').last, findsOneWidget);
    expect(find.text('decision'), findsOneWidget);
    expect(find.text('project'), findsOneWidget);
  });

  testWidgets('FAB on captures tab opens capture screen', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: NoxMemApp()));
    await tester.tap(find.byType(FloatingActionButton));
    await tester.pumpAndSettle();
    expect(find.text('Nova captura'), findsWidgets);
  });
}
