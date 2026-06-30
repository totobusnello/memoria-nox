/// capture/share_listener.dart — escuta share intents do sistema (iOS/Android).
///
/// iOS:    Share Extension delivery via UIActivityViewController.
/// Android: ACTION_SEND / ACTION_SEND_MULTIPLE intent.
///
/// Plugin `share_handler` é o adapter cross-platform. Captura inicial é
/// recebida em `getInitialSharedMedia()` (cold start), e subsequentes em
/// `sharedMediaStream` (warm).
///
/// Política: app NUNCA aceita share de arquivos binários em v1 (audio/video).
/// Apenas texto.

import 'package:share_handler/share_handler.dart';

import 'capture_service.dart';

class ShareListener {
  ShareListener({required this.capture});

  final CaptureService capture;
  final _handler = ShareHandlerPlatform.instance;
  Stream<SharedMedia>? _subscription;

  Future<void> start() async {
    // Initial (cold start).
    final initial = await _handler.getInitialSharedMedia();
    if (initial != null) {
      await _handle(initial);
    }
    // Subsequent (warm).
    _subscription = _handler.sharedMediaStream;
    _subscription?.listen(_handle);
  }

  Future<void> _handle(SharedMedia media) async {
    final text = media.content?.trim();
    if (text == null || text.isEmpty) return;
    await capture.captureFromShare(text, source: 'share-intent');
  }
}
