/// sync/tailscale_manager.dart — Detecta conexão Tailscale + resolve VPS IP.
///
/// State machine:
///
///   OFFLINE ──── tunnel detectado ──── CONNECTING
///      ↑                                  │
///      │                                  ▼
///   disconnect                         ONLINE
///      │                                  │
///      └─────────────────────────── sync trigger
///
/// Estratégia de detecção:
///   1. `connectivity_plus` indica que há rede (qualquer tipo).
///   2. HTTP GET `/api/health` com timeout 3s no IP/URL configurado pelo usuário.
///   3. Se OK em ≤ 3s → ONLINE. Se timeout/erro → OFFLINE.
///   4. Re-check periódico a cada 60s + on-resume da app.
///
/// Tailscale SDK NÃO está integrado no MVP — assume-se que o app Tailscale
/// nativo está rodando e o tunnel está estabelecido. App nox-mem mobile
/// só precisa fazer HTTP para o IP 100.x.y.z da VPS.

import 'dart:async';
import 'dart:io';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:http/http.dart' as http;

enum TailscaleState { offline, connecting, online }

class TailscaleManager {
  TailscaleManager({
    required this.vpsBaseUrl,
    required this.bearerToken,
    Duration probeInterval = const Duration(seconds: 60),
    Duration probeTimeout = const Duration(seconds: 3),
  })  : _probeInterval = probeInterval,
        _probeTimeout = probeTimeout;

  final String vpsBaseUrl; // ex: http://100.x.y.z:18802
  final String bearerToken;
  final Duration _probeInterval;
  final Duration _probeTimeout;

  TailscaleState _state = TailscaleState.offline;
  final _controller = StreamController<TailscaleState>.broadcast();
  Timer? _probeTimer;
  StreamSubscription<List<ConnectivityResult>>? _connSub;

  /// Stream pública pra UI escutar mudanças de estado.
  Stream<TailscaleState> get stateStream => _controller.stream;

  TailscaleState get state => _state;

  Future<void> start() async {
    _connSub = Connectivity().onConnectivityChanged.listen((_) {
      // Mudança de rede → re-probe imediato.
      _probe();
    });
    _probeTimer = Timer.periodic(_probeInterval, (_) => _probe());
    await _probe();
  }

  Future<void> stop() async {
    _probeTimer?.cancel();
    await _connSub?.cancel();
    await _controller.close();
  }

  /// Force re-probe — útil ao retornar do background.
  Future<void> refresh() => _probe();

  Future<void> _probe() async {
    _setState(TailscaleState.connecting);

    try {
      final result = await http
          .get(
            Uri.parse('$vpsBaseUrl/api/health'),
            headers: {
              'Authorization': 'Bearer $bearerToken',
              'Accept': 'application/json',
            },
          )
          .timeout(_probeTimeout);

      if (result.statusCode == 200) {
        _setState(TailscaleState.online);
      } else {
        _setState(TailscaleState.offline);
      }
    } on TimeoutException {
      _setState(TailscaleState.offline);
    } on SocketException {
      _setState(TailscaleState.offline);
    } on http.ClientException {
      _setState(TailscaleState.offline);
    } catch (_) {
      // Defensivo — qualquer erro inesperado vira offline.
      _setState(TailscaleState.offline);
    }
  }

  void _setState(TailscaleState newState) {
    if (newState == _state) return;
    _state = newState;
    if (!_controller.isClosed) _controller.add(newState);
  }
}
