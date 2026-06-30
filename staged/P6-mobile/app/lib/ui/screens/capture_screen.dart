/// ui/screens/capture_screen.dart — input manual de captura.
///
/// Phase 1: paste de texto + type picker + slider de pain.
/// Phase 3 adicionará: voz (UC-4), foto+OCR (UC-?).

import 'package:flutter/material.dart';

class CaptureScreen extends StatefulWidget {
  const CaptureScreen({super.key});

  @override
  State<CaptureScreen> createState() => _CaptureScreenState();
}

class _CaptureScreenState extends State<CaptureScreen> {
  final _textController = TextEditingController();
  String _type = 'lesson';
  double _pain = 0.2;
  bool _saving = false;

  static const _types = ['lesson', 'decision', 'project', 'person', 'feedback'];

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Nova captura'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _textController,
              maxLines: 8,
              autofocus: true,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                hintText: 'Cole ou digite o conteúdo aqui...',
              ),
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              value: _type,
              decoration: const InputDecoration(
                labelText: 'Tipo',
                border: OutlineInputBorder(),
              ),
              items: _types
                  .map((t) => DropdownMenuItem(value: t, child: Text(t)))
                  .toList(),
              onChanged: (v) => setState(() => _type = v ?? 'lesson'),
            ),
            const SizedBox(height: 16),
            Text('Pain: ${_pain.toStringAsFixed(1)}'),
            Slider(
              value: _pain,
              min: 0.1,
              max: 1.0,
              divisions: 9,
              label: _pain.toStringAsFixed(1),
              onChanged: (v) => setState(() => _pain = v),
            ),
            const Spacer(),
            FilledButton.icon(
              onPressed: _saving ? null : _save,
              icon: _saving
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.save),
              label: Text(_saving ? 'Salvando…' : 'Salvar'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      // CaptureService.captureText() vai ser ligado via Provider em Phase 2.
      // No kickoff só simulamos pra UI ficar coerente.
      await Future.delayed(const Duration(milliseconds: 300));
      if (!mounted) return;
      Navigator.of(context).pop();
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }
}
