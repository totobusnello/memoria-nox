/// nox_privacy/patterns.dart — Dart port de privacy/patterns.ts (A1 US)
/// + privacy-br/patterns.ts (A1.1 BR).
///
/// Total: 13 US + 12 BR = 25 padrões.
///
/// CUIDADOS load-bearing:
///
///   - Em Dart, `\b` no RegExp falha em Unicode da mesma forma que em JS.
///     Caracteres `ç`, `ã`, `ê` não são word chars. Por isso usamos
///     lookbehind/lookahead Unicode-safe (`SOL`/`EOL` abaixo).
///
///   - Algoritmos de check-digit:
///     - CPF: pesos 10..2 (DV1), 11..2 (DV2)
///     - CNPJ: pesos [5,4,3,2,9,8,7,6,5,4,3,2] (DV1); [6,5,4,3,2,9,8,7,6,5,4,3,2] (DV2)
///     - CNH: pesos 9..1 (DV1), 1..9 (DV2) com delta `dsv`
///     - Título de Eleitor: pesos 2..9 (DV1), [7,8,9] sobre UF+DV1 (DV2),
///                          SP/MG (UF=01/02) têm caso especial mod==0 → dv=1
///     - Cartão: Luhn (mod 10)
///
///   - Sequências triviais (000...0, 111...1) são REJEITADAS — formalmente
///     passam check mas em prática são placeholders, geram FP em docs.
///
///   - Ordem de prioridade do catálogo:
///     CNPJ (14 dig) > PIX UUID > CPF (11 dig) > cartão (13–19 dig) >
///     telefone BR > PIX phone > PIX email > PIX CPF > CEP > RG > CNH > TE
///
///   - Tests em test/patterns_test.dart cobrem positives + negatives + edge.

import 'types.dart';

// ─── Boundary helpers — Unicode-safe ─────────────────────────────────────────
// Dart RegExp aceita lookbehind/lookahead. Replicamos os mesmos delimitadores
// do TS para garantir parity de cobertura:
//   start  : start-of-string, whitespace, ()[]<> , ; : . / = " '
//   end    : end-of-string, whitespace, )]><    , ; : . ! ? / = " ' -
// Não usamos raw strings aqui porque o regex precisa conter ambos `"` e `'`.
// String regular com escape duplo de `\\` resolve sem ambiguidade.
const String _sol = "(?<=^|[\\s(,;:./=\"'\\[<>])";
const String _eol = "(?=[\\s),;:.!?/=\"'\\]>-]|\$)";

/// Remove tudo que não for dígito.
String _digitsOnly(String s) => s.replaceAll(RegExp(r'\D'), '');

// ─── Validators ──────────────────────────────────────────────────────────────

/// Algoritmo Luhn (Mod 10) — cartões de crédito.
bool luhn(String digits) {
  if (!RegExp(r'^\d+$').hasMatch(digits)) return false;
  int sum = 0;
  bool alt = false;
  for (int i = digits.length - 1; i >= 0; i--) {
    int n = int.parse(digits[i]);
    if (alt) {
      n *= 2;
      if (n > 9) n -= 9;
    }
    sum += n;
    alt = !alt;
  }
  return sum % 10 == 0;
}

/// CPF check digit — algoritmo Receita Federal.
bool validateCpf(String digits) {
  if (!RegExp(r'^\d{11}$').hasMatch(digits)) return false;
  // Rejeita 11 dígitos idênticos (000...0, 111...1, ..., 999...9).
  if (RegExp(r'^(\d)\1{10}$').hasMatch(digits)) return false;

  // DV1
  int sum = 0;
  for (int i = 0; i < 9; i++) {
    sum += int.parse(digits[i]) * (10 - i);
  }
  int mod = sum % 11;
  final dv1 = mod < 2 ? 0 : 11 - mod;
  if (dv1 != int.parse(digits[9])) return false;

  // DV2
  sum = 0;
  for (int i = 0; i < 10; i++) {
    sum += int.parse(digits[i]) * (11 - i);
  }
  mod = sum % 11;
  final dv2 = mod < 2 ? 0 : 11 - mod;
  return dv2 == int.parse(digits[10]);
}

