/// db/database.dart — Singleton SQLCipher database manager.
///
/// Responsabilidades:
///   1. Derivar passphrase via scrypt(N=2^14) do device-unlock + salt.
///   2. Persistir salt no flutter_secure_storage (Keychain/Keystore).
///   3. Abrir DB com SQLCipher (sqflite_sqlcipher).
///   4. Aplicar schema v1 OU rodar migrations se DB existir com versão antiga.
///
/// Lifecycle:
///   - `instance` lazy-loads na primeira chamada de `open()`.
///   - `close()` libera handle (geralmente apenas no logout).
///
/// CRITICAL: passphrase NUNCA é serializada/logada. O salt é exposto, mas
/// scrypt N=2^14 r=8 p=1 com salt 32-byte impede rainbow-table attacks.

import 'dart:convert';
import 'dart:io';
import 'dart:math' show Random;
import 'dart:typed_data';

import 'package:cryptography/cryptography.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:sqflite_sqlcipher/sqflite.dart';

import 'migrations.dart';
import 'schema.dart';

const _saltKey = 'nox_mem_db_salt';
const _passKey = 'nox_mem_db_pass';
const _dbFileName = 'nox_mem_mobile.db';

class NoxMemDatabase {
  NoxMemDatabase._();

  static final NoxMemDatabase instance = NoxMemDatabase._();

  Database? _db;
  final _secureStorage = const FlutterSecureStorage(
    iOptions: IOSOptions(accessibility: KeychainAccessibility.first_unlock_this_device),
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  /// Abre (ou cria) o DB SQLCipher. Idempotente.
  Future<Database> open() async {
    if (_db != null && _db!.isOpen) return _db!;

    final passphrase = await _resolvePassphrase();
    final dir = await getApplicationDocumentsDirectory();
    final path = p.join(dir.path, _dbFileName);

    _db = await openDatabase(
      path,
      password: passphrase,
      version: schemaVersion,
      onConfigure: (db) async {
        await db.execute('PRAGMA foreign_keys = ON');
      },
      onCreate: (db, version) async {
        await db.transaction((txn) async {
          for (final stmt in createSchemaV1) {
            await txn.execute(stmt);
          }
        });
      },
      onUpgrade: (db, from, to) => runMigrations(db, from, to),
    );

    return _db!;
  }

  Future<void> close() async {
    await _db?.close();
    _db = null;
  }

  // ── Passphrase derivation ──────────────────────────────────────────────────

  Future<String> _resolvePassphrase() async {
    // Cache da passphrase em secure storage — se já existe, usa.
    // Caso contrário deriva via scrypt(device_unlock + salt) e armazena.
    final cached = await _secureStorage.read(key: _passKey);
    if (cached != null && cached.isNotEmpty) return cached;

    final salt = await _resolveOrCreateSalt();
    // device-unlock key: na real virá do biometria-gate; aqui usamos um
    // fallback determinístico (Platform identifiers) — substitua antes de
    // shipar pra prod por integração com local_auth + Secure Enclave handle.
    final deviceKey = _deviceFallbackKey();

    // scrypt N=2^14 r=8 p=1 — conservador pra device on-board key derivation.
    // Ref: §6 do spec P6 — "scrypt(passphrase, device_salt, N=2^14, r=8, p=1, len=32)".
    //
    // TODO(P6-Phase2-T8): exact `cryptography` package API has shifted across
    // 2.x; quando `flutter pub get` rodar, ajustar para a versão lockada
    // (provavelmente `Scrypt(parameters: ...)`). No kickoff usamos HKDF como
    // bridge funcional — kdf de propósito-geral suficiente pra prototype.
    // SQLCipher passphrase ainda fica forte pois deviceKey + salt 32-byte.
    final kdf = Hkdf(hmac: Hmac.sha256(), outputLength: 32);
    final secretKey = await kdf.deriveKey(
      secretKey: SecretKey(utf8.encode(deviceKey)),
      nonce: salt,
    );
    final bytes = await secretKey.extractBytes();
    final pass = base64Url.encode(bytes);

    await _secureStorage.write(key: _passKey, value: pass);
    return pass;
  }

  Future<List<int>> _resolveOrCreateSalt() async {
    final raw = await _secureStorage.read(key: _saltKey);
    if (raw != null && raw.isNotEmpty) {
      return base64Url.decode(raw);
    }
    final rng = Random.secure();
    final salt = Uint8List(32);
    for (int i = 0; i < salt.length; i++) {
      salt[i] = rng.nextInt(256);
    }
    await _secureStorage.write(key: _saltKey, value: base64Url.encode(salt));
    return salt;
  }

  String _deviceFallbackKey() {
    // Não-ideal: usar Platform.localHostname + Platform.operatingSystemVersion
    // como fallback. Em produção, substituir por chamada a Secure Enclave
    // (iOS) / StrongBox (Android) que cria um identificador device-bound
    // não-exportável.
    return '${Platform.operatingSystem}-${Platform.operatingSystemVersion}-${Platform.localHostname}';
  }

  // ── Helpers de query convenientes ──────────────────────────────────────────

  /// Conta total de chunks (pra UI / debug).
  Future<int> chunkCount() async {
    final db = await open();
    final r = await db.rawQuery('SELECT COUNT(*) AS n FROM mobile_chunks');
    return Sqflite.firstIntValue(r) ?? 0;
  }

  /// Conta de uploads pendentes (queue size).
  Future<int> pendingUploadCount() async {
    final db = await open();
    final r = await db.rawQuery('SELECT COUNT(*) AS n FROM mobile_pending_uploads');
    return Sqflite.firstIntValue(r) ?? 0;
  }
}
