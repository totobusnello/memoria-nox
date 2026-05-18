/// db/migrations.dart — Sistema de migration incremental.
///
/// Cada bump de schemaVersion exige uma função aqui mapeada por
/// from→to. O `openDb()` em [database.dart] checa a versão persistida
/// em `_meta.schema_version` e roda em ordem todas as migrations
/// necessárias até atingir [schemaVersion] atual.

import 'package:sqflite_sqlcipher/sqflite.dart';

/// Mapa de migrations: chave = "fromVersion→toVersion".
///
/// Quando adicionar v2, criar entry "1→2" com SQL DDL necessário.
final Map<String, List<String>> migrations = {
  // Placeholder: futuras migrations entram aqui.
  // Exemplo:
  // '1→2': [
  //   'ALTER TABLE mobile_chunks ADD COLUMN salience REAL DEFAULT 0',
  //   "UPDATE _meta SET value = '2' WHERE key = 'schema_version'",
  // ],
};

/// Executa migrations sequenciais de [currentVersion] até [targetVersion].
///
/// Falha rápido se não houver migration definida para algum passo
/// intermediário — isso evita silent data corruption.
Future<void> runMigrations(
  Database db,
  int currentVersion,
  int targetVersion,
) async {
  for (int v = currentVersion; v < targetVersion; v++) {
    final key = '$v→${v + 1}';
    final steps = migrations[key];
    if (steps == null) {
      throw StateError(
        'Missing migration $key — refusing to silently skip schema gap.',
      );
    }
    await db.transaction((txn) async {
      for (final stmt in steps) {
        await txn.execute(stmt);
      }
    });
  }
}
