-- ===============================================
-- SEED OFICIAL MÍNIMO - HB TRACK SISTEMA LIMPO
-- ===============================================
-- VERSÃO: V1.2 BANCO LIMPO
-- DATA: 2026-01-10
-- DESCRIÇÃO: Seed mínimo para funcionalidade completa
-- SOURCE: backup-dados-criticos (65 permissões oficiais)
-- ===============================================

-- ============================
-- ROLES (Conforme definição oficial do sistema)
-- ============================
INSERT INTO roles (id, code, name, description) VALUES 
(1, 'dirigente', 'Dirigente', 'R4: Gestor máximo da organização. Gerencia clubes, equipes, temporadas, dirigentes e coordenadores. Não tem hierarquia sobre treinadores técnicos.'),
(2, 'coordenador', 'Coordenador', 'R4: Gestor de equipes específicas. Intermedia dirigente e treinadores. Não tem autoridade sobre aspectos técnicos de treino e jogo.'),
(3, 'treinador', 'Treinador', 'R4: Responsável técnico de equipe(s). Gerencia treinos, jogos, convocações e análises táticas. Não gerencia atletas de outras equipes.'),
(4, 'atleta', 'Atleta', 'R4: Praticante do esporte. Pode ter vínculos com múltiplas equipes simultaneamente (V1.2). Acesso opcional ao sistema para consulta de wellness e estatísticas.');

-- ============================  
-- PERMISSIONS (65 Permissões Oficiais - backup-dados-criticos)
-- ============================
INSERT INTO permissions (id, code, description) VALUES 
(1, 'persons.create', 'Criar pessoas no sistema'),
(2, 'persons.read', 'Visualizar pessoas'),
(3, 'persons.update', 'Atualizar dados de pessoas'),
(4, 'persons.delete', 'Soft delete de pessoas'),
(5, 'athletes.create', 'Cadastrar atletas'),
(6, 'athletes.read', 'Visualizar atletas'),
(7, 'athletes.update', 'Atualizar dados de atletas'),
(8, 'athletes.delete', 'Soft delete de atletas'),
(9, 'athletes.state_change', 'Mudar estado de atleta (ativa/dispensada/arquivada)'),
(10, 'teams.create', 'Criar equipes'),
(11, 'teams.read', 'Visualizar equipes'),
(12, 'teams.update', 'Atualizar equipes'),
(13, 'teams.delete', 'Soft delete de equipes'),
(14, 'organizations.create', 'Criar organizações (clubes)'),
(15, 'organizations.read', 'Visualizar organizações'),
(16, 'organizations.update', 'Atualizar organizações'),
(17, 'organizations.delete', 'Soft delete de organizações'),
(18, 'seasons.create', 'Criar temporadas'),
(19, 'seasons.read', 'Visualizar temporadas'),
(20, 'seasons.update', 'Atualizar temporadas'),
(21, 'seasons.delete', 'Soft delete de temporadas'),
(22, 'seasons.cancel', 'Cancelar temporada (pré-início)'),
(23, 'seasons.interrupt', 'Interromper temporada (força maior)'),
(24, 'training_sessions.create', 'Criar treinos'),
(25, 'training_sessions.read', 'Visualizar treinos'),
(26, 'training_sessions.update', 'Atualizar treinos'),
(27, 'training_sessions.delete', 'Soft delete de treinos'),
(28, 'attendance.create', 'Registrar presença'),
(29, 'attendance.read', 'Visualizar presença'),
(30, 'attendance.update', 'Atualizar presença'),
(31, 'attendance.delete', 'Soft delete de presença'),
(32, 'wellness.read', 'Visualizar wellness de atletas'),
(33, 'wellness.read_own', 'Atleta visualizar próprio wellness'),
(34, 'wellness.create_pre', 'Registrar wellness pré-treino'),
(35, 'wellness.create_post', 'Registrar wellness pós-treino'),
(36, 'matches.create', 'Criar jogos'),
(37, 'matches.read', 'Visualizar jogos'),
(38, 'matches.update', 'Atualizar jogos'),
(39, 'matches.delete', 'Soft delete de jogos'),
(40, 'matches.reopen', 'Reabrir jogo finalizado'),
(41, 'match_events.create', 'Registrar eventos de jogo'),
(42, 'match_events.read', 'Visualizar eventos'),
(43, 'match_events.update', 'Atualizar eventos'),
(44, 'match_roster.create', 'Criar súmula/convocação'),
(45, 'match_roster.read', 'Visualizar súmula'),
(46, 'match_roster.update', 'Atualizar súmula'),
(47, 'users.create', 'Criar usuários'),
(48, 'users.read', 'Visualizar usuários'),
(49, 'users.update', 'Atualizar usuários'),
(50, 'users.delete', 'Soft delete de usuários'),
(51, 'users.lock', 'Bloquear/desbloquear usuários'),
(52, 'org_memberships.create', 'Criar vínculos organizacionais (staff)'),
(53, 'org_memberships.read', 'Visualizar vínculos'),
(54, 'org_memberships.update', 'Atualizar vínculos'),
(55, 'org_memberships.delete', 'Soft delete de vínculos'),
(56, 'team_registrations.create', 'Registrar atleta em equipe'),
(57, 'team_registrations.read', 'Visualizar registros de atletas'),
(58, 'team_registrations.update', 'Atualizar registros'),
(59, 'team_registrations.delete', 'Soft delete de registros'),
(60, 'reports.training', 'Visualizar relatórios de treino'),
(61, 'reports.matches', 'Visualizar relatórios de jogos'),
(62, 'reports.wellness', 'Visualizar relatórios de wellness'),
(63, 'reports.athletes', 'Visualizar relatórios de atletas'),
(64, 'audit_logs.read', 'Visualizar logs de auditoria'),
(65, 'admin.full_access', 'Acesso total ao sistema (Super Admin)');

