/// capture/capture_service.dart — entrypoint de captura mobile.
///
/// Fluxo:
///   1. Texto cru entra via [captureText] (paste manual, share intent, OCR).
///   2. Roda PII filter (nox_privacy) com `minConfidence=0.7` (conservador).
///   3. Insere em `mobile_chunks` com `sync_status='pending'` se app está offline,
///      ou tenta upload direto se ONLINE (via TailscaleManager).
///   4. Enfileira em `mobile_pending_uploads` quando offline.
///
/// IMPORTANTE: nunca persiste texto pré-filtro. PII filter é aplicado ANTES
/// da inserção no DB local. Princípio: "se vazar, vaza só REDACTED".

import 'dart:convert';

import 'package:nox_privacy/nox_privacy.dart';
import 'package:sqflite_sqlcipher/sqflite.dart';
import 'package:uuid/uuid.dart';

import '../db/database.dart';
import '../sync/tailscale_manager.dart';

class CaptureService {
  CaptureService({
    required this.db,
    required this.tailscale,
  });

  final NoxMemDatabase db;
  final TailscaleManager tailscale;
  static const _uuid = Uuid();

  /// Captura texto e persiste localmente após PII filter.
  ///
  /// Retorna o `local_id` (UUID) do chunk capturado. O ID canônico
  /// VPS-side só é atribuído após sync bem-sucedido.
  Future<String> captureText({
    required String text,
    String type = 'lesson',
    double pain = 0.2,
    Map<String, dynamic>? metadata,
  }) async {
    if (text.trim().isEmpty) {
      throw ArgumentError('Cannot capture empty text.');
    }

    // ── Layer 1: PII filter ───────────────────────────────────────────────
    final result = redactAll(text, minConfidence: 0.7);
    final cleanText = result.redacted;

    // ── Layer 2: Persist locally ──────────────────────────────────────────
    final database = await db.open();
    final localId = _uuid.v4();
    int chunkId = -1;

    await database.transaction((txn) async {
      chunkId = await txn.insert('mobile_chunks', {
        'text': cleanText,
        'type': type,
        'pain': pain,
        'sync_status': 'pending',
        'base_text': null,
      });

      await txn.insert('mobile_pending_uploads', {
        'local_id': localId,
        'chunk_id': chunkId,
      });
    });

    // ── Layer 3: Best-effort immediate upload se online ───────────────────
    // (Stub no kickoff — implementação completa em Phase 3.)
    if (tailscale.state == TailscaleState.online) {
      // TODO(P6-Phase3): dispatch SyncEngine.uploadPending() não-bloqueante.
    }

    // Surface metadata como log line pra telemetria local.
    if (metadata != null && metadata.isNotEmpty) {
      // Não persistimos metadata em v1 (schema simplificado).
      // ignore: avoid_print
      // print é proibido por lint; canal de telemetria fica em SyncLog.
    }

    return localId;
  }

  /// Captura via share intent — sanitiza tipo/pain antes de delegar.
  Future<String> captureFromShare(String text, {String? source}) {
    return captureText(
      text: text,
      type: 'shared',
      pain: 0.3,
      metadata: source != null ? {'source': source} : null,
    );
  }

  /// Captura de OCR — quando texto vem de câmera/imagem.
  Future<String> captureFromOcr(String text, {required double confidence}) {
    // Pain dinâmico baseado em confidence do OCR (low conf → menor pain).
    final pain = (0.1 + confidence * 0.3).clamp(0.1, 0.5);
    return captureText(text: text, type: 'ocr', pain: pain);
  }
}

/// Helper isolado para serializar payload de upload pendente.
///
/// Usado por SyncEngine na Phase 3. Documentado aqui pra contract clarity.
Map<String, dynamic> pendingChunkToPayload({
  required String localId,
  required Map<String, dynamic> chunkRow,
}) {
  return {
    'local_id': localId,
    'text': chunkRow['text'],
    'type': chunkRow['type'],
    'created_at': chunkRow['created_at'],
    'pain': chunkRow['pain'],
  };
}

/// Serialização defensiva — garante JSON bem formado.
String encodeUploadBody(List<Map<String, dynamic>> payloads) {
  return jsonEncode({
    'chunks': payloads,
  });
}
