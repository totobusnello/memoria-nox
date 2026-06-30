/// nox_privacy/types.dart — Dart port de privacy-br/types.ts.
///
/// Confidence numérico (não enum) pra permitir comparações finas em
/// scoring downstream.

/// Categorias de PII suportadas — US (A1) + BR (A1.1).
enum PiiKind {
  // ── US (A1) ────────────────────────────────────────────────────────────────
  pemPrivateKey,
  awsAccessKeyId,
  awsSecretKey,
  anthropicKey,
  openaiKey,
  geminiKey,
  githubToken,
  sshPrivateKeyLine,
  jwt,
  genericHighEntropy,
  emailUs,
  phoneUs,
  ssn,
  creditCard,

  // ── BR (A1.1) ──────────────────────────────────────────────────────────────
  cpf,
  cnpj,
  pixEmail,
  pixPhone,
  pixCpf,
  pixUuid,
  cep,
  rg,
  cnh,
  tituloEleitor,
  telefoneBr,
  cartaoBr,
}

/// Match individual produzido pelo detector.
///
/// - [raw]: substring exatamente como apareceu no texto original.
/// - [normalized]: forma canônica (só dígitos, lowercase email, etc.).
/// - [position]: par [start, end] do match (end exclusivo, padrão Dart String slice).
/// - [confidence]: 0.0–1.0.
class PiiMatch {
  PiiMatch({
    required this.kind,
    required this.raw,
    required this.normalized,
    required this.position,
    required this.confidence,
  });

  final PiiKind kind;
  final String raw;
  final String normalized;
  final List<int> position; // [start, end]
  final double confidence;

  @override
  String toString() =>
      'PiiMatch(kind=${kind.name}, raw=$raw, conf=${confidence.toStringAsFixed(2)}, pos=$position)';
}

/// Resultado da redação.
class PiiRedactResult {
  PiiRedactResult({
    required this.redacted,
    required this.redactionCount,
    required this.matches,
  });

  final String redacted;
  final int redactionCount;
  final List<PiiMatch> matches;
}

/// Buckets de confiança canônicos. Espelham privacy-br/types.ts CONFIDENCE.
class PiiConfidence {
  static const double high = 0.95;
  static const double mediumHigh = 0.85;
  static const double medium = 0.75;
  static const double mediumLow = 0.65;
  static const double low = 0.5;
  static const double veryLow = 0.3;
}