-- ============================
-- ROLE_PERMISSIONS (RBAC Oficial)
-- NOTA: Superadmin não precisa de role específico (bypass is_superadmin=true)
-- ============================

-- DIRIGENTE: Gestão organizacional completa
INSERT INTO role_permissions (role_id, permission_id) VALUES 
-- Organizations
(1, 14), (1, 15), (1, 16), (1, 17),
-- Seasons  
(1, 18), (1, 19), (1, 20), (1, 21), (1, 22), (1, 23),
-- Users
(1, 47), (1, 48), (1, 49), (1, 50), (1, 51),
-- Persons
(1, 1), (1, 2), (1, 3), (1, 4),
-- Athletes
(1, 5), (1, 6), (1, 7), (1, 8), (1, 9),
-- Teams
(1, 10), (1, 11), (1, 12), (1, 13),
-- Org Memberships
(1, 52), (1, 53), (1, 54), (1, 55),
-- Team Registrations
(1, 56), (1, 57), (1, 58), (1, 59),
-- Reports
(1, 60), (1, 61), (1, 62), (1, 63),
-- Audit
(1, 64);

-- COORDENADOR: Gestão de equipes e atletas
INSERT INTO role_permissions (role_id, permission_id) VALUES 
-- Teams (read/update, não create/delete)
(2, 11), (2, 12),
-- Athletes
(2, 5), (2, 6), (2, 7), (2, 9),
-- Persons
(2, 1), (2, 2), (2, 3),
-- Team Registrations
(2, 56), (2, 57), (2, 58),
-- Training Sessions (read only)
(2, 25),
-- Attendance (read only)
(2, 29),
-- Reports
(2, 60), (2, 61), (2, 62), (2, 63);

-- TREINADOR: Gestão técnica
INSERT INTO role_permissions (role_id, permission_id) VALUES 
-- Training Sessions
(3, 24), (3, 25), (3, 26), (3, 27),
-- Attendance
(3, 28), (3, 29), (3, 30), (3, 31),
-- Wellness
(3, 32), (3, 34), (3, 35),
-- Matches
(3, 36), (3, 37), (3, 38), (3, 40),
-- Match Events
(3, 41), (3, 42), (3, 43),
-- Match Roster
(3, 44), (3, 45), (3, 46),
-- Athletes (read only)
(3, 6),
-- Reports
(3, 60), (3, 61), (3, 62), (3, 63);

-- ATLETA: Acesso limitado (próprios dados)
INSERT INTO role_permissions (role_id, permission_id) VALUES 
-- Wellness próprio
(4, 33),
-- Athletes (read próprios dados)
(4, 6);