/// CNPJ check digit — algoritmo Receita Federal.
bool validateCnpj(String digits) {
  if (!RegExp(r'^\d{14}$').hasMatch(digits)) return false;
  if (RegExp(r'^(\d)\1{13}$').hasMatch(digits)) return false;

  const w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  const w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];

  int sum = 0;
  for (int i = 0; i < 12; i++) {
    sum += int.parse(digits[i]) * w1[i];
  }
  int mod = sum % 11;
  final dv1 = mod < 2 ? 0 : 11 - mod;
  if (dv1 != int.parse(digits[12])) return false;

  sum = 0;
  for (int i = 0; i < 13; i++) {
    sum += int.parse(digits[i]) * w2[i];
  }
  mod = sum % 11;
  final dv2 = mod < 2 ? 0 : 11 - mod;
  return dv2 == int.parse(digits[13]);
}

/// CNH check digit — algoritmo DETRAN.
bool validateCnh(String digits) {
  if (!RegExp(r'^\d{11}$').hasMatch(digits)) return false;
  if (RegExp(r'^(\d)\1{10}$').hasMatch(digits)) return false;

  // DV1
  int sum = 0;
  int dsv = 0;
  for (int i = 0, j = 9; i < 9; i++, j--) {
    sum += int.parse(digits[i]) * j;
  }
  int dv1 = sum % 11;
  if (dv1 >= 10) {
    dv1 = 0;
    dsv = 2;
  }
  if (dv1 != int.parse(digits[9])) return false;

  // DV2
  sum = 0;
  for (int i = 0, j = 1; i < 9; i++, j++) {
    sum += int.parse(digits[i]) * j;
  }
  final x = sum % 11;
  int dv2 = x >= 10 ? 0 : x - dsv;
  if (dv2 < 0) dv2 += 11;
  return dv2 == int.parse(digits[10]);
}

/// Título de Eleitor — algoritmo TSE com caso especial SP/MG.
bool validateTituloEleitor(String digits) {
  if (!RegExp(r'^\d{12}$').hasMatch(digits)) return false;
  if (RegExp(r'^(\d)\1{11}$').hasMatch(digits)) return false;

  final uf = digits.substring(8, 10);
  final ufNum = int.parse(uf);
  // UF válida: 01 (SP) a 28 (Exterior).
  if (ufNum < 1 || ufNum > 28) return false;

  final isSpMg = uf == '01' || uf == '02';

  int sum = 0;
  for (int i = 0; i < 8; i++) {
    sum += int.parse(digits[i]) * (i + 2);
  }
  int mod = sum % 11;
  int dv1;
  if (mod == 10) {
    dv1 = 0;
  } else if (mod == 0 && isSpMg) {
    dv1 = 1;
  } else {
    dv1 = mod;
  }
  if (dv1 != int.parse(digits[10])) return false;

  sum = int.parse(digits[8]) * 7 +
      int.parse(digits[9]) * 8 +
      dv1 * 9;
  mod = sum % 11;
  int dv2;
  if (mod == 10) {
    dv2 = 0;
  } else if (mod == 0 && isSpMg) {
    dv2 = 1;
  } else {
    dv2 = mod;
  }
  return dv2 == int.parse(digits[11]);
}

/// CEP — formato 5+3 dígitos. Reject placeholder 00000000.
bool validateCep(String digits) {
  if (!RegExp(r'^\d{8}$').hasMatch(digits)) return false;
  if (digits == '00000000') return false;
  return true;
}

// ─── Pattern catalogue ───────────────────────────────────────────────────────

/// Definição interna de cada padrão. Cada entry mapeia diretamente para
/// uma entry no `REDACTION_PATTERNS` (A1 US) ou `BR_PATTERNS` (A1.1 BR).
class _PatternDef {
  _PatternDef({
    required this.kind,
    required this.regex,
    this.validator,
    required this.confidenceWhenValid,
    this.confidenceWhenInvalid,
    required this.normalize,
  });

  final PiiKind kind;
  final RegExp regex;
  final bool Function(String normalized)? validator;
  final double confidenceWhenValid;
  final double? confidenceWhenInvalid;
  final String Function(String raw) normalize;
}

