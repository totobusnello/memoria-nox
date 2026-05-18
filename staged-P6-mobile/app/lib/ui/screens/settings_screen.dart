/// ui/screens/settings_screen.dart — VPS URL + token + Tailscale status.
///
/// Phase 1 wireframe. Phase 2 conecta com flutter_secure_storage + TailscaleManager.

import 'package:flutter/material.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _urlController = TextEditingController();
  final _tokenController = TextEditingController();
  bool _captureEnabled = false;

  @override
  void dispose() {
    _urlController.dispose();
    _tokenController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _section('Conexão VPS'),
        TextField(
          controller: _urlController,
          decoration: const InputDecoration(
            labelText: 'URL da VPS no Tailnet',
            helperText: 'Ex: http://100.x.y.z:18802',
            border: OutlineInputBorder(),
          ),
          keyboardType: TextInputType.url,
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _tokenController,
          decoration: const InputDecoration(
            labelText: 'Bearer token (NOX_API_TOKEN)',
            border: OutlineInputBorder(),
          ),
          obscureText: true,
        ),
        const SizedBox(height: 24),
        _section('Tailscale'),
        const Card(
          child: ListTile(
            leading: Icon(Icons.lan_outlined),
            title: Text('Status: detectando…'),
            subtitle: Text('Phase 2 — TailscaleManager ainda não wired.'),
          ),
        ),
        const SizedBox(height: 24),
        _section('Captura'),
        SwitchListTile(
          value: _captureEnabled,
          title: const Text('Habilitar captura'),
          subtitle: const Text('PII filter ativo + SQLCipher local.'),
          onChanged: (v) => setState(() => _captureEnabled = v),
        ),
        const SizedBox(height: 24),
        _section('Sobre'),
        const Card(
          child: ListTile(
            leading: Icon(Icons.info_outline),
            title: Text('nox-mem mobile'),
            subtitle: Text('Phase 1 kickoff — v0.1.0'),
          ),
        ),
      ],
    );
  }

  Widget _section(String title) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Text(
        title,
        style: Theme.of(context).textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.bold,
              color: Theme.of(context).colorScheme.primary,
            ),
      ),
    );
  }
}
