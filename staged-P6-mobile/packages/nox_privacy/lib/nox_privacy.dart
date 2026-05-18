/// nox_privacy — Dart port do A1 (US) + A1.1 (BR) PII filter do nox-mem.
///
/// Roda no device antes de qualquer upload. Faz feature parity com o filter
/// TypeScript:
///   - 13 padrões US (PEM, AWS, Anthropic, OpenAI, Gemini, GitHub, SSH,
///     JWT, generic high-entropy, email, phone US, SSN, credit card).
///   - 12 padrões BR (CPF, CNPJ, PIX UUID/email/phone/cpf, CEP, RG, CNH,
///     Título de Eleitor, telefone BR, cartão BR).
///
/// Princípios:
///   - **Sem `\b`** — falha em Unicode (ç/ã/ê). Usar lookbehind/lookahead.
///   - **Check-digit obrigatório** quando aplicável (CPF, CNPJ, CNH, TE, Luhn).
///   - **Confidence numérico** 0.0–1.0 — caller decide threshold.
///   - **Right-to-left replacement** para preservar offsets ao redactar.
library nox_privacy;

export 'src/patterns.dart';
export 'src/redact.dart';
export 'src/types.dart';
