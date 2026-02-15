# HB_SCRIPT_KIND=MIGRATE
# HB_SCRIPT_SCOPE=db
# HB_SCRIPT_SIDE_EFFECTS=DB_WRITE
# HB_SCRIPT_IDEMPOTENT=NO
# HB_SCRIPT_ENTRYPOINT=python scripts/migrate/mig_import_legacy_training.py
# HB_SCRIPT_OUTPUTS=stdout
"""
Script de Importação de Dados Legacy do Módulo Training

**Step 28:** Import CSV Legacy

**Funcionalidades:**
- Importa CSVs legacy (sessions.csv, attendance.csv)
- Valida schema e integridade
- Mapeia teams e athletes
- Regra readonly: sessões >60 dias recebem status 'readonly'
- Importação em transação (rollback on error)
- Gera relatório import_summary.json

**Usage:**
```bash
python import_legacy_training.py --sessions sessions.csv --attendance attendance.csv --org-id <uuid>
```

**CSV Format - sessions.csv:**
```
team_name,title,description,session_type,session_at,location,duration_minutes,focus_attack_pct,focus_defense_pct,focus_physical_pct,focus_technical_pct,focus_tactical_pct,focus_transition_pct,focus_goalkeeper_pct
Juvenil Feminino,Treino Tático,Trabalho de defesa posicional,quadra,2025-11-15T10:00:00,Ginásio A,90,10,40,10,15,20,5,0
```

**CSV Format - attendance.csv:**
```
team_name,session_title,session_at,athlete_name,status,arrival_time,notes
Juvenil Feminino,Treino Tático,2025-11-15T10:00:00,Maria Silva,present,2025-11-15T09:55:00,
```
"""

import argparse
import csv
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID, uuid4

# Adicionar path do backend ao sys.path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_db_context
from app.models.team import Team
from app.models.athlete import Athlete
from app.models.person import Person
from app.models.training_session import TrainingSession
from app.models.attendance import Attendance

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================================================================================
# CONSTANTS
# ================================================================================

READONLY_THRESHOLD_DAYS = 60

VALID_SESSION_TYPES = ['quadra', 'fisico', 'video', 'reuniao']
VALID_ATTENDANCE_STATUSES = ['present', 'absent', 'justified', 'late']

SESSIONS_REQUIRED_FIELDS = [
    'team_name', 'title', 'session_type', 'session_at',
    'duration_minutes', 'focus_attack_pct', 'focus_defense_pct',
    'focus_physical_pct', 'focus_technical_pct', 'focus_tactical_pct',
    'focus_transition_pct', 'focus_goalkeeper_pct'
]

ATTENDANCE_REQUIRED_FIELDS = [
    'team_name', 'session_title', 'session_at', 'athlete_name', 'status'
]

# ================================================================================
# VALIDATION FUNCTIONS
# ================================================================================

def validate_sessions_schema(row: Dict, row_num: int) -> List[str]:
    """Valida schema de uma linha de sessions.csv"""
    errors = []
    
    # Check required fields
    for field in SESSIONS_REQUIRED_FIELDS:
        if field not in row or not row[field].strip():
            errors.append(f"Row {row_num}: Missing required field '{field}'")
    
    if errors:
        return errors
    
    # Validate session_type
    if row['session_type'].lower() not in VALID_SESSION_TYPES:
        errors.append(
            f"Row {row_num}: Invalid session_type '{row['session_type']}'. "
            f"Must be one of: {', '.join(VALID_SESSION_TYPES)}"
        )
    
    # Validate datetime format
    try:
        datetime.fromisoformat(row['session_at'])
    except ValueError:
        errors.append(
            f"Row {row_num}: Invalid session_at format '{row['session_at']}'. "
            "Expected ISO format: YYYY-MM-DDTHH:MM:SS"
        )
    
    # Validate duration_minutes
    try:
        duration = int(row['duration_minutes'])
        if duration <= 0 or duration > 300:
            errors.append(f"Row {row_num}: duration_minutes must be between 1 and 300")
    except ValueError:
        errors.append(f"Row {row_num}: duration_minutes must be an integer")
    
    # Validate focus percentages
    focus_fields = [
        'focus_attack_pct', 'focus_defense_pct', 'focus_physical_pct',
        'focus_technical_pct', 'focus_tactical_pct', 'focus_transition_pct',
        'focus_goalkeeper_pct'
    ]
    
    focus_values = []
    for field in focus_fields:
        try:
            value = int(row[field])
            if value < 0 or value > 100:
                errors.append(f"Row {row_num}: {field} must be between 0 and 100")
            focus_values.append(value)
        except ValueError:
            errors.append(f"Row {row_num}: {field} must be an integer")
    
    # Validate focus sum = 100
    if focus_values and sum(focus_values) != 100:
        errors.append(
            f"Row {row_num}: Sum of focus percentages must equal 100 "
            f"(current sum: {sum(focus_values)})"
        )
    
    return errors


