-- ================================================
-- KENO ANALYZER PRO - SCHEMA SQL FINAL UNIFIÉ
-- BASÉ SUR LE FICHIER public.sql
-- TOUTES LES TABLES CONNECTÉES ENSEMBLE
-- ================================================

-- ================================================================
-- 1. SEQUENCES (MAINTENUES DU public.sql)
-- ================================================================
DROP SEQUENCE IF EXISTS analysis_results_id_seq CASCADE;
CREATE SEQUENCE analysis_results_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 START 1 CACHE 1;

DROP SEQUENCE IF EXISTS backups_id_seq CASCADE;
CREATE SEQUENCE backups_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 START 1 CACHE 1;

DROP SEQUENCE IF EXISTS method_stats_id_seq CASCADE;
CREATE SEQUENCE method_stats_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 START 1 CACHE 1;

DROP SEQUENCE IF EXISTS ml_models_id_seq CASCADE;
CREATE SEQUENCE ml_models_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 START 1 CACHE 1;

DROP SEQUENCE IF EXISTS predictions_id_seq CASCADE;
CREATE SEQUENCE predictions_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 START 1 CACHE 1;

DROP SEQUENCE IF EXISTS tirages_keno_id_seq CASCADE;
CREATE SEQUENCE tirages_keno_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 START 1 CACHE 1;

DROP SEQUENCE IF EXISTS users_id_seq CASCADE;
CREATE SEQUENCE users_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 START 1 CACHE 1;

-- ================================================================
-- 2. TABLES PRINCIPALES UNIFIÉES
-- ================================================================

