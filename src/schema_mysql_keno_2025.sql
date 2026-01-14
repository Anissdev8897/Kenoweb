-- ============================================================
-- Schéma MySQL pour Keno Analyzer Pro - Format Keno 2025
-- Base de données MySQL compatible avec le nouveau format FDJ 2025
-- Format: 16 numéros tirés parmi 56 (au lieu de 20/70)
-- ============================================================

-- Créer la base de données si elle n'existe pas
-- DÉCOMMENTER LA LIGNE SUIVANTE ET MODIFIER LE NOM SI NÉCESSAIRE
-- CREATE DATABASE IF NOT EXISTS keno_analyzer CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE keno_analyzer;

-- ============================================================
-- TABLE 1: Archive des tirages ancien format (20/70)
-- ============================================================
CREATE TABLE IF NOT EXISTS tirages_keno_archive (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date_tirage DATE NOT NULL,
    heure_tirage TIME,
    numero_1 INT NOT NULL CHECK (numero_1 BETWEEN 1 AND 70),
    numero_2 INT NOT NULL CHECK (numero_2 BETWEEN 1 AND 70),
    numero_3 INT NOT NULL CHECK (numero_3 BETWEEN 1 AND 70),
    numero_4 INT NOT NULL CHECK (numero_4 BETWEEN 1 AND 70),
    numero_5 INT NOT NULL CHECK (numero_5 BETWEEN 1 AND 70),
    numero_6 INT NOT NULL CHECK (numero_6 BETWEEN 1 AND 70),
    numero_7 INT NOT NULL CHECK (numero_7 BETWEEN 1 AND 70),
    numero_8 INT NOT NULL CHECK (numero_8 BETWEEN 1 AND 70),
    numero_9 INT NOT NULL CHECK (numero_9 BETWEEN 1 AND 70),
    numero_10 INT NOT NULL CHECK (numero_10 BETWEEN 1 AND 70),
    numero_11 INT NOT NULL CHECK (numero_11 BETWEEN 1 AND 70),
    numero_12 INT NOT NULL CHECK (numero_12 BETWEEN 1 AND 70),
    numero_13 INT NOT NULL CHECK (numero_13 BETWEEN 1 AND 70),
    numero_14 INT NOT NULL CHECK (numero_14 BETWEEN 1 AND 70),
    numero_15 INT NOT NULL CHECK (numero_15 BETWEEN 1 AND 70),
    numero_16 INT NOT NULL CHECK (numero_16 BETWEEN 1 AND 70),
    numero_17 INT NOT NULL CHECK (numero_17 BETWEEN 1 AND 70),
    numero_18 INT NOT NULL CHECK (numero_18 BETWEEN 1 AND 70),
    numero_19 INT NOT NULL CHECK (numero_19 BETWEEN 1 AND 70),
    numero_20 INT NOT NULL CHECK (numero_20 BETWEEN 1 AND 70),
    multiplicateur INT,
    joker VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    migrated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_tirage_archive (date_tirage, heure_tirage)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Archive des tirages Keno ancien format (20 numéros sur 70)';

-- ============================================================
-- TABLE 2: Tirages nouveau format 2025 (16/56)
-- ============================================================
CREATE TABLE IF NOT EXISTS tirages_keno_2025 (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date_tirage DATE NOT NULL,
    heure_tirage TIME,
    numero_1 INT NOT NULL CHECK (numero_1 BETWEEN 1 AND 56),
    numero_2 INT NOT NULL CHECK (numero_2 BETWEEN 1 AND 56),
    numero_3 INT NOT NULL CHECK (numero_3 BETWEEN 1 AND 56),
    numero_4 INT NOT NULL CHECK (numero_4 BETWEEN 1 AND 56),
    numero_5 INT NOT NULL CHECK (numero_5 BETWEEN 1 AND 56),
    numero_6 INT NOT NULL CHECK (numero_6 BETWEEN 1 AND 56),
    numero_7 INT NOT NULL CHECK (numero_7 BETWEEN 1 AND 56),
    numero_8 INT NOT NULL CHECK (numero_8 BETWEEN 1 AND 56),
    numero_9 INT NOT NULL CHECK (numero_9 BETWEEN 1 AND 56),
    numero_10 INT NOT NULL CHECK (numero_10 BETWEEN 1 AND 56),
    numero_11 INT NOT NULL CHECK (numero_11 BETWEEN 1 AND 56),
    numero_12 INT NOT NULL CHECK (numero_12 BETWEEN 1 AND 56),
    numero_13 INT NOT NULL CHECK (numero_13 BETWEEN 1 AND 56),
    numero_14 INT NOT NULL CHECK (numero_14 BETWEEN 1 AND 56),
    numero_15 INT NOT NULL CHECK (numero_15 BETWEEN 1 AND 56),
    numero_16 INT NOT NULL CHECK (numero_16 BETWEEN 1 AND 56),
    multiplicateur INT,
    joker VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version VARCHAR(20) DEFAULT '2025',
    UNIQUE KEY unique_tirage_2025 (date_tirage, heure_tirage)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Tirages Keno nouveau format FDJ 2025 (16 numéros sur 56)';

-- ============================================================
-- TABLE 3: Utilisateurs
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    session_id VARCHAR(100),
    ip_address VARCHAR(45),  -- IPv6 compatible (max 45 caractères)
    user_agent TEXT,
    first_prediction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    total_predictions INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Utilisateurs du système Keno Analyzer';

-- ============================================================
-- TABLE 4: Modèles ML
-- ============================================================
CREATE TABLE IF NOT EXISTS ml_models (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    method_name VARCHAR(100) NOT NULL,
    s3_path VARCHAR(500) NOT NULL,
    training_score DECIMAL(10, 8),
    test_score DECIMAL(10, 8),
    r2_score DECIMAL(10, 8),
    training_time_seconds INT,
    trained_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    metadata JSON,  -- MySQL 5.7+ supporte JSON natif
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Modèles Machine Learning pour les prédictions';

-- ============================================================
-- TABLE 5: Prédictions unifiées (utilisateurs + modèles ML)
-- ============================================================
CREATE TABLE IF NOT EXISTS unified_predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    predictor_id VARCHAR(100) NOT NULL,
    predictor_type ENUM('USER', 'ML_MODEL') NOT NULL,
    session_id VARCHAR(100),
    prediction_method VARCHAR(100) NOT NULL,
    predicted_numbers JSON NOT NULL,  -- Tableau JSON des numéros prédits
    confidence_score DECIMAL(5, 4),
    target_tirage_date DATE NOT NULL,
    target_tirage_time TIME,
    actual_numbers JSON,  -- Tableau JSON des numéros réels tirés
    correct_count INT DEFAULT 0,
    accuracy_percentage DECIMAL(5, 2) DEFAULT 0.0,
    is_evaluated BOOLEAN DEFAULT FALSE,
    prediction_hash VARCHAR(64),  -- Hash pour éviter les doublons
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    evaluated_at TIMESTAMP NULL,
    UNIQUE KEY unique_prediction (predictor_id, prediction_method, target_tirage_date, prediction_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Prédictions unifiées des utilisateurs et modèles ML';

-- ============================================================
-- TABLE 6: Performances par méthode et utilisateur
-- ============================================================
CREATE TABLE IF NOT EXISTS method_performance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    predictor_id VARCHAR(100) NOT NULL,
    method_name VARCHAR(100) NOT NULL,
    predictor_type ENUM('USER', 'ML_MODEL') NOT NULL,
    total_predictions INT DEFAULT 0,
    total_evaluated INT DEFAULT 0,
    total_correct_numbers INT DEFAULT 0,
    average_accuracy DECIMAL(5, 2) DEFAULT 0.0,
    best_score INT DEFAULT 0,
    worst_score INT DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_performance (predictor_id, method_name, predictor_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Performances des méthodes de prédiction par utilisateur';

-- ============================================================
-- TABLE 7: Erreurs de prédiction
-- ============================================================
CREATE TABLE IF NOT EXISTS prediction_errors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    prediction_id INT,
    predictor_id VARCHAR(100) NOT NULL,
    predictor_type ENUM('USER', 'ML_MODEL') NOT NULL,
    method_name VARCHAR(100) NOT NULL,
    predicted_but_not_drawn JSON NOT NULL,  -- Numéros prédits mais non tirés
    drawn_but_not_predicted JSON NOT NULL,  -- Numéros tirés mais non prédits
    correct_predictions JSON NOT NULL,  -- Numéros correctement prédits
    error_count INT NOT NULL,
    miss_count INT NOT NULL,  -- Nombre de numéros manqués
    tirage_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prediction_id) REFERENCES unified_predictions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Erreurs détaillées par prédiction';

-- ============================================================
-- TABLE 8: Historique d'entraînement ML
-- ============================================================
CREATE TABLE IF NOT EXISTS ml_training_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    training_start TIMESTAMP NOT NULL,
    training_end TIMESTAMP NOT NULL,
    data_start_date DATE NOT NULL,
    data_end_date DATE NOT NULL,
    total_tirages_used INT NOT NULL,
    training_metrics JSON,  -- Métriques d'entraînement en JSON
    retrain_trigger VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Historique des entraînements Machine Learning';

-- ============================================================
-- TABLE 9: Sessions utilisateur
-- ============================================================
CREATE TABLE IF NOT EXISTS user_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    user_id VARCHAR(100),
    ip_address VARCHAR(45),  -- IPv6 compatible
    user_agent TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    predictions_count INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Sessions utilisateur pour le suivi';

-- ============================================================
-- INDEX pour optimiser les performances
-- ============================================================

-- Index pour tirages_keno_archive
CREATE INDEX IF NOT EXISTS idx_tirages_archive_date ON tirages_keno_archive(date_tirage DESC);

-- Index pour tirages_keno_2025
CREATE INDEX IF NOT EXISTS idx_tirages_2025_date ON tirages_keno_2025(date_tirage DESC);

-- Index pour users
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_users_session_id ON users(session_id);

-- Index pour unified_predictions
CREATE INDEX IF NOT EXISTS idx_unified_predictions_predictor ON unified_predictions(predictor_id, predictor_type);
CREATE INDEX IF NOT EXISTS idx_unified_predictions_method ON unified_predictions(prediction_method);
CREATE INDEX IF NOT EXISTS idx_unified_predictions_target_date ON unified_predictions(target_tirage_date DESC);

-- Index pour method_performance
CREATE INDEX IF NOT EXISTS idx_method_performance_predictor ON method_performance(predictor_id, method_name);

-- Index pour prediction_errors
CREATE INDEX IF NOT EXISTS idx_prediction_errors_predictor ON prediction_errors(predictor_id, method_name);
CREATE INDEX IF NOT EXISTS idx_prediction_errors_date ON prediction_errors(tirage_date DESC);

-- Index pour user_sessions
CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);

-- ============================================================
-- VUE UNIFIÉE pour faciliter les requêtes
-- ============================================================
CREATE OR REPLACE VIEW tirages_keno_unified AS
SELECT 
    id, date_tirage, heure_tirage,
    numero_1, numero_2, numero_3, numero_4, numero_5,
    numero_6, numero_7, numero_8, numero_9, numero_10,
    numero_11, numero_12, numero_13, numero_14, numero_15,
    numero_16, numero_17, numero_18, numero_19, numero_20,
    multiplicateur, joker, created_at,
    'archive' as version, 20 as numbers_per_draw, 70 as max_number
FROM tirages_keno_archive
UNION ALL
SELECT 
    id, date_tirage, heure_tirage,
    numero_1, numero_2, numero_3, numero_4, numero_5,
    numero_6, numero_7, numero_8, numero_9, numero_10,
    numero_11, numero_12, numero_13, numero_14, numero_15,
    numero_16, NULL as numero_17, NULL as numero_18, 
    NULL as numero_19, NULL as numero_20,
    multiplicateur, joker, created_at,
    version, 16 as numbers_per_draw, 56 as max_number
FROM tirages_keno_2025;

-- ============================================================
-- FIN DU SCRIPT
-- ============================================================

