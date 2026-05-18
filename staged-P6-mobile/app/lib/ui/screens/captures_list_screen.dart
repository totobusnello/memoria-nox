/// ui/screens/captures_list_screen.dart — lista de capturas recentes.

import 'package:flutter/material.dart';

class CapturesListScreen extends StatelessWidget {
  const CapturesListScreen({super.key});

  @override
  Widget build(BuildContext context) {
    // Phase 1 placeholder — em Phase 2 conectamos com NoxMemDatabase.
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.bookmark_border, size: 64, color: Colors.grey),
            const SizedBox(height: 16),
            Text(
              'Nenhuma captura ainda.',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            const Text(
              'Use o botão + ou compartilhe texto de outro app.',
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
