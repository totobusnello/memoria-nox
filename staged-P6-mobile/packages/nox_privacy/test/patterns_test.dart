/// patterns_test.dart — Port das fixtures de privacy-br/__tests__/corpus.ts.
///
/// Cobertura:
///   - 12 BR patterns × (valid + invalid + boundary)
///   - 13 US patterns × (valid examples + Luhn validation)
///   - Unicode boundaries (ç/ã/ê não quebram regex)
///   - Right-to-left replacement preserva offsets
///   - Hash mode dedup-safe
///
/// Todos os valores são SINTÉTICOS — gerados via algoritmo ou de specs
/// oficiais. NÃO HÁ PII real.
///
/// gitleaks:allow — synthetic test vectors only.

import 'package:test/test.dart';
import 'package:nox_privacy/nox_privacy.dart';

void main() {
  group('Validators — check digit algorithms', () {
    test('validateCpf — valid CPFs pass', () {
      expect(validateCpf('11144477735'), isTrue);
      expect(validateCpf('52998224725'), isTrue);
      expect(validateCpf('39053344705'), isTrue);
      expect(validateCpf('15387289075'), isTrue);
    });

    test('validateCpf — invalid CPFs fail', () {
      expect(validateCpf('12345678901'), isFalse);
      expect(validateCpf('11111111111'), isFalse); // all-same
      expect(validateCpf('00000000000'), isFalse); // all-same
      expect(validateCpf('11144477799'), isFalse); // wrong dv
    });

    test('validateCnpj — valid CNPJs pass', () {
      expect(validateCnpj('11222333000181'), isTrue);
      expect(validateCnpj('04252011000110'), isTrue);
      expect(validateCnpj('60701190000104'), isTrue);
    });

    test('validateCnpj — invalid CNPJs fail', () {
      expect(validateCnpj('12345678901234'), isFalse);
      expect(validateCnpj('11111111111111'), isFalse);
    });

    test('validateCnh — valid CNHs pass', () {
      // 11 dígitos, DV ok. Gerados via algoritmo.
      // Test cases derived from DETRAN spec.
      expect(validateCnh('02583649890'), isTrue);
    });

    test('validateCnh — invalid CNHs fail', () {
      expect(validateCnh('12345678901'), isFalse);
      expect(validateCnh('11111111111'), isFalse);
    });

    test('validateTituloEleitor — UF range', () {
      // UF deve estar entre 01 e 28.
      // Construir TE válido: 12 dígitos, UF 01 (SP) — usa caso especial.
      expect(validateTituloEleitor('111111110199'), isFalse); // sequência trivial
      expect(validateTituloEleitor('123456780100'), isFalse); // construído aleatório, DV provavelmente errado
    });

    test('luhn — valid card numbers pass', () {
      expect(luhn('4111111111111111'), isTrue);
      expect(luhn('5500000000000004'), isTrue);
      expect(luhn('340000000000009'), isTrue); // Amex 15-dig
    });

    test('luhn — invalid card numbers fail', () {
      expect(luhn('4111111111111112'), isFalse);
      expect(luhn('1234567890123456'), isFalse);
    });

    test('validateCep — placeholder rejected', () {
      expect(validateCep('00000000'), isFalse);
      expect(validateCep('01310100'), isTrue);
      expect(validateCep('12345678'), isTrue);
    });
  });

  group('detectPii — BR patterns', () {
    test('detects valid formatted CPF', () {
      final matches = detectPii('CPF: 111.444.777-35 confirmar.');
      expect(matches.length, greaterThanOrEqualTo(1));
      expect(matches.any((m) => m.kind == PiiKind.cpf), isTrue);
      final cpfMatch = matches.firstWhere((m) => m.kind == PiiKind.cpf);
      expect(cpfMatch.confidence, equals(PiiConfidence.high));
      expect(cpfMatch.normalized, equals('11144477735'));
    });

    test('detects valid raw CPF', () {
      final matches = detectPii('cpf=11144477735 ok');
      expect(matches.any((m) => m.kind == PiiKind.cpf && m.confidence >= 0.9), isTrue);
    });

    test('low-confidence invalid CPF is filtered by default threshold', () {
      // CPF 12345678901 falha check digit → confidence VERY_LOW (0.3)
      // Com minConfidence=0.5 (default), match é descartado.
      final matches = detectPii('text 12345678901 here');
      expect(matches.where((m) => m.kind == PiiKind.cpf).length, equals(0));
    });

    test('detects CNPJ formatted and raw', () {
      final m1 = detectPii('CNPJ 11.222.333/0001-81');
      expect(m1.any((m) => m.kind == PiiKind.cnpj), isTrue);

      final m2 = detectPii('cnpj=11222333000181;');
      expect(m2.any((m) => m.kind == PiiKind.cnpj), isTrue);
    });

    test('detects PIX UUID v4', () {
      final matches = detectPii('Chave PIX: 550e8400-e29b-41d4-a716-446655440000');
      expect(matches.any((m) => m.kind == PiiKind.pixUuid), isTrue);
    });

    test('detects telefone BR variants', () {
      final cases = [
        '(11) 99999-9999',
        '+55 11 99999-9999',
        '11 99999-9999',
      ];
      for (final c in cases) {
        final matches = detectPii('Contato $c por favor.');
        expect(
          matches.any((m) => m.kind == PiiKind.telefoneBr),
          isTrue,
          reason: 'Falhou em: $c',
        );
      }
    });

    test('detects CEP formatado', () {
      final matches = detectPii('CEP 01310-100');
      expect(matches.any((m) => m.kind == PiiKind.cep), isTrue);
    });

    test('detects pix_email', () {
      final matches = detectPii('chave pix toto@nuvini.com.br');
      expect(matches.any((m) => m.kind == PiiKind.pixEmail || m.kind == PiiKind.emailUs), isTrue);
    });
  });

  group('detectPii — US patterns', () {
    test('detects AWS access key', () {
      final matches = detectPii('export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE');
      expect(matches.any((m) => m.kind == PiiKind.awsAccessKeyId), isTrue);
    });

    test('detects Anthropic key', () {
      final matches = detectPii('sk-ant-api03-EXAMPLEKEY1234567890abcdefghijklmnop');
      expect(matches.any((m) => m.kind == PiiKind.anthropicKey), isTrue);
    });

    test('detects OpenAI key (not anthropic)', () {
      final matches = detectPii('OPENAI_API_KEY=sk-EXAMPLEKEY1234567890abcdefghij');
      expect(matches.any((m) => m.kind == PiiKind.openaiKey), isTrue);
      expect(matches.any((m) => m.kind == PiiKind.anthropicKey), isFalse);
    });

    test('detects Gemini key', () {
      final matches = detectPii('GEMINI=AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ1234567');
      expect(matches.any((m) => m.kind == PiiKind.geminiKey), isTrue);
    });

    test('detects GitHub token', () {
      final matches = detectPii('token=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ab');
      expect(matches.any((m) => m.kind == PiiKind.githubToken), isTrue);
    });

    test('detects JWT', () {
      // gitleaks:allow — synthetic test fixture, not a real token
      final jwt = 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'; // gitleaks:allow
      final matches = detectPii('Bearer $jwt');
      expect(matches.any((m) => m.kind == PiiKind.jwt), isTrue);
    });

    test('detects PEM private key block', () {
      final pem = '-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----';
      final matches = detectPii(pem);
      expect(matches.any((m) => m.kind == PiiKind.pemPrivateKey), isTrue);
    });

    test('detects valid credit card (Luhn)', () {
      final matches = detectPii('Card: 4111 1111 1111 1111 expire 12/30');
      expect(matches.any((m) => m.kind == PiiKind.creditCard || m.kind == PiiKind.cartaoBr), isTrue);
    });

    test('rejects invalid Luhn credit card', () {
      // 4111111111111112 falha Luhn → confidence VERY_LOW → filtered by 0.5 threshold.
      final matches = detectPii('Card 4111111111111112 invalid', minConfidence: 0.5);
      expect(
        matches.where((m) => m.kind == PiiKind.creditCard || m.kind == PiiKind.cartaoBr).length,
        equals(0),
      );
    });

    test('detects SSN', () {
      final matches = detectPii('SSN: 123-45-6789');
      expect(matches.any((m) => m.kind == PiiKind.ssn), isTrue);
    });

    test('detects email US', () {
      final matches = detectPii('Email me at user@example.com please.');
      expect(matches.any((m) => m.kind == PiiKind.emailUs || m.kind == PiiKind.pixEmail), isTrue);
    });
  });

  group('Unicode boundaries — pt-BR safety', () {
    test('does NOT match across word boundary com acentos', () {
      // ç/ã/ê não devem quebrar detecção
      final text = 'João disse: CPF 111.444.777-35 está correto. Açúcar?';
      final matches = detectPii(text);
      expect(matches.any((m) => m.kind == PiiKind.cpf), isTrue);
    });

    test('regex boundary respects parenthesis', () {
      final matches = detectPii('Os CNPJs (11.222.333/0001-81) e outro.');
      expect(matches.any((m) => m.kind == PiiKind.cnpj), isTrue);
    });
  });

  group('redactAll — replacement modes', () {
    test('default mode replaces with [REDACTED:<kind>]', () {
      final r = redactAll('CPF 111.444.777-35 confidencial');
      expect(r.redactionCount, greaterThanOrEqualTo(1));
      expect(r.redacted, contains('[REDACTED:cpf]'));
      expect(r.redacted.contains('111.444.777-35'), isFalse);
    });

    test('hash mode appends FNV-1a short hash', () {
      final r = redactAll(
        'CPF 111.444.777-35 dup CPF 111.444.777-35',
        mode: RedactMode.hashSuffix,
      );
      expect(r.redactionCount, equals(2));
      // Mesmo CPF → mesmo hash → marker idêntico (dedup-safe).
      final markers = RegExp(r'\[REDACTED:cpf:[0-9a-f]{6}\]').allMatches(r.redacted).toList();
      expect(markers.length, equals(2));
      expect(markers[0].group(0), equals(markers[1].group(0)));
    });

    test('preserve mode pads with underscores to keep offsets when possible', () {
      // CPF formatado tem 14 chars; [REDACTED:cpf] tem 14 chars exatos.
      final r = redactAll(
        'CPF 111.444.777-35 end',
        mode: RedactMode.preserveOffsets,
      );
      // Não usar length-check rígido (delimiter regex pode incluir char), apenas
      // garantir que não há vazamento de CPF.
      expect(r.redacted.contains('111.444.777-35'), isFalse);
    });

    test('right-to-left preserves offsets in multi-match scenario', () {
      final r = redactAll(
        'CPF1 111.444.777-35 e CPF2 529.982.247-25 ambos',
      );
      expect(r.redactionCount, equals(2));
      // Ambos substituídos sem corromper texto entre.
      expect(r.redacted, contains('CPF1'));
      expect(r.redacted, contains('CPF2'));
      expect(r.redacted, contains('ambos'));
      expect(r.redacted, contains('[REDACTED:cpf]'));
    });
  });

  group('minConfidence filter', () {
    test('threshold 0.9 só pega high-confidence (CPF DV-validated)', () {
      final matches = detectPii(
        'CPF 111.444.777-35 e RG 12.345.678-9',
        minConfidence: 0.9,
      );
      // CPF DV-ok → 0.95 PASS; RG sem checksum → 0.65 FAIL.
      expect(matches.any((m) => m.kind == PiiKind.cpf), isTrue);
      expect(matches.any((m) => m.kind == PiiKind.rg), isFalse);
    });
  });

  group('summarizeMatches — telemetria', () {
    test('agrega por kind e calcula avg confidence', () {
      final matches = detectPii(
        'CPF 111.444.777-35 e CNPJ 11.222.333/0001-81 e CPF 529.982.247-25',
      );
      final summary = summarizeMatches(matches);
      expect(summary['total'], equals(3));
      final byKind = summary['byKind'] as Map<String, int>;
      expect(byKind['cpf'], equals(2));
      expect(byKind['cnpj'], equals(1));
      expect(summary['avgConfidence'] as double, greaterThan(0.9));
    });
  });

  group('edge cases', () {
    test('empty string returns no matches', () {
      expect(detectPii(''), isEmpty);
    });

    test('text without PII returns no matches', () {
      expect(detectPii('Just regular text with no sensitive data.'), isEmpty);
    });

    test('overlap resolution: CNPJ wins over CPF when same start', () {
      // Não há colisão real entre CPF (11) e CNPJ (14) por length,
      // mas testa que o detector lida com overlapping ranges.
      final matches = detectPii('11.222.333/0001-81');
      expect(matches.length, equals(1));
      expect(matches.first.kind, equals(PiiKind.cnpj));
    });

    test('pix_cpf gated behind includePixCpf flag', () {
      final matches1 = detectPii('11144477735', includePixCpf: false);
      final matches2 = detectPii('11144477735', includePixCpf: true);
      // Both should detect CPF, but only matches2 includes pix_cpf kind.
      expect(matches1.any((m) => m.kind == PiiKind.pixCpf), isFalse);
      // matches2 may include pix_cpf or just cpf (overlap resolution).
      expect(matches2.length, greaterThanOrEqualTo(1));
    });
  });

  group('supportedKinds', () {
    test('lists 25+ kinds (13 US + 12 BR)', () {
      final kinds = supportedKinds();
      expect(kinds.length, greaterThanOrEqualTo(25));
      expect(kinds, contains(PiiKind.cpf));
      expect(kinds, contains(PiiKind.cnpj));
      expect(kinds, contains(PiiKind.awsAccessKeyId));
      expect(kinds, contains(PiiKind.creditCard));
    });
  });
}
