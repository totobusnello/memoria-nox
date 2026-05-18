/// capture_service_test.dart — Phase 1 contract test for capture.
///
/// Não exercita SQLCipher real (requer DB lifecycle Flutter binding) — apenas
/// valida helpers de serialização e PII filter pre-check.

import 'package:flutter_test/flutter_test.dart';
import 'package:nox_mem_mobile/capture/capture_service.dart';
import 'package:nox_privacy/nox_privacy.dart';

void main() {
  group('pendingChunkToPayload — serialização', () {
    test('extrai campos esperados', () {
      final row = {
        'id': 42,
        'text': 'algo aprendido',
        'type': 'lesson',
        'created_at': '2026-05-18T10:00:00Z',
        'pain': 0.4,
      };
      final payload = pendingChunkToPayload(localId: 'uuid-1', chunkRow: row);
      expect(payload['local_id'], equals('uuid-1'));
      expect(payload['text'], equals('algo aprendido'));
      expect(payload['type'], equals('lesson'));
      expect(payload['pain'], equals(0.4));
    });
  });

  group('encodeUploadBody — JSON envelope', () {
    test('envelope com chunks array', () {
      final body = encodeUploadBody([
        {'local_id': 'u1', 'text': 'a', 'type': 'lesson', 'pain': 0.2}
      ]);
      expect(body, contains('chunks'));
      expect(body, contains('u1'));
    });
  });

  group('PII filter integration with capture', () {
    test('CPF in text is redacted before persist', () {
      const raw = 'Toto CPF 111.444.777-35 confidencial';
      final r = redactAll(raw, minConfidence: 0.7);
      expect(r.redactionCount, greaterThanOrEqualTo(1));
      expect(r.redacted, contains('[REDACTED:cpf]'));
      expect(r.redacted.contains('111.444.777-35'), isFalse);
    });

    test('API token in text is redacted', () {
      const raw = 'export NOX_API_TOKEN=sk-ant-api03-EXAMPLEABCDEFGHIJKLMNOPQRSTUVWXYZ1234567';
      final r = redactAll(raw, minConfidence: 0.5);
      expect(r.redactionCount, greaterThanOrEqualTo(1));
      expect(r.redacted.contains('sk-ant-api03'), isFalse);
    });

    test('PEM private key block is redacted', () {
      const raw = '''
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAfake-key-here-not-real
-----END RSA PRIVATE KEY-----
''';
      final r = redactAll(raw, minConfidence: 0.5);
      expect(r.redactionCount, greaterThanOrEqualTo(1));
      expect(r.redacted.contains('BEGIN RSA PRIVATE KEY'), isFalse);
    });
  });
}
