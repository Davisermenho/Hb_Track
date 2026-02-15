# HB_SCRIPT_KIND=MIGRATE
# HB_SCRIPT_SCOPE=db
# HB_SCRIPT_SIDE_EFFECTS=DB_WRITE
# HB_SCRIPT_IDEMPOTENT=NO
# HB_SCRIPT_ENTRYPOINT=python scripts/migrate/mig_backfill_training_season_team.py
# HB_SCRIPT_OUTPUTS=stdout
#!/usr/bin/env python3
"""
Backfill script para popular season_id e team_id em training_sessions.

FASE 1: Executado após migration 5c90cfd7e291 (adiciona colunas NULL).

Estratégia de Backfill:
1. season_id: Obtido de membership.season_id via created_by_membership_id
2. team_id: Obtido de team_registrations (equipe ativa do criador na data do treino)

Referências RAG: R8 (temporada), R39 (equipe), RDB5 (audit logs)

Uso:
    python backend/db/scripts/backfill_training_sessions_season_team.py --database-url <URL> [--batch-size 1000] [--dry-run]
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

# Adiciona o diretório raiz ao path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


def backfill_season_id(
    conn: psycopg2.extensions.connection,
    batch_size: int = 1000,
    dry_run: bool = False
) -> int:
    """
    Backfill de season_id via membership.season_id.

    Lógica:
    - training_sessions.created_by_membership_id -> membership.id
    - membership.season_id -> training_sessions.season_id
    """
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Conta quantos registros precisam de backfill
    cursor.execute("""
        SELECT COUNT(*)
        FROM training_sessions ts
        WHERE ts.season_id IS NULL
          AND ts.deleted_at IS NULL
    """)
    total_count = cursor.fetchone()['count']

    if total_count == 0:
        print("✅ Nenhum registro precisa de backfill de season_id.")
        return 0

    print(f"🔍 Encontrados {total_count} registros sem season_id.")

    if dry_run:
        print("🔍 [DRY RUN] Mostrando sample de registros que seriam atualizados:")
        cursor.execute("""
            SELECT
                ts.id AS session_id,
                ts.session_at,
                ts.created_by_membership_id,
                m.season_id AS season_from_membership,
                s.name AS season_name
            FROM training_sessions ts
            INNER JOIN membership m ON m.id = ts.created_by_membership_id
            LEFT JOIN seasons s ON s.id = m.season_id
            WHERE ts.season_id IS NULL
              AND ts.deleted_at IS NULL
            LIMIT 5
        """)
        for row in cursor.fetchall():
            print(f"  - Session {row['session_id'][:8]}... ({row['session_at']}) -> Season: {row['season_name']}")
        print(f"🔍 [DRY RUN] Total: {total_count} registros seriam atualizados.")
        return total_count

    # Executa backfill em lotes (evita picos de lock/IO)
    print(f"🚀 Iniciando backfill de season_id em lotes de {batch_size}...")

    updated_count = 0
    offset = 0

    while True:
        # Atualiza lote
        cursor.execute("""
            UPDATE training_sessions ts
            SET season_id = m.season_id
            FROM membership m
            WHERE ts.created_by_membership_id = m.id
              AND ts.season_id IS NULL
              AND ts.deleted_at IS NULL
              AND ts.id IN (
                  SELECT id
                  FROM training_sessions
                  WHERE season_id IS NULL
                    AND deleted_at IS NULL
                  ORDER BY session_at DESC
                  LIMIT %s OFFSET %s
              )
        """, (batch_size, offset))

        batch_updated = cursor.rowcount
        updated_count += batch_updated

        conn.commit()

        print(f"  ✅ Lote {offset // batch_size + 1}: {batch_updated} registros atualizados ({updated_count}/{total_count})")

        if batch_updated == 0:
            break

        offset += batch_size

    print(f"✅ Backfill de season_id concluído: {updated_count} registros atualizados.")
    return updated_count


def backfill_team_id(
    conn: psycopg2.extensions.connection,
    batch_size: int = 1000,
    dry_run: bool = False
) -> int:
    """
    Backfill de team_id via team_registrations.

    Lógica:
    - Busca a equipe ativa do criador (via membership -> athlete_id) na data do treino
    - Se múltiplas equipes, pega a mais recente
    - Se nenhuma equipe, deixa NULL
    """
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Conta quantos registros precisam de backfill
    cursor.execute("""
        SELECT COUNT(*)
        FROM training_sessions ts
        WHERE ts.team_id IS NULL
          AND ts.deleted_at IS NULL
    """)
    total_count = cursor.fetchone()['count']

    if total_count == 0:
        print("✅ Nenhum registro precisa de backfill de team_id.")
        return 0

    print(f"🔍 Encontrados {total_count} registros sem team_id.")

    if dry_run:
        print("🔍 [DRY RUN] Mostrando sample de registros que seriam atualizados:")
        cursor.execute("""
            WITH session_teams AS (
                SELECT DISTINCT ON (ts.id)
                    ts.id AS session_id,
                    ts.session_at,
                    tr.team_id,
                    t.name AS team_name
                FROM training_sessions ts
                INNER JOIN membership m ON m.id = ts.created_by_membership_id
                LEFT JOIN team_registrations tr ON tr.athlete_id = m.athlete_id
                    AND tr.deleted_at IS NULL
                    AND tr.start_at <= ts.session_at
                    AND (tr.end_at IS NULL OR tr.end_at >= ts.session_at)
                LEFT JOIN teams t ON t.id = tr.team_id
                WHERE ts.team_id IS NULL
                  AND ts.deleted_at IS NULL
                ORDER BY ts.id, tr.start_at DESC
            )
            SELECT * FROM session_teams LIMIT 5
        """)
        for row in cursor.fetchall():
            team_info = f"{row['team_name']}" if row['team_name'] else "NULL (sem equipe)"
            print(f"  - Session {row['session_id'][:8]}... ({row['session_at']}) -> Team: {team_info}")
        print(f"🔍 [DRY RUN] Total: {total_count} registros seriam processados.")
        return total_count

    # Executa backfill em lotes
    print(f"🚀 Iniciando backfill de team_id em lotes de {batch_size}...")

    updated_count = 0
    offset = 0

    while True:
        # Atualiza lote
        cursor.execute("""
            WITH sessions_to_update AS (
                SELECT id
                FROM training_sessions
                WHERE team_id IS NULL
                  AND deleted_at IS NULL
                ORDER BY session_at DESC
                LIMIT %s OFFSET %s
            ),
            session_team_mapping AS (
                SELECT DISTINCT ON (ts.id)
                    ts.id AS session_id,
                    tr.team_id
                FROM training_sessions ts
                INNER JOIN sessions_to_update stu ON stu.id = ts.id
                INNER JOIN membership m ON m.id = ts.created_by_membership_id
                LEFT JOIN team_registrations tr ON tr.athlete_id = m.athlete_id
                    AND tr.deleted_at IS NULL
                    AND tr.start_at <= ts.session_at
                    AND (tr.end_at IS NULL OR tr.end_at >= ts.session_at)
                ORDER BY ts.id, tr.start_at DESC
            )
            UPDATE training_sessions ts
            SET team_id = stm.team_id
            FROM session_team_mapping stm
            WHERE ts.id = stm.session_id
              AND stm.team_id IS NOT NULL
        """, (batch_size, offset))

        batch_updated = cursor.rowcount
        updated_count += batch_updated

        conn.commit()

        print(f"  ✅ Lote {offset // batch_size + 1}: {batch_updated} registros atualizados ({updated_count}/{total_count})")

        if batch_updated == 0:
            break

        offset += batch_size

    print(f"✅ Backfill de team_id concluído: {updated_count} registros atualizados.")

    # Relata quantos ficaram NULL
    cursor.execute("""
        SELECT COUNT(*)
        FROM training_sessions
        WHERE team_id IS NULL
          AND deleted_at IS NULL
    """)
    remaining_nulls = cursor.fetchone()['count']
    if remaining_nulls > 0:
        print(f"⚠️  {remaining_nulls} registros permaneceram com team_id NULL (sem equipe ativa encontrada).")

    return updated_count


def main():
    parser = argparse.ArgumentParser(
        description="Backfill season_id e team_id em training_sessions"
    )
    parser.add_argument(
        "--database-url",
        type=str,
        required=True,
        help="URL de conexão PostgreSQL (postgresql://user:pass@host/db)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Tamanho do lote para backfill (default: 1000)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula execução sem modificar dados"
    )
    parser.add_argument(
        "--only-season",
        action="store_true",
        help="Executa apenas backfill de season_id"
    )
    parser.add_argument(
        "--only-team",
        action="store_true",
        help="Executa apenas backfill de team_id"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("🔧 BACKFILL: training_sessions.season_id e team_id")
    print("=" * 80)
    print(f"Database: {args.database_url.split('@')[1] if '@' in args.database_url else 'N/A'}")
    print(f"Batch Size: {args.batch_size}")
    print(f"Dry Run: {'SIM' if args.dry_run else 'NÃO'}")
    print("=" * 80)

    # Conecta ao banco
    try:
        conn = psycopg2.connect(args.database_url)
        print("✅ Conexão estabelecida.")
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        sys.exit(1)

    try:
        # Backfill season_id
        if not args.only_team:
            print("\n" + "=" * 80)
            print("1️⃣  BACKFILL: season_id")
            print("=" * 80)
            season_updated = backfill_season_id(conn, args.batch_size, args.dry_run)

        # Backfill team_id
        if not args.only_season:
            print("\n" + "=" * 80)
            print("2️⃣  BACKFILL: team_id")
            print("=" * 80)
            team_updated = backfill_team_id(conn, args.batch_size, args.dry_run)

        print("\n" + "=" * 80)
        print("✅ BACKFILL CONCLUÍDO")
        print("=" * 80)

        if args.dry_run:
            print("🔍 [DRY RUN] Nenhum dado foi modificado.")
        else:
            if not args.only_team:
                print(f"  - season_id: {season_updated} registros atualizados")
            if not args.only_season:
                print(f"  - team_id: {team_updated} registros atualizados")

    except Exception as e:
        print(f"\n❌ Erro durante backfill: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()
        print("\n🔌 Conexão fechada.")


if __name__ == "__main__":
    main()