def validate_attendance_schema(row: Dict, row_num: int) -> List[str]:
    """Valida schema de uma linha de attendance.csv"""
    errors = []
    
    # Check required fields
    for field in ATTENDANCE_REQUIRED_FIELDS:
        if field not in row or not row[field].strip():
            errors.append(f"Row {row_num}: Missing required field '{field}'")
    
    if errors:
        return errors
    
    # Validate status
    if row['status'].lower() not in VALID_ATTENDANCE_STATUSES:
        errors.append(
            f"Row {row_num}: Invalid status '{row['status']}'. "
            f"Must be one of: {', '.join(VALID_ATTENDANCE_STATUSES)}"
        )
    
    # Validate session_at format
    try:
        datetime.fromisoformat(row['session_at'])
    except ValueError:
        errors.append(
            f"Row {row_num}: Invalid session_at format '{row['session_at']}'. "
            "Expected ISO format: YYYY-MM-DDTHH:MM:SS"
        )
    
    # Validate arrival_time if present
    if row.get('arrival_time') and row['arrival_time'].strip():
        try:
            datetime.fromisoformat(row['arrival_time'])
        except ValueError:
            errors.append(
                f"Row {row_num}: Invalid arrival_time format '{row['arrival_time']}'. "
                "Expected ISO format: YYYY-MM-DDTHH:MM:SS"
            )
    
    return errors


# ================================================================================
# IMPORT FUNCTIONS
# ================================================================================

