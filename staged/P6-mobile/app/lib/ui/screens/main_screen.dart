/// ui/screens/main_screen.dart — host com BottomNavigation.
///
/// Tabs:
///   1. Captures — lista de recent + FAB pra novo
///   2. Settings — VPS URL, token, Tailscale status
///
/// Phase 2 vai adicionar tabs Search + Answer. Por isso o nav usa lista
/// mutável (vs. hard-coded indexes) — fácil estender.

import 'package:flutter/material.dart';

import 'capture_screen.dart';
import 'captures_list_screen.dart';
import 'settings_screen.dart';

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _index = 0;

  static const List<_TabSpec> _tabs = [
    _TabSpec(
      label: 'Capturas',
      icon: Icons.bookmark_added_outlined,
      activeIcon: Icons.bookmark_added,
      child: CapturesListScreen(),
    ),
    _TabSpec(
      label: 'Configurações',
      icon: Icons.settings_outlined,
      activeIcon: Icons.settings,
      child: SettingsScreen(),
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final tab = _tabs[_index];
    return Scaffold(
      appBar: AppBar(title: Text(tab.label)),
      body: tab.child,
      floatingActionButton: _index == 0
          ? FloatingActionButton.extended(
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => const CaptureScreen(),
                  ),
                );
              },
              icon: const Icon(Icons.add),
              label: const Text('Nova captura'),
            )
          : null,
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: _tabs
            .map(
              (t) => NavigationDestination(
                icon: Icon(t.icon),
                selectedIcon: Icon(t.activeIcon),
                label: t.label,
              ),
            )
            .toList(),
      ),
    );
  }
}

class _TabSpec {
  const _TabSpec({
    required this.label,
    required this.icon,
    required this.activeIcon,
    required this.child,
  });

  final String label;
  final IconData icon;
  final IconData activeIcon;
  final Widget child;
}
