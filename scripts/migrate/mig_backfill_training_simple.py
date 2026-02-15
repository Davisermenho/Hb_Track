# HB_SCRIPT_KIND=MIGRATE
# HB_SCRIPT_SCOPE=db
# HB_SCRIPT_SIDE_EFFECTS=DB_WRITE
# HB_SCRIPT_IDEMPOTENT=NO
# HB_SCRIPT_ENTRYPOINT=python scripts/migrate/mig_backfill_training_simple.py
# HB_SCRIPT_OUTPUTS=stdout
#!/usr/bin/env python3
"""
Simple backfill script for season_id and team_id in training_sessions.
No emojis, compatible with Windows console.
"""

import argparse
import sys
import psycopg2
from psycopg2.extras import RealDictCursor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("=" * 80)
    print("BACKFILL: training_sessions.season_id e team_id")
    print("=" * 80)
    print(f"Dry Run: {'YES' if args.dry_run else 'NO'}")
    print("=" * 80)

    conn = psycopg2.connect(args.database_url)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Backfill season_id
    print("\n1. BACKFILL season_id via membership.season_id")
    print("-" * 80)

    cursor.execute("""
        SELECT COUNT(*)
        FROM training_sessions ts
        WHERE ts.season_id IS NULL
          AND ts.deleted_at IS NULL
    """)
    total = cursor.fetchone()['count']
    print(f"Found {total} records without season_id")

    if total > 0 and not args.dry_run:
        cursor.execute("""
            UPDATE training_sessions ts
            SET season_id = m.season_id
            FROM membership m
            WHERE ts.created_by_membership_id = m.id
              AND ts.season_id IS NULL
              AND ts.deleted_at IS NULL
        """)
        conn.commit()
        print(f"Updated {cursor.rowcount} records")
    elif total > 0:
        print("[DRY RUN] Would update records")

    # Backfill team_id
    print("\n2. BACKFILL team_id via team_registrations")
    print("-" * 80)

    cursor.execute("""
        SELECT COUNT(*)
        FROM training_sessions ts
        WHERE ts.team_id IS NULL
          AND ts.deleted_at IS NULL
    """)
    total = cursor.fetchone()['count']
    print(f"Found {total} records without team_id")

    if total > 0 and not args.dry_run:
        cursor.execute("""
            WITH session_team_mapping AS (
                SELECT DISTINCT ON (ts.id)
                    ts.id AS session_id,
                    tr.team_id
                FROM training_sessions ts
                INNER JOIN membership m ON m.id = ts.created_by_membership_id
                LEFT JOIN team_registrations tr ON tr.athlete_id = m.athlete_id
                    AND tr.deleted_at IS NULL
                    AND tr.start_at <= ts.session_at
                    AND (tr.end_at IS NULL OR tr.end_at >= ts.session_at)
                WHERE ts.team_id IS NULL
                  AND ts.deleted_at IS NULL
                ORDER BY ts.id, tr.start_at DESC
            )
            UPDATE training_sessions ts
            SET team_id = stm.team_id
            FROM session_team_mapping stm
            WHERE ts.id = stm.session_id
              AND stm.team_id IS NOT NULL
        """)
        conn.commit()
        print(f"Updated {cursor.rowcount} records")
    elif total > 0:
        print("[DRY RUN] Would update records")

    print("\n" + "=" * 80)
    print("BACKFILL COMPLETE")
    print("=" * 80)

    conn.close()


if __name__ == "__main__":
    main()