/// 13 padrões US (A1) — espelha staged-privacy/edits/privacy/patterns.ts.
final List<_PatternDef> _usPatterns = [
  // 1. PEM private key (multiline, dotall via [\s\S]).
  _PatternDef(
    kind: PiiKind.pemPrivateKey,
    regex: RegExp(
      r'-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----',
      multiLine: true,
    ),
    confidenceWhenValid: PiiConfidence.high,
    normalize: (s) => s,
  ),
  // 2. AWS access key id.
  _PatternDef(
    kind: PiiKind.awsAccessKeyId,
    regex: RegExp(r'\bAKIA[0-9A-Z]{16}\b'),
    confidenceWhenValid: PiiConfidence.high,
    normalize: (s) => s,
  ),
  // 3. AWS secret access key (env var prefix).
  _PatternDef(
    kind: PiiKind.awsSecretKey,
    regex: RegExp(
      "(?:aws_secret_access_key|AWS_SECRET_ACCESS_KEY)\\s*[=:]\\s*[\"']?([A-Za-z0-9/+]{40})[\"']?",
      caseSensitive: false,
    ),
    confidenceWhenValid: PiiConfidence.high,
    normalize: (s) => s,
  ),
  // 4. Anthropic key.
  _PatternDef(
    kind: PiiKind.anthropicKey,
    regex: RegExp(r'\bsk-ant-(?:api\d+-)?[a-zA-Z0-9_-]{20,}\b'),
    confidenceWhenValid: PiiConfidence.high,
    normalize: (s) => s,
  ),
  // 5. OpenAI key.
  _PatternDef(
    kind: PiiKind.openaiKey,
    regex: RegExp(r'\bsk-(?!ant-)[a-zA-Z0-9_-]{20,}\b'),
    confidenceWhenValid: PiiConfidence.high,
    normalize: (s) => s,
  ),
  // 6. Gemini / Google API key.
  _PatternDef(
    kind: PiiKind.geminiKey,
    regex: RegExp(r'\bAIza[0-9A-Za-z\-_]{35}\b'),
    confidenceWhenValid: PiiConfidence.high,
    normalize: (s) => s,
  ),
  // 7. GitHub token.
  _PatternDef(
    kind: PiiKind.githubToken,
    regex: RegExp(r'\b(?:ghp_|gho_|ghu_|ghs_|ghr_)[A-Za-z0-9_]{36,}\b'),
    confidenceWhenValid: PiiConfidence.high,
    normalize: (s) => s,
  ),
  // 8. SSH private key line (compact form, single line).
  _PatternDef(
    kind: PiiKind.sshPrivateKeyLine,
    regex: RegExp(r'\bssh-(?:rsa|dss|ed25519|ecdsa)\s+[A-Za-z0-9+/]{40,}={0,2}\b'),
    confidenceWhenValid: PiiConfidence.mediumHigh,
    normalize: (s) => s,
  ),
  // 9. JWT.
  _PatternDef(
    kind: PiiKind.jwt,
    regex: RegExp(r'\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b'),
    confidenceWhenValid: PiiConfidence.high,
    normalize: (s) => s,
  ),
  // 10. Generic high-entropy (40+ chars base64-ish após `password|secret|token`).
  _PatternDef(
    kind: PiiKind.genericHighEntropy,
    regex: RegExp(
      "(?:password|passwd|secret|token|api_?key)\\s*[=:]\\s*[\"']?([A-Za-z0-9/+=_-]{32,})[\"']?",
      caseSensitive: false,
    ),
    confidenceWhenValid: PiiConfidence.medium,
    normalize: (s) => s,
  ),
  // 11. Email US (genérico — A1 trata como PII porque pode ser identificação).
  _PatternDef(
    kind: PiiKind.emailUs,
    regex: RegExp(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'),
    confidenceWhenValid: PiiConfidence.mediumHigh,
    normalize: (s) => s.toLowerCase(),
  ),
  // 12. SSN (xxx-xx-xxxx).
  _PatternDef(
    kind: PiiKind.ssn,
    regex: RegExp(r'\b\d{3}-\d{2}-\d{4}\b'),
    confidenceWhenValid: PiiConfidence.high,
    normalize: _digitsOnly,
  ),
  // 13. Credit card (genérico — qualquer 13–19 dígitos com separador opcional, Luhn).
  _PatternDef(
    kind: PiiKind.creditCard,
    regex: RegExp(r'\b(?:\d{4}[\s-]?){3}\d{1,7}\b'),
    validator: (n) => luhn(n) && n.length >= 13 && n.length <= 19 && !RegExp(r'^(\d)\1+$').hasMatch(n),
    confidenceWhenValid: PiiConfidence.high,
    confidenceWhenInvalid: PiiConfidence.veryLow,
    normalize: _digitsOnly,
  ),
];

/// 12 padrões BR (A1.1) — espelha staged-A1.1/edits/src/lib/privacy-br/patterns.ts.
///
/// Ordem importa: CNPJ (14 dig) > PIX UUID > CPF (11 dig) > cartão >
/// telefone BR > PIX phone > PIX email > PIX CPF > CEP > RG > CNH > TE.
final List<_PatternDef> _brPatterns = [
  // CNPJ
  _PatternDef(
    kind: PiiKind.cnpj,
    regex: RegExp('$_sol(\\d{2}\\.\\d{3}\\.\\d{3}/\\d{4}-\\d{2}|\\d{14})$_eol'),
    validator: validateCnpj,
    confidenceWhenValid: PiiConfidence.high,
    confidenceWhenInvalid: PiiConfidence.mediumLow,
    normalize: _digitsOnly,
  ),
  // PIX UUID (v4)
  _PatternDef(
    kind: PiiKind.pixUuid,
    regex: RegExp(
      '$_sol([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12})$_eol',
    ),
    confidenceWhenValid: PiiConfidence.mediumHigh,
    normalize: (s) => s.toLowerCase(),
  ),
  // CPF
  _PatternDef(
    kind: PiiKind.cpf,
    regex: RegExp('$_sol(\\d{3}\\.\\d{3}\\.\\d{3}-\\d{2}|\\d{11})$_eol'),
    validator: validateCpf,
    confidenceWhenValid: PiiConfidence.high,
    confidenceWhenInvalid: PiiConfidence.veryLow,
    normalize: _digitsOnly,
  ),
  // Cartão BR
  _PatternDef(
    kind: PiiKind.cartaoBr,
    regex: RegExp(
      '$_sol(\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{1,7}|\\d{13,19})$_eol',
    ),
    validator: (n) => luhn(n) && n.length >= 13 && n.length <= 19 && !RegExp(r'^(\d)\1+$').hasMatch(n),
    confidenceWhenValid: PiiConfidence.high,
    confidenceWhenInvalid: PiiConfidence.veryLow,
    normalize: _digitsOnly,
  ),
  // Telefone BR
  _PatternDef(
    kind: PiiKind.telefoneBr,
    regex: RegExp(
      '$_sol(?:\\+?55[\\s-]?)?(?:\\(?[1-9][0-9]\\)?[\\s-]?)?9?\\d{4}[\\s-]?\\d{4}$_eol',
    ),
    validator: (n) {
      final len = n.length;
      if (len < 8 || len > 13) return false;
      if (len == 13 && !n.startsWith('55')) return false;
      if (len == 12 && !n.startsWith('55')) return false;
      if (len == 11 && n[2] != '9') return false;
      return true;
    },
    confidenceWhenValid: PiiConfidence.mediumHigh,
    confidenceWhenInvalid: PiiConfidence.low,
    normalize: _digitsOnly,
  ),
  // PIX phone (+55 obrigatório, formato chave PIX estrito)
  _PatternDef(
    kind: PiiKind.pixPhone,
    regex: RegExp('$_sol(\\+55[1-9][0-9]9\\d{8})$_eol'),
    validator: (n) => RegExp(r'^55[1-9][0-9]9\d{8}$').hasMatch(n),
    confidenceWhenValid: PiiConfidence.high,
    confidenceWhenInvalid: PiiConfidence.mediumLow,
    normalize: _digitsOnly,
  ),
  // PIX email
  _PatternDef(
    kind: PiiKind.pixEmail,
    regex: RegExp('$_sol([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})$_eol'),
    confidenceWhenValid: PiiConfidence.mediumHigh,
    normalize: (s) => s.toLowerCase(),
  ),
  // PIX CPF (CPF puro tratado como chave PIX quando caller pede explicitamente)
  _PatternDef(
    kind: PiiKind.pixCpf,
    regex: RegExp('$_sol(\\d{11})$_eol'),
    validator: validateCpf,
    confidenceWhenValid: PiiConfidence.high,
    confidenceWhenInvalid: PiiConfidence.veryLow,
    normalize: _digitsOnly,
  ),
  // CEP
  _PatternDef(
    kind: PiiKind.cep,
    regex: RegExp('$_sol(\\d{5}-\\d{3})$_eol'),
    validator: validateCep,
    confidenceWhenValid: PiiConfidence.mediumHigh,
    confidenceWhenInvalid: PiiConfidence.veryLow,
    normalize: _digitsOnly,
  ),
  // RG (formato amplo, sem checksum oficial)
  _PatternDef(
    kind: PiiKind.rg,
    regex: RegExp(
      '$_sol(\\d{1,2}\\.\\d{3}\\.\\d{3}-[\\dxX]|\\d{7,9}[\\dxX]?)$_eol',
    ),
    confidenceWhenValid: PiiConfidence.mediumLow,
    normalize: (s) => s.replaceAll(RegExp(r'[.\-]'), '').toUpperCase(),
  ),
  // CNH
  _PatternDef(
    kind: PiiKind.cnh,
    regex: RegExp('$_sol(\\d{11})$_eol'),
    validator: validateCnh,
    confidenceWhenValid: PiiConfidence.medium,
    confidenceWhenInvalid: PiiConfidence.veryLow,
    normalize: _digitsOnly,
  ),
  // Título de Eleitor
  _PatternDef(
    kind: PiiKind.tituloEleitor,
    regex: RegExp('$_sol(\\d{12})$_eol'),
    validator: validateTituloEleitor,
    confidenceWhenValid: PiiConfidence.high,
    confidenceWhenInvalid: PiiConfidence.veryLow,
    normalize: _digitsOnly,
  ),
];

/// Concat de catálogos — US primeiro (porque PEM/AWS são contexto-livres),
/// BR depois (Unicode-safe boundaries).
final List<_PatternDef> _allPatterns = [..._usPatterns, ..._brPatterns];

/// Detecta PII no texto e retorna lista ordenada por position (asc).
///
/// Pattern collision resolution: matches que se sobreponhem são resolvidos
/// pela ordem do catálogo (CNPJ antes de CPF, etc.) — vencedor mantém,
/// perdedores são descartados.
///
/// [minConfidence] filtra matches com confiança abaixo do threshold.
/// [includePixCpf] habilita o kind `pixCpf` além de `cpf` (default false —
/// CPF puro vira `cpf`).
List<PiiMatch> detectPii(
  String text, {
  double minConfidence = 0.5,
  bool includePixCpf = false,
}) {
  if (text.isEmpty) return const [];

  final List<PiiMatch> all = [];

  for (final p in _allPatterns) {
    // Skip pixCpf unless caller wants it (avoid duplicate with cpf).
    if (p.kind == PiiKind.pixCpf && !includePixCpf) continue;

    for (final m in p.regex.allMatches(text)) {
      // Para padrões com lookbehind/lookahead, group(0) é a string match
      // completa (inclui delimiters). Os capture groups (group(1)) contêm
      // o "valor" real. Estratégia: pegar group(1) se existir, senão
      // fallback pra group(0). Calcular position usando o índice do group(1).
      final String raw;
      final int start;
      final int end;
      if (m.groupCount >= 1 && m.group(1) != null) {
        raw = m.group(1)!;
        // Para grupos capturados, precisamos achar o início do group(1)
        // dentro do match. Heurística: procurar substring dentro do match.
        // É robusto pra todos os padrões deste catálogo (cada match tem 1
        // grupo único e único no match).
        final fullStart = m.start;
        final offsetInFull = m.group(0)!.indexOf(raw);
        start = fullStart + (offsetInFull >= 0 ? offsetInFull : 0);
        end = start + raw.length;
      } else {
        raw = m.group(0)!;
        start = m.start;
        end = m.end;
      }

      final normalized = p.normalize(raw);

      double confidence = p.confidenceWhenValid;
      if (p.validator != null) {
        final ok = p.validator!(normalized);
        if (!ok) {
          if (p.confidenceWhenInvalid == null) continue; // descarta
          confidence = p.confidenceWhenInvalid!;
        }
      }

      if (confidence < minConfidence) continue;

      all.add(PiiMatch(
        kind: p.kind,
        raw: raw,
        normalized: normalized,
        position: [start, end],
        confidence: confidence,
      ));
    }
  }

  // Overlap resolution: keep first-occurring (catálogo ordering), drop overlaps.
  all.sort((a, b) {
    final cmp = a.position[0].compareTo(b.position[0]);
    if (cmp != 0) return cmp;
    // Tiebreaker: ordem do catálogo (kind index).
    final ai = PiiKind.values.indexOf(a.kind);
    final bi = PiiKind.values.indexOf(b.kind);
    return ai.compareTo(bi);
  });

  final List<PiiMatch> filtered = [];
  int lastEnd = -1;
  for (final m in all) {
    if (m.position[0] >= lastEnd) {
      filtered.add(m);
      lastEnd = m.position[1];
    }
    // else: overlap com match anterior — descartado.
  }

  return filtered;
}

/// Conveniência: lista todos os kinds atualmente suportados.
List<PiiKind> supportedKinds() => PiiKind.values.toList(growable: false);
