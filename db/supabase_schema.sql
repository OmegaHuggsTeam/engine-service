-- Schema para gestão de API Keys no Supabase
-- Execute este script no SQL Editor do Supabase

-- Tabela principal de API Keys
CREATE TABLE IF NOT EXISTS api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  platform VARCHAR(50) NOT NULL,
  key_value TEXT NOT NULL,
  key_prefix VARCHAR(20),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  validated_at TIMESTAMPTZ,
  last_tested_at TIMESTAMPTZ,
  status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'expired', 'revoked')),
  metadata JSONB DEFAULT '{}'::jsonb,
  
  -- Constraint: apenas uma chave ativa por plataforma/prefixo
  UNIQUE(platform, key_prefix)
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_api_keys_platform ON api_keys(platform);
CREATE INDEX IF NOT EXISTS idx_api_keys_status ON api_keys(status);
CREATE INDEX IF NOT EXISTS idx_api_keys_created_at ON api_keys(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_keys_last_tested_at ON api_keys(last_tested_at DESC);

-- Índice GIN para busca em metadata (JSONB)
CREATE INDEX IF NOT EXISTS idx_api_keys_metadata ON api_keys USING GIN (metadata);

-- Row Level Security (RLS)
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

-- Política: Permitir todas as operações para usuários autenticados
-- IMPORTANTE: Ajuste conforme suas necessidades de segurança
CREATE POLICY "Allow all operations for authenticated users"
  ON api_keys
  FOR ALL
  TO authenticated
  USING (true)
  WITH CHECK (true);

-- Política: Permitir leitura para service_role (backend)
CREATE POLICY "Allow read for service role"
  ON api_keys
  FOR SELECT
  TO service_role
  USING (true);

-- Função para atualizar automaticamente last_tested_at
CREATE OR REPLACE FUNCTION update_last_tested_at()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.status = 'active' AND OLD.status != 'active' THEN
    NEW.last_tested_at = NOW();
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para atualizar last_tested_at quando status muda para active
CREATE TRIGGER trigger_update_last_tested_at
  BEFORE UPDATE ON api_keys
  FOR EACH ROW
  EXECUTE FUNCTION update_last_tested_at();

-- View para chaves ativas (sem expor key_value completo)
CREATE OR REPLACE VIEW api_keys_active AS
SELECT 
  id,
  platform,
  key_prefix,
  created_at,
  validated_at,
  last_tested_at,
  status,
  metadata
FROM api_keys
WHERE status = 'active';

-- Comentários para documentação
COMMENT ON TABLE api_keys IS 'Armazena API keys de diferentes plataformas (Groq, OpenAI, etc.)';
COMMENT ON COLUMN api_keys.platform IS 'Nome da plataforma (groq, openai, anthropic, etc.)';
COMMENT ON COLUMN api_keys.key_value IS 'Valor completo da API key (sensível)';
COMMENT ON COLUMN api_keys.key_prefix IS 'Prefixo da chave para identificação (primeiros 10 caracteres)';
COMMENT ON COLUMN api_keys.status IS 'Status da chave: active, expired, revoked';
COMMENT ON COLUMN api_keys.metadata IS 'Metadata adicional em JSON (validação, origem, etc.)';

-- Exemplo de insert (para testes)
-- INSERT INTO api_keys (platform, key_value, key_prefix, validated_at, metadata)
-- VALUES (
--   'groq',
--   'gsk_test123456789012345678901234567890',
--   'gsk_test12',
--   NOW(),
--   '{"validation": {"valid": true, "models_count": 5}, "origin": "manual"}'::jsonb
-- );

-- Query úteis para monitoramento

-- 1. Contar chaves por plataforma e status
-- SELECT platform, status, COUNT(*) as total
-- FROM api_keys
-- GROUP BY platform, status
-- ORDER BY platform, status;

-- 2. Chaves que não foram testadas há mais de 24h
-- SELECT id, platform, key_prefix, last_tested_at
-- FROM api_keys
-- WHERE status = 'active'
--   AND (last_tested_at IS NULL OR last_tested_at < NOW() - INTERVAL '24 hours')
-- ORDER BY last_tested_at ASC NULLS FIRST;

-- 3. Histórico de criação de chaves (últimos 7 dias)
-- SELECT DATE(created_at) as date, platform, COUNT(*) as total
-- FROM api_keys
-- WHERE created_at > NOW() - INTERVAL '7 days'
-- GROUP BY DATE(created_at), platform
-- ORDER BY date DESC, platform;
