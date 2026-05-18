/// sync_smoke_test.dart — Phase 1 integration test stubs.
///
/// Estes tests só valida estrutura/contract — execução real requer rede +
/// Tailscale + VPS mock. Implementação completa fica em Phase 3.

import 'package:flutter_test/flutter_test.dart';
import 'package:nox_mem_mobile/sync/tailscale_manager.dart';

void main() {
  group('TailscaleManager — instantiation contract', () {
    test('builds with required params', () {
      final mgr = TailscaleManager(
        vpsBaseUrl: 'http://100.0.0.1:18802',
        bearerToken: 'fake-token-for-test',
      );
      expect(mgr.state, equals(TailscaleState.offline));
    });

    test('exposes state stream', () async {
      final mgr = TailscaleManager(
        vpsBaseUrl: 'http://100.0.0.1:18802',
        bearerToken: 'fake-token-for-test',
      );
      expect(mgr.stateStream, isNotNull);
    });

    test('refresh method exists', () {
      final mgr = TailscaleManager(
        vpsBaseUrl: 'http://invalid-test-url-never-resolves.local',
        bearerToken: 'fake-token-for-test',
        probeTimeout: const Duration(milliseconds: 100),
      );
      // Não roda — refresh() chama HTTP que não temos mock. Apenas
      // valida que o método existe. Phase 3 vai usar mocktail.
      expect(mgr.refresh, isA<Function>());
    });
  });

  group('TailscaleState enum', () {
    test('has three states', () {
      expect(TailscaleState.values.length, equals(3));
      expect(TailscaleState.values, contains(TailscaleState.offline));
      expect(TailscaleState.values, contains(TailscaleState.connecting));
      expect(TailscaleState.values, contains(TailscaleState.online));
    });
  });

  group('Phase 3 stubs', () {
    test('sync engine integration TODO marker', () {
      // Phase 3 vai adicionar:
      //   - SyncEngine.uploadPending() com mock HTTP server
      //   - SyncEngine.downloadDelta() com archive A2 sintético
      //   - SyncEngine.resolveConflicts() com fixtures L1/L2/L3
      // Por ora, marker para garantir que ninguém esqueça.
      expect(true, isTrue, reason: 'See SYNC-PROTOCOL.md §10');
    });
  });
}