-- ================================================
-- 2.1 TABLE DES TIRAGES KENO (UNIFIÉE)
-- ================================================
DROP TABLE IF EXISTS tirages_keno CASCADE;
CREATE TABLE tirages_keno (
    id INTEGER NOT NULL DEFAULT nextval('tirages_keno_id_seq'::regclass),
    date_tirage DATE NOT NULL,
    heure_tirage TIME,
    numeros INTEGER[20] NOT NULL,
    multiplicateur INTEGER,
    joker VARCHAR(20),
    periode VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

-- ================================================
-- 2.2 TABLE DES PRÉDICTIONS (USER + SYSTEM)
-- ================================================
DROP TABLE IF EXISTS predictions CASCADE;
CREATE TABLE predictions (
    id INTEGER NOT NULL DEFAULT nextval('predictions_id_seq'::regclass),
    tirage_id INTEGER REFERENCES tirages_keno(id) ON DELETE SET NULL,
    user_id VARCHAR(50) NOT NULL,
    method VARCHAR(100) NOT NULL,
    numeros INTEGER[] NOT NULL,
    confidence NUMERIC(5,4) DEFAULT 0.0,
    correct_count INTEGER DEFAULT 0,
    is_validated BOOLEAN DEFAULT FALSE,
    session_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

-- ================================================
-- 2.3 TABLE DES UTILISATEURS
-- ================================================
DROP TABLE IF EXISTS users CASCADE;
CREATE TABLE users (
    id INTEGER NOT NULL DEFAULT nextval('users_id_seq'::regclass),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255),
    password_hash VARCHAR(255),
    total_predictions INTEGER DEFAULT 0,
    correct_predictions INTEGER DEFAULT 0,
    accuracy_rate NUMERIC(5,4) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

-- ================================================
-- 2.4 TABLE DES RÉSULTATS D'ANALYSE
-- ================================================
DROP TABLE IF EXISTS analysis_results CASCADE;
CREATE TABLE analysis_results (
    id INTEGER NOT NULL DEFAULT nextval('analysis_results_id_seq'::regclass),
    analysis_type VARCHAR(50) NOT NULL,
    parameters JSONB,
    results JSONB NOT NULL,
    execution_time_ms INTEGER,
    prediction_id INTEGER REFERENCES predictions(id) ON DELETE CASCADE,
    tirage_id INTEGER REFERENCES tirages_keno(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

-- ================================================
-- 2.5 TABLE DES STATISTIQUES PAR MÉTHODE
-- ================================================
DROP TABLE IF EXISTS method_stats CASCADE;
CREATE TABLE method_stats (
    id INTEGER NOT NULL DEFAULT nextval('method_stats_id_seq'::regclass),
    method VARCHAR(100) UNIQUE NOT NULL,
    total_predictions INTEGER DEFAULT 0,
    correct_predictions INTEGER DEFAULT 0,
    accuracy NUMERIC(5,4) DEFAULT 0.0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

-- ================================================
-- 2.6 TABLE DES MODÈLES ML
-- ================================================
DROP TABLE IF EXISTS ml_models CASCADE;
CREATE TABLE ml_models (
    id INTEGER NOT NULL DEFAULT nextval('ml_models_id_seq'::regclass),
    model_name VARCHAR(100) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    parameters JSONB,
    training_score NUMERIC(10,8),
    test_score NUMERIC(10,8),
    r2_score NUMERIC(10,8),
    training_time_seconds INTEGER,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    trained_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

-- ================================================
-- 2.7 TABLE DES SAUVEGARDES
-- ================================================
DROP TABLE IF EXISTS backups CASCADE;
CREATE TABLE backups (
    id INTEGER NOT NULL DEFAULT nextval('backups_id_seq'::regclass),
    backup_type VARCHAR(50) NOT NULL,
    backup_data JSONB NOT NULL,
    file_path TEXT,
    checksum VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

-- ================================================================
-- 3. INDEX POUR PERFORMANCE
-- ================================================================
CREATE INDEX IF NOT EXISTS idx_tirages_date ON tirages_keno(date_tirage DESC);
CREATE INDEX IF NOT EXISTS idx_tirages_numeros ON tirages_keno USING GIN(numeros);
CREATE INDEX IF NOT EXISTS idx_predictions_user ON predictions(user_id);
CREATE INDEX IF NOT EXISTS idx_predictions_method ON predictions(method);
CREATE INDEX IF NOT EXISTS idx_predictions_created ON predictions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_tirage ON predictions(tirage_id);
CREATE INDEX IF NOT EXISTS idx_analysis_tirage ON analysis_results(tirage_id);
CREATE INDEX IF NOT EXISTS idx_analysis_prediction ON analysis_results(prediction_id);

-- ================================================================
-- 4. VUES POUR STATISTIQUES UNIFIÉES
-- ================================================================

-- Vue des statistiques globales
DROP VIEW IF EXISTS v_global_stats CASCADE;
CREATE VIEW v_global_stats AS
SELECT 
    (SELECT COUNT(*) FROM tirages_keno) as total_tirages,
    (SELECT COUNT(*) FROM predictions) as total_predictions,
    (SELECT COUNT(*) FROM users) as total_users,
    (SELECT COUNT(*) FROM predictions WHERE user_id = 'system') as system_predictions,
    (SELECT COUNT(*) FROM predictions WHERE user_id != 'system') as user_predictions,
    (SELECT AVG(confidence) FROM predictions) as avg_confidence,
    (SELECT AVG(correct_count) FROM predictions) as avg_correct;

-- Vue des statistiques par méthode
DROP VIEW IF EXISTS v_method_stats CASCADE;
CREATE VIEW v_method_stats AS
SELECT 
    method,
    COUNT(*) as total_predictions,
    AVG(confidence) as avg_confidence,
    AVG(correct_count) as avg_correct,
    COUNT(CASE WHEN user_id = 'system' THEN 1 END) as system_count,
    COUNT(CASE WHEN user_id != 'system' THEN 1 END) as user_count
FROM predictions
GROUP BY method
ORDER BY total_predictions DESC;

-- Vue des performances utilisateur
DROP VIEW IF EXISTS v_user_performance CASCADE;
CREATE VIEW v_user_performance AS
SELECT 
    u.username,
    COALESCE(COUNT(p.id), 0) as total_predictions,
    COALESCE(AVG(p.confidence), 0) as avg_confidence,
    COALESCE(AVG(p.correct_count), 0) as avg_correct,
    COALESCE(COUNT(CASE WHEN p.is_validated = TRUE THEN 1 END), 0) as validated_predictions
FROM users u
LEFT JOIN predictions p ON u.username = p.user_id
GROUP BY u.username
ORDER BY total_predictions DESC;

-- Vue des dernières prédictions
DROP VIEW IF EXISTS v_recent_predictions CASCADE;
CREATE VIEW v_recent_predictions AS
SELECT 
    p.*,
    tk.date_tirage,
    tk.numeros as actual_numbers,
    u.email as user_email
FROM predictions p
LEFT JOIN tirages_keno tk ON p.tirage_id = tk.id
LEFT JOIN users u ON p.user_id = u.username
ORDER BY p.created_at DESC
LIMIT 100;

-- ================================================================
-- 5. FONCTIONS UTILITAIRES UNIFIÉES
-- ================================================================

-- Fonction pour mettre à jour les statistiques de méthode
CREATE OR REPLACE FUNCTION update_method_stats()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO method_stats (method, total_predictions, correct_predictions, accuracy)
    VALUES (NEW.method, 1, NEW.correct_count, CASE WHEN NEW.correct_count > 0 THEN 1.0 ELSE 0.0 END)
    ON CONFLICT (method) DO UPDATE SET
        total_predictions = method_stats.total_predictions + 1,
        correct_predictions = method_stats.correct_predictions + EXCLUDED.correct_predictions,
        accuracy = (method_stats.correct_predictions + EXCLUDED.correct_predictions)::NUMERIC / (method_stats.total_predictions + 1),
        last_updated = CURRENT_TIMESTAMP;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour mettre à jour les statistiques utilisateur
CREATE OR REPLACE FUNCTION update_user_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.user_id != 'system' THEN
        UPDATE users 
        SET total_predictions = total_predictions + 1,
            correct_predictions = correct_predictions + NEW.correct_count,
            accuracy_rate = (correct_predictions + NEW.correct_count)::NUMERIC / (total_predictions + 1),
            last_active = CURRENT_TIMESTAMP
        WHERE username = NEW.user_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- 6. TRIGGERS POUR AUTOMATISATION
-- ================================================================

-- Trigger pour mettre à jour les statistiques après une nouvelle prédiction
DROP TRIGGER IF EXISTS trigger_update_method_stats ON predictions;
CREATE TRIGGER trigger_update_method_stats
    AFTER INSERT OR UPDATE ON predictions
    FOR EACH ROW EXECUTE FUNCTION update_method_stats();

-- Trigger pour mettre à jour les statistiques utilisateur
DROP TRIGGER IF EXISTS trigger_update_user_stats ON predictions;
CREATE TRIGGER trigger_update_user_stats
    AFTER INSERT OR UPDATE ON predictions
    FOR EACH ROW EXECUTE FUNCTION update_user_stats();

-- ================================================================
-- 7. DONNÉES DE BASE (MÉTHODES D'ANALYSE)
-- ================================================================
INSERT INTO method_stats (method, total_predictions, correct_predictions, accuracy) VALUES
('frequency', 0, 0, 0.0),
('gaps', 0, 0, 0.0),
('cycles', 0, 0, 0.0),
('mixed', 0, 0, 0.0),
('ml', 0, 0, 0.0),
('fibonacci', 0, 0, 0.0),
('sums', 0, 0, 0.0),
('complete', 0, 0, 0.0)
ON CONFLICT (method) DO NOTHING;

-- ================================================================
-- 8. INDEX SUPPLÉMENTAIRES POUR PERFORMANCE
-- ================================================================
CREATE INDEX IF NOT EXISTS idx_tirages_created ON tirages_keno(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_confidence ON predictions(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_correct ON predictions(correct_count DESC);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_method_stats_method ON method_stats(method);

-- ================================================================
-- 9. COMMENTAIRES POUR DOCUMENTATION
-- ================================================================
COMMENT ON TABLE tirages_keno IS 'Table principale des tirages Keno FDJ';
COMMENT ON TABLE predictions IS 'Table unifiée des prédictions (utilisateur + système)';
COMMENT ON TABLE users IS 'Table des utilisateurs enregistrés';
COMMENT ON TABLE analysis_results IS 'Résultats détaillés des analyses';
COMMENT ON TABLE method_stats IS 'Statistiques par méthode d analyse';
COMMENT ON TABLE ml_models IS 'Modèles ML et leurs performances';
COMMENT ON TABLE backups IS 'Sauvegardes des données';

COMMENT ON COLUMN predictions.user_id IS 'ID utilisateur ou "system" pour les prédictions système';
COMMENT ON COLUMN predictions.method IS 'Méthode d analyse utilisée (frequency, gaps, cycles, etc.)';
COMMENT ON COLUMN predictions.confidence IS 'Score de confiance de la prédiction (0.0000 - 1.0000)';
COMMENT ON COLUMN predictions.correct_count IS 'Nombre de numéros corrects lors de la validation';

-- ================================================================
-- 10. FONCTION DE VALIDATION DES PRÉDICTIONS
-- ================================================================
CREATE OR REPLACE FUNCTION validate_prediction(prediction_id INTEGER, actual_numbers INTEGER[])
RETURNS INTEGER AS $$
DECLARE
    pred RECORD;
    correct_count INTEGER;
BEGIN
    SELECT * INTO pred FROM predictions WHERE id = prediction_id;
    
    IF FOUND THEN
        -- Calculer le nombre de numéros corrects
        SELECT COUNT(*) INTO correct_count
        FROM unnest(pred.numeros) AS pred_num
        WHERE pred_num = ANY(actual_numbers);
        
        -- Mettre à jour la prédiction
        UPDATE predictions 
        SET correct_count = correct_count,
            is_validated = TRUE,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = prediction_id;
        
        RETURN correct_count;
    END IF;
    
    RETURN 0;
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- 11. FONCTION DE NETTOYAGE DES DONNÉES ANCIENNES
-- ================================================================
CREATE OR REPLACE FUNCTION cleanup_old_data(days_to_keep INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Supprimer les prédictions anciennes
    DELETE FROM predictions 
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * days_to_keep
    AND is_validated = TRUE;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
