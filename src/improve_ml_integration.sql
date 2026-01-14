-- Script d'amélioration de l'intégration des modèles ML
-- Ce script doit être exécuté pour améliorer l'intégration des modèles ML avec le reste du schéma

-- 1. Ajouter une colonne 'model_version' à la table ml_models
ALTER TABLE ml_models 
ADD COLUMN IF NOT EXISTS model_version VARCHAR(20) DEFAULT '1.0.0',
ADD COLUMN IF NOT EXISTS is_production BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS description TEXT;

-- Mettre à jour la version du modèle existant si nécessaire
UPDATE ml_models 
SET model_version = '1.0.0', 
    is_production = TRUE,
    description = 'Modèle initial de prédiction Keno'
WHERE model_name = 'KenoPredictorV1';

-- 2. Créer la table model_metrics pour suivre les métriques des modèles
CREATE TABLE IF NOT EXISTS model_metrics (
    id SERIAL PRIMARY KEY,
    model_id INTEGER NOT NULL REFERENCES ml_models(id) ON DELETE CASCADE,
    metric_name VARCHAR(50) NOT NULL,
    metric_value NUMERIC(10, 6) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    CONSTRAINT unique_metric_per_model UNIQUE (model_id, metric_name, created_at)
);

-- 3. Créer la table model_training_runs pour suivre les sessions d'entraînement
CREATE TABLE IF NOT EXISTS model_training_runs (
    id SERIAL PRIMARY KEY,
    model_id INTEGER NOT NULL REFERENCES ml_models(id) ON DELETE CASCADE,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL CHECK (status IN ('started', 'completed', 'failed')),
    training_params JSONB NOT NULL,
    metrics JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Ajouter une colonne model_id à la table predictions
ALTER TABLE predictions 
ADD COLUMN IF NOT EXISTS model_id INTEGER REFERENCES ml_models(id) ON DELETE SET NULL;

-- 5. Créer un index sur model_id pour améliorer les performances des requêtes
CREATE INDEX IF NOT EXISTS idx_predictions_model_id ON predictions(model_id);
CREATE INDEX IF NOT EXISTS idx_model_metrics_model_id ON model_metrics(model_id);
CREATE INDEX IF NOT EXISTS idx_training_runs_model_id ON model_training_runs(model_id);

-- 6. Mettre à jour les prédictions existantes pour les associer au modèle par défaut si nécessaire
-- (Cette partie est commentée car elle nécessite une logique métier spécifique)
-- UPDATE predictions
-- SET model_id = (SELECT id FROM ml_models WHERE model_name = 'KenoPredictorV1' LIMIT 1)
-- WHERE model_id IS NULL;

-- Vérification des modifications
SELECT 
    'ml_models' as table_name, 
    column_name, 
    data_type, 
    is_nullable
FROM 
    information_schema.columns 
WHERE 
    table_name = 'ml_models'
    AND column_name IN ('model_version', 'is_production', 'description')
UNION ALL
SELECT 
    table_name, 
    '-- TABLE --' as column_name, 
    '-- CREATED --' as data_type, 
    '--' as is_nullable
FROM 
    information_schema.tables 
WHERE 
    table_name IN ('model_metrics', 'model_training_runs')
ORDER BY 
    table_name, 
    column_name;
