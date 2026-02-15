-- ===============================================
-- SEED USUARIOS DE TESTE - TODOS OS ROLES
-- ===============================================
-- Para testes E2E com diferentes perfis de acesso
-- Senha padrão: Admin@123 (hash bcrypt abaixo)
-- ===============================================

-- Hash bcrypt para "Admin@123"
-- $2b$12$loYyOoIZwD/nSCx5MJct2eCKM3cfBJsPRMPpn1TBOeABJjThxS/Ma

-- ============================
-- DIRIGENTE (role_id=1)
-- ============================
INSERT INTO persons (id, full_name, first_name, last_name, birth_date, created_at, updated_at) 
VALUES ('10000000-0000-0000-0000-000000000001', 'Dirigente Teste', 'Dirigente', 'Teste', '1980-01-01', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

INSERT INTO users (id, person_id, email, password_hash, is_superadmin, status, created_at, updated_at) 
VALUES (
  '20000000-0000-0000-0000-000000000001',
  '10000000-0000-0000-0000-000000000001',
  'dirigente@teste.com',
  '$2b$12$loYyOoIZwD/nSCx5MJct2eCKM3cfBJsPRMPpn1TBOeABJjThxS/Ma',
  false,
  'ativo',
  NOW(),
  NOW()
) ON CONFLICT (id) DO NOTHING;

INSERT INTO org_memberships (id, person_id, organization_id, role_id, start_at, created_at, updated_at) 
VALUES (
  '30000000-0000-0000-0000-000000000001',
  '10000000-0000-0000-0000-000000000001',
  '00000000-0000-0000-0000-000000000001',  -- IDEC
  1,  -- dirigente
  '2026-01-01',
  NOW(),
  NOW()
) ON CONFLICT (id) DO NOTHING;

-- ============================
-- COORDENADOR (role_id=2)
-- ============================
INSERT INTO persons (id, full_name, first_name, last_name, birth_date, created_at, updated_at) 
VALUES ('10000000-0000-0000-0000-000000000002', 'Coordenador Teste', 'Coordenador', 'Teste', '1985-05-15', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

INSERT INTO users (id, person_id, email, password_hash, is_superadmin, status, created_at, updated_at) 
VALUES (
  '20000000-0000-0000-0000-000000000002',
  '10000000-0000-0000-0000-000000000002',
  'coordenador@teste.com',
  '$2b$12$loYyOoIZwD/nSCx5MJct2eCKM3cfBJsPRMPpn1TBOeABJjThxS/Ma',
  false,
  'ativo',
  NOW(),
  NOW()
) ON CONFLICT (id) DO NOTHING;

INSERT INTO org_memberships (id, person_id, organization_id, role_id, start_at, created_at, updated_at) 
VALUES (
  '30000000-0000-0000-0000-000000000002',
  '10000000-0000-0000-0000-000000000002',
  '00000000-0000-0000-0000-000000000001',  -- IDEC
  2,  -- coordenador
  '2026-01-01',
  NOW(),
  NOW()
) ON CONFLICT (id) DO NOTHING;

-- ============================
-- TREINADOR (role_id=3)
-- ============================
INSERT INTO persons (id, full_name, first_name, last_name, birth_date, created_at, updated_at) 
VALUES ('10000000-0000-0000-0000-000000000003', 'Treinador Teste', 'Treinador', 'Teste', '1982-08-20', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

INSERT INTO users (id, person_id, email, password_hash, is_superadmin, status, created_at, updated_at) 
VALUES (
  '20000000-0000-0000-0000-000000000003',
  '10000000-0000-0000-0000-000000000003',
  'treinador@teste.com',
  '$2b$12$loYyOoIZwD/nSCx5MJct2eCKM3cfBJsPRMPpn1TBOeABJjThxS/Ma',
  false,
  'ativo',
  NOW(),
  NOW()
) ON CONFLICT (id) DO NOTHING;

INSERT INTO org_memberships (id, person_id, organization_id, role_id, start_at, created_at, updated_at) 
VALUES (
  '30000000-0000-0000-0000-000000000003',
  '10000000-0000-0000-0000-000000000003',
  '00000000-0000-0000-0000-000000000001',  -- IDEC
  3,  -- treinador
  '2026-01-01',
  NOW(),
  NOW()
) ON CONFLICT (id) DO NOTHING;

-- ============================
-- ATLETA (role_id=4)
-- ============================
INSERT INTO persons (id, full_name, first_name, last_name, birth_date, created_at, updated_at) 
VALUES ('10000000-0000-0000-0000-000000000004', 'Atleta Teste', 'Atleta', 'Teste', '2010-03-10', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

INSERT INTO users (id, person_id, email, password_hash, is_superadmin, status, created_at, updated_at) 
VALUES (
  '20000000-0000-0000-0000-000000000004',
  '10000000-0000-0000-0000-000000000004',
  'atleta@teste.com',
  '$2b$12$loYyOoIZwD/nSCx5MJct2eCKM3cfBJsPRMPpn1TBOeABJjThxS/Ma',
  false,
  'ativo',
  NOW(),
  NOW()
) ON CONFLICT (id) DO NOTHING;

INSERT INTO org_memberships (id, person_id, organization_id, role_id, start_at, created_at, updated_at) 
VALUES (
  '30000000-0000-0000-0000-000000000004',
  '10000000-0000-0000-0000-000000000004',
  '00000000-0000-0000-0000-000000000001',  -- IDEC
  4,  -- atleta
  '2026-01-01',
  NOW(),
  NOW()
) ON CONFLICT (id) DO NOTHING;

-- Também criar como atleta real (tabela athletes)
INSERT INTO athletes (id, person_id, created_at, updated_at)
VALUES (
  '40000000-0000-0000-0000-000000000004',
  '10000000-0000-0000-0000-000000000004',
  NOW(),
  NOW()
) ON CONFLICT (id) DO NOTHING;

-- Vincular atleta à equipe principal
INSERT INTO team_registrations (id, athlete_id, team_id, season_id, jersey_number, position, created_at, updated_at)
VALUES (
  '50000000-0000-0000-0000-000000000001',
  '40000000-0000-0000-0000-000000000004',
  '00000000-0000-0000-0000-000000000006',  -- Equipe Principal
  '00000000-0000-0000-0000-000000000002',  -- Temporada 2026
  10,
  'P',  -- pivô
  NOW(),
  NOW()
) ON CONFLICT (id) DO NOTHING;

-- ============================
-- VERIFICAÇÕES
-- ============================
SELECT 'USUARIOS DE TESTE CRIADOS' as status;

SELECT 
  u.email,
  r.name as role_name,
  u.is_superadmin,
  u.status
FROM users u
JOIN persons p ON u.person_id = p.id
JOIN org_memberships om ON om.person_id = p.id
JOIN roles r ON om.role_id = r.id
WHERE u.email LIKE '%@teste.com'
ORDER BY r.id;