-- ============================
-- ORGANIZATION PADRÃO (IDEC)
-- ============================
INSERT INTO organizations (id, name, created_at, updated_at) VALUES 
('00000000-0000-0000-0000-000000000001', 'IDEC', NOW(), NOW());

-- ============================
-- TEAM PADRÃO (para vincular season)
-- ============================
INSERT INTO teams (id, organization_id, name, gender, category_id, created_at, updated_at) VALUES 
('00000000-0000-0000-0000-000000000006', 
 '00000000-0000-0000-0000-000000000001',
 'Equipe Principal',
 'masculino',
 1,  -- categoria_id=1 (Sub-10 ou similar)
 NOW(), 
 NOW());

-- ============================
-- SEASON 2026 (Current - vinculada ao team)
-- ============================
INSERT INTO seasons (id, team_id, name, year, start_date, end_date, created_at, updated_at) VALUES 
('00000000-0000-0000-0000-000000000002', 
 '00000000-0000-0000-0000-000000000006',  -- team_id
 'Temporada 2026', 
 2026,
 '2026-01-01', 
 '2026-12-31',
 NOW(), 
 NOW());

-- ============================
-- SUPERADMIN (Algoritmo Hash Oficial)
-- NOTA: Hash gerado via bcrypt para senha "Admin@123"
-- ============================

-- Pessoa do superadmin
INSERT INTO persons (id, full_name, first_name, last_name, birth_date, created_at, updated_at) VALUES 
('00000000-0000-0000-0000-000000000003', 'Super Administrador', 'Super', 'Administrador', '1990-01-01', NOW(), NOW());

-- Usuário superadmin (is_superadmin=true bypassa roles)
-- ATENÇÃO: Substituir [HASH_A_SER_GERADO] pelo hash real do backend
INSERT INTO users (id, person_id, email, password_hash, is_superadmin, status, created_at, updated_at) VALUES 
('00000000-0000-0000-0000-000000000004',
 '00000000-0000-0000-0000-000000000003',
 'admin@hbtracking.com',
 '$2b$12$loYyOoIZwD/nSCx5MJct2eCKM3cfBJsPRMPpn1TBOeABJjThxS/Ma',  -- Hash bcrypt para Admin@123
 true,
 'ativo',
 NOW(),
 NOW());

-- ============================
-- ORG_MEMBERSHIP (Vínculo Superadmin)
-- ============================
-- Vincular superadmin à organização padrão 
-- NOTA: role_id pode ser qualquer um já que is_superadmin=true bypassa validações
INSERT INTO org_memberships (id, person_id, organization_id, role_id, start_at, created_at, updated_at) VALUES 
('00000000-0000-0000-0000-000000000005',
 '00000000-0000-0000-0000-000000000003',  -- person superadmin
 '00000000-0000-0000-0000-000000000001',  -- organization padrão
 1,  -- role dirigente (irrelevante para superadmin)
 '2026-01-10',
 NOW(),
 NOW());

-- ============================
-- VERIFICAÇÕES FINAIS
-- ============================
SELECT 'SEED APLICADO COM SUCESSO' as status;

-- Contadores esperados
SELECT 'VERIFICAÇÃO COUNTS' as titulo;
SELECT 'roles' as tabela, COUNT(*) as total FROM roles UNION ALL
SELECT 'permissions', COUNT(*) FROM permissions UNION ALL  
SELECT 'role_permissions', COUNT(*) FROM role_permissions UNION ALL
SELECT 'organizations', COUNT(*) FROM organizations UNION ALL
SELECT 'teams', COUNT(*) FROM teams UNION ALL
SELECT 'seasons', COUNT(*) FROM seasons UNION ALL
SELECT 'users', COUNT(*) FROM users UNION ALL
SELECT 'org_memberships', COUNT(*) FROM org_memberships;

-- Verificar superadmin completo
SELECT 'VERIFICAÇÃO SUPERADMIN' as titulo;
SELECT 
  u.email,
  u.is_superadmin,
  u.status,
  p.full_name,
  om.end_at as membership_end_at
FROM users u
JOIN persons p ON p.id = u.person_id  
LEFT JOIN org_memberships om ON om.person_id = u.person_id
WHERE u.is_superadmin = true;