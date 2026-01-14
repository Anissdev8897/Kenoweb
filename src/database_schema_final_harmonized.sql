-- Schéma SQL complet et harmonisé pour Keno Analyzer Pro
-- Toutes les tables avec structures et noms cohérents

-- Extensions nécessaires
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Table principale des tirages
CREATE TABLE IF NOT EXISTS tirages (
    id SERIAL PRIMARY KEY,
    date_tirage DATE NOT NULL,
    numeros INTEGER[] NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_tirages_date ON tirages(date_tirage);
CREATE INDEX IF NOT EXISTS idx_tirages_numeros ON tirages USING GIN(numeros);

-- Table des utilisateurs
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    is_moderator BOOLEAN DEFAULT FALSE,
    total_predictions INTEGER DEFAULT 0,
    correct_predictions INTEGER DEFAULT 0,
    accuracy_rate NUMERIC(5,4) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des prédictions
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    tirage_id INTEGER REFERENCES tirages(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    method VARCHAR(100) NOT NULL,
    numeros INTEGER[] NOT NULL,
    confidence NUMERIC(5,4) DEFAULT 0.0,
    correct_count INTEGER DEFAULT 0,
    is_validated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des statistiques de méthodes
CREATE TABLE IF NOT EXISTS method_stats (
    id SERIAL PRIMARY KEY,
    method VARCHAR(100) UNIQUE NOT NULL,
    total_predictions INTEGER DEFAULT 0,
    successful_predictions INTEGER DEFAULT 0,
    success_rate DECIMAL(5,2) DEFAULT 0.00,
    avg_confidence DECIMAL(5,2) DEFAULT 0.00,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des résultats d'analyse
CREATE TABLE IF NOT EXISTS analysis_results (
    id SERIAL PRIMARY KEY,
    tirage_id INTEGER REFERENCES tirages(id) ON DELETE CASCADE,
    analysis_type VARCHAR(50) NOT NULL,
    result_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des modèles ML
CREATE TABLE IF NOT EXISTS ml_models (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    weights JSONB,
    training_score NUMERIC(10,8),
    test_score NUMERIC(10,8),
    r2_score NUMERIC(10,8),
    training_time_seconds INTEGER,
    is_active BOOLEAN DEFAULT FALSE,
    parameters JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    trained_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_tirages_date ON tirages(date_tirage DESC);
CREATE INDEX IF NOT EXISTS idx_tirages_numeros ON tirages USING GIN(numeros);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_predictions_user ON predictions(user_id);
CREATE INDEX IF NOT EXISTS idx_predictions_method ON predictions(method);
CREATE INDEX IF NOT EXISTS idx_predictions_created ON predictions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_tirage ON predictions(tirage_id);
CREATE INDEX IF NOT EXISTS idx_analysis_tirage ON analysis_results(tirage_id);
CREATE INDEX IF NOT EXISTS idx_method_stats_method ON method_stats(method);

-- Insertion de données de test
INSERT INTO tirages (date_tirage, numeros) VALUES 
('2024-01-15', ARRAY[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]),
('2024-01-16', ARRAY[21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40])
ON CONFLICT DO NOTHING;

-- Insertion de statistiques de méthodes
INSERT INTO method_stats (method, total_predictions, successful_predictions, success_rate, avg_confidence) VALUES 
('frequency_analysis', 0, 0, 0.00, 0.00),
('monte_carlo', 0, 0, 0.00, 0.00),
('ml_prediction', 0, 0, 0.00, 0.00)
ON CONFLICT (method) DO NOTHING;

-- Insertion d'un administrateur
INSERT INTO users (username, email, password_hash, is_admin, is_moderator) VALUES 
('admin', 'admin@kenoanalyzer.com', '$2b$12$KIXxP3K1Kp5K4K5K6K7K8K9K0K1K2K3K4K5K6K7K8K9K0K1K2', TRUE, TRUE)
ON CONFLICT DO NOTHING;