async def load_teams_map(db: AsyncSession, org_id: UUID) -> Dict[str, Team]:
    """Carrega mapa de teams por nome"""
    stmt = select(Team).where(
        Team.organization_id == org_id,
        Team.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    teams = result.scalars().all()
    
    teams_map = {team.name: team for team in teams}
    logger.info(f"Loaded {len(teams_map)} teams from organization")
    return teams_map


async def load_athletes_map(db: AsyncSession, org_id: UUID) -> Dict[str, Athlete]:
    """Carrega mapa de athletes por nome (via person)"""
    stmt = select(Athlete).join(Person).join(Team).where(
        Team.organization_id == org_id,
        Athlete.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    athletes = result.scalars().all()
    
    # Mapa por nome completo
    athletes_map = {}
    for athlete in athletes:
        if athlete.person:
            full_name = f"{athlete.person.first_name} {athlete.person.last_name}"
            athletes_map[full_name] = athlete
    
    logger.info(f"Loaded {len(athletes_map)} athletes from organization")
    return athletes_map


async def import_sessions(
    db: AsyncSession,
    csv_path: Path,
    teams_map: Dict[str, Team],
    org_id: UUID
) -> Dict:
    """Importa sessões de treino do CSV"""
    logger.info(f"Reading sessions from {csv_path}")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    logger.info(f"Found {len(rows)} sessions to import")
    
    # Validate all rows first
    validation_errors = []
    for i, row in enumerate(rows, start=2):  # Start at 2 (header = 1)
        errors = validate_sessions_schema(row, i)
        validation_errors.extend(errors)
    
    if validation_errors:
        logger.error(f"Validation failed with {len(validation_errors)} errors")
        return {
            'success': False,
            'errors': validation_errors,
            'sessions_imported': 0
        }
    
    # Import sessions
    now = datetime.now(timezone.utc)
    readonly_cutoff = now - timedelta(days=READONLY_THRESHOLD_DAYS)
    
    sessions_imported = 0
    sessions_readonly = 0
    sessions_skipped = []
    
    for i, row in enumerate(rows, start=2):
        team_name = row['team_name'].strip()
        
        # Check if team exists
        if team_name not in teams_map:
            sessions_skipped.append({
                'row': i,
                'reason': f"Team '{team_name}' not found",
                'title': row['title']
            })
            continue
        
        team = teams_map[team_name]
        session_at = datetime.fromisoformat(row['session_at'])
        
        # Determine status (readonly if >60 days old)
        is_readonly = session_at < readonly_cutoff
        status = 'readonly' if is_readonly else 'draft'
        
        # Create session
        session = TrainingSession(
            id=uuid4(),
            team_id=team.id,
            organization_id=org_id,
            title=row['title'].strip(),
            description=row.get('description', '').strip() or None,
            session_type=row['session_type'].lower(),
            session_at=session_at,
            location=row.get('location', '').strip() or None,
            duration_minutes=int(row['duration_minutes']),
            focus_attack_pct=int(row['focus_attack_pct']),
            focus_defense_pct=int(row['focus_defense_pct']),
            focus_physical_pct=int(row['focus_physical_pct']),
            focus_technical_pct=int(row['focus_technical_pct']),
            focus_tactical_pct=int(row['focus_tactical_pct']),
            focus_transition_pct=int(row['focus_transition_pct']),
            focus_goalkeeper_pct=int(row['focus_goalkeeper_pct']),
            status=status,
            is_imported=True,
            imported_at=now
        )
        
        db.add(session)
        sessions_imported += 1
        
        if is_readonly:
            sessions_readonly += 1
    
    await db.commit()
    
    logger.info(
        f"Imported {sessions_imported} sessions "
        f"({sessions_readonly} readonly, {len(sessions_skipped)} skipped)"
    )
    
    return {
        'success': True,
        'sessions_imported': sessions_imported,
        'sessions_readonly': sessions_readonly,
        'sessions_skipped': sessions_skipped
    }


async def import_attendance(
    db: AsyncSession,
    csv_path: Path,
    teams_map: Dict[str, Team],
    athletes_map: Dict[str, Athlete]
) -> Dict:
    """Importa attendance do CSV"""
    logger.info(f"Reading attendance from {csv_path}")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    logger.info(f"Found {len(rows)} attendance records to import")
    
    # Validate all rows first
    validation_errors = []
    for i, row in enumerate(rows, start=2):
        errors = validate_attendance_schema(row, i)
        validation_errors.extend(errors)
    
    if validation_errors:
        logger.error(f"Validation failed with {len(validation_errors)} errors")
        return {
            'success': False,
            'errors': validation_errors,
            'attendance_imported': 0
        }
    
    # Build sessions map (team_name + title + session_at)
    stmt = select(TrainingSession).where(
        TrainingSession.is_imported == True,
        TrainingSession.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    
    sessions_map = {}
    for session in sessions:
        team = await db.get(Team, session.team_id)
        if team:
            key = f"{team.name}|{session.title}|{session.session_at.isoformat()}"
            sessions_map[key] = session
    
    logger.info(f"Found {len(sessions_map)} imported sessions for attendance mapping")
    
    # Import attendance
    attendance_imported = 0
    attendance_skipped = []
    
    for i, row in enumerate(rows, start=2):
        team_name = row['team_name'].strip()
        session_title = row['session_title'].strip()
        session_at_str = row['session_at'].strip()
        athlete_name = row['athlete_name'].strip()
        
        # Find session
        session_key = f"{team_name}|{session_title}|{session_at_str}"
        if session_key not in sessions_map:
            attendance_skipped.append({
                'row': i,
                'reason': f"Session not found: {team_name} / {session_title} / {session_at_str}",
                'athlete': athlete_name
            })
            continue
        
        # Find athlete
        if athlete_name not in athletes_map:
            attendance_skipped.append({
                'row': i,
                'reason': f"Athlete '{athlete_name}' not found",
                'session': session_title
            })
            continue
        
        session = sessions_map[session_key]
        athlete = athletes_map[athlete_name]
        
        # Create attendance
        arrival_time = None
        if row.get('arrival_time') and row['arrival_time'].strip():
            arrival_time = datetime.fromisoformat(row['arrival_time'])
        
        attendance = Attendance(
            id=uuid4(),
            training_session_id=session.id,
            athlete_id=athlete.id,
            status=row['status'].lower(),
            arrival_time=arrival_time,
            notes=row.get('notes', '').strip() or None
        )
        
        db.add(attendance)
        attendance_imported += 1
    
    await db.commit()
    
    logger.info(
        f"Imported {attendance_imported} attendance records "
        f"({len(attendance_skipped)} skipped)"
    )
    
    return {
        'success': True,
        'attendance_imported': attendance_imported,
        'attendance_skipped': attendance_skipped
    }


# ================================================================================
# MAIN FUNCTION
# ================================================================================

async def main(
    sessions_csv: Path,
    attendance_csv: Optional[Path],
    org_id: UUID,
    output_json: Path
):
    """Main import function"""
    logger.info("=" * 80)
    logger.info("HB Track - Legacy Training Data Import")
    logger.info("=" * 80)
    logger.info(f"Organization ID: {org_id}")
    logger.info(f"Sessions CSV: {sessions_csv}")
    logger.info(f"Attendance CSV: {attendance_csv}")
    logger.info(f"Output JSON: {output_json}")
    logger.info("")
    
    results = {
        'import_started_at': datetime.now(timezone.utc).isoformat(),
        'organization_id': str(org_id),
        'sessions_csv': str(sessions_csv),
        'attendance_csv': str(attendance_csv) if attendance_csv else None,
        'sessions': {},
        'attendance': {},
        'errors': []
    }
    
    try:
        async with get_async_db_context() as db:
            # Load organization data
            logger.info("Loading teams and athletes...")
            teams_map = await load_teams_map(db, org_id)
            athletes_map = await load_athletes_map(db, org_id)
            
            if not teams_map:
                raise ValueError("No teams found in organization")
            
            # Import sessions
            logger.info("\n" + "=" * 80)
            logger.info("IMPORTING SESSIONS")
            logger.info("=" * 80)
            sessions_result = await import_sessions(
                db, sessions_csv, teams_map, org_id
            )
            results['sessions'] = sessions_result
            
            if not sessions_result['success']:
                results['errors'].extend(sessions_result['errors'])
                raise ValueError("Session import failed validation")
            
            # Import attendance (if provided)
            if attendance_csv and attendance_csv.exists():
                logger.info("\n" + "=" * 80)
                logger.info("IMPORTING ATTENDANCE")
                logger.info("=" * 80)
                attendance_result = await import_attendance(
                    db, attendance_csv, teams_map, athletes_map
                )
                results['attendance'] = attendance_result
                
                if not attendance_result['success']:
                    results['errors'].extend(attendance_result['errors'])
            
            results['import_completed_at'] = datetime.now(timezone.utc).isoformat()
            results['success'] = True
            
            logger.info("\n" + "=" * 80)
            logger.info("IMPORT COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            logger.info(f"Sessions imported: {sessions_result.get('sessions_imported', 0)}")
            logger.info(f"Sessions readonly: {sessions_result.get('sessions_readonly', 0)}")
            logger.info(f"Sessions skipped: {len(sessions_result.get('sessions_skipped', []))}")
            if attendance_csv:
                logger.info(f"Attendance imported: {attendance_result.get('attendance_imported', 0)}")
                logger.info(f"Attendance skipped: {len(attendance_result.get('attendance_skipped', []))}")
            
    except Exception as e:
        logger.error(f"Import failed: {str(e)}")
        results['success'] = False
        results['error_message'] = str(e)
        results['import_failed_at'] = datetime.now(timezone.utc).isoformat()
    
    # Write summary JSON
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\nSummary written to: {output_json}")
    
    return results['success']


# ================================================================================
# CLI
# ================================================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Import legacy training data from CSV files'
    )
    parser.add_argument(
        '--sessions',
        type=Path,
        required=True,
        help='Path to sessions.csv'
    )
    parser.add_argument(
        '--attendance',
        type=Path,
        help='Path to attendance.csv (optional)'
    )
    parser.add_argument(
        '--org-id',
        type=UUID,
        required=True,
        help='Organization UUID'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('import_summary.json'),
        help='Output JSON summary file (default: import_summary.json)'
    )
    
    args = parser.parse_args()
    
    # Validate files exist
    if not args.sessions.exists():
        logger.error(f"Sessions CSV not found: {args.sessions}")
        sys.exit(1)
    
    if args.attendance and not args.attendance.exists():
        logger.error(f"Attendance CSV not found: {args.attendance}")
        sys.exit(1)
    
    # Run import
    import asyncio
    success = asyncio.run(main(
        args.sessions,
        args.attendance,
        args.org_id,
        args.output
    ))
    
    sys.exit(0 if success else 1)

