/// nox_privacy/redact.dart — Dart port de privacy-br/redact.ts.
///
/// Substitui matches detectados por marcadores `[REDACTED:<kind>]`.
///
/// Modos:
///   - default   : `[REDACTED:cpf]` (curto)
///   - preserve  : pad com underscores pra manter offsets
///   - hash      : `[REDACTED:cpf:abc123]` (FNV-1a hash dos últimos 6 chars do
///                  normalizado) — útil pra dedup downstream sem reidentificar
///
/// Right-to-left replacement é load-bearing — bug clássico de "regex offset
/// drift" se processarmos ASC.

import 'patterns.dart';
import 'types.dart';

/// Modo de substituição.
enum RedactMode { defaultMarker, preserveOffsets, hashSuffix }

/// Hash curto estável — FNV-1a 32-bit em hex (6 chars). NÃO criptográfico.
String _shortHash(String s) {
  int h = 0x811c9dc5;
  for (int i = 0; i < s.length; i++) {
    h ^= s.codeUnitAt(i);
    h = (h * 0x01000193) & 0xFFFFFFFF;
  }
  return h.toRadixString(16).padLeft(8, '0').substring(0, 6);
}

String _kindName(PiiKind k) {
  // snake_case spelling pra parity com TS tags.
  switch (k) {
    case PiiKind.pemPrivateKey:
      return 'pem-private-key';
    case PiiKind.awsAccessKeyId:
      return 'aws-access-key-id';
    case PiiKind.awsSecretKey:
      return 'aws-secret-key';
    case PiiKind.anthropicKey:
      return 'anthropic-key';
    case PiiKind.openaiKey:
      return 'openai-key';
    case PiiKind.geminiKey:
      return 'gemini-key';
    case PiiKind.githubToken:
      return 'github-token';
    case PiiKind.sshPrivateKeyLine:
      return 'ssh-private-key';
    case PiiKind.jwt:
      return 'jwt';
    case PiiKind.genericHighEntropy:
      return 'generic-secret';
    case PiiKind.emailUs:
      return 'email';
    case PiiKind.phoneUs:
      return 'phone-us';
    case PiiKind.ssn:
      return 'ssn';
    case PiiKind.creditCard:
      return 'credit-card';
    case PiiKind.cpf:
      return 'cpf';
    case PiiKind.cnpj:
      return 'cnpj';
    case PiiKind.pixEmail:
      return 'pix_email';
    case PiiKind.pixPhone:
      return 'pix_phone';
    case PiiKind.pixCpf:
      return 'pix_cpf';
    case PiiKind.pixUuid:
      return 'pix_uuid';
    case PiiKind.cep:
      return 'cep';
    case PiiKind.rg:
      return 'rg';
    case PiiKind.cnh:
      return 'cnh';
    case PiiKind.tituloEleitor:
      return 'titulo_eleitor';
    case PiiKind.telefoneBr:
      return 'telefone_br';
    case PiiKind.cartaoBr:
      return 'cartao_br';
  }
}

String _renderMarker(
  PiiMatch m,
  RedactMode mode, {
  String Function(PiiKind kind)? formatMarker,
}) {
  if (formatMarker != null) return formatMarker(m.kind);

  final tag = '[REDACTED:${_kindName(m.kind)}]';

  switch (mode) {
    case RedactMode.preserveOffsets:
      final origLen = m.position[1] - m.position[0];
      if (tag.length == origLen) return tag;
      if (tag.length < origLen) {
        return tag + ('_' * (origLen - tag.length));
      }
      return tag; // tag maior — drift aceito
    case RedactMode.hashSuffix:
      final h = _shortHash(m.normalized);
      return '[REDACTED:${_kindName(m.kind)}:$h]';
    case RedactMode.defaultMarker:
      return tag;
  }
}

/// Redacta toda PII encontrada no texto e retorna o resultado completo.
///
/// Ordem de operações:
///   1. detectPii() encontra matches non-overlapping.
///   2. Sort matches DESC por position[0] (right-to-left).
///   3. Substring replace, posições restantes não shiftam.
///
/// [mode] controla o marker shape.
/// [minConfidence] filtra matches com baixa confiança (default 0.5).
/// [includePixCpf] habilita kind `pixCpf` (default false).
PiiRedactResult redactAll(
  String text, {
  RedactMode mode = RedactMode.defaultMarker,
  double minConfidence = 0.5,
  bool includePixCpf = false,
  String Function(PiiKind kind)? formatMarker,
}) {
  if (text.isEmpty) {
    return PiiRedactResult(redacted: text, redactionCount: 0, matches: const []);
  }

  final matches = detectPii(
    text,
    minConfidence: minConfidence,
    includePixCpf: includePixCpf,
  );

  if (matches.isEmpty) {
    return PiiRedactResult(redacted: text, redactionCount: 0, matches: const []);
  }

  // Right-to-left — clone matches sorted DESC por position[0].
  final sorted = [...matches]..sort((a, b) => b.position[0].compareTo(a.position[0]));

  String redacted = text;
  for (final m in sorted) {
    final marker = _renderMarker(m, mode, formatMarker: formatMarker);
    final start = m.position[0];
    final end = m.position[1];
    redacted = redacted.substring(0, start) + marker + redacted.substring(end);
  }

  return PiiRedactResult(
    redacted: redacted,
    redactionCount: matches.length,
    matches: matches,
  );
}

/// Helper de telemetria — agregação por kind + avg confidence.
Map<String, dynamic> summarizeMatches(List<PiiMatch> matches) {
  final byKind = <String, int>{};
  double totalConf = 0;
  int lowCount = 0;
  for (final m in matches) {
    final k = _kindName(m.kind);
    byKind[k] = (byKind[k] ?? 0) + 1;
    totalConf += m.confidence;
    if (m.confidence < 0.6) lowCount++;
  }
  return {
    'total': matches.length,
    'byKind': byKind,
    'avgConfidence': matches.isNotEmpty ? totalConf / matches.length : 0.0,
    'lowConfidenceCount': lowCount,
  };
}
