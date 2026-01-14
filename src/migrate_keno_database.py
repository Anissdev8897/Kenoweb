#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de migration de la base de données Keno
Migration de l'ancien format (20/70) vers le nouveau format (16/56)

Ce script:
1. Crée une nouvelle table pour les tirages 2025
2. Archive les anciens tirages dans une table dédiée
3. Met à jour les contraintes de validation
4. Préserve toutes les données historiques
"""

import os
import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
import pandas as pd

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import de la configuration
from keno_config import KenoConfig, KenoVersion

class KenoDatabaseMigrator:
    """Migrateur de base de données pour la transition Keno 2025"""
    
    def __init__(self, database_url=None):
        """
        Initialise le migrateur
        
        Args:
            database_url: URL de connexion à la base de données (None = variable d'environnement)
        """
        self.database_url = database_url or os.environ.get("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set or not provided")
        
        self.engine = create_engine(self.database_url)
        self.transition_date = KenoConfig.TRANSITION_DATE
        
        logger.info(f"Migrateur initialisé avec transition date: {self.transition_date}")
    
    def create_new_tables(self):
        """Crée les nouvelles tables pour le format Keno 2025"""
        logger.info("Création des nouvelles tables Keno 2025...")
        
        with self.engine.connect() as conn:
            # Table pour les tirages archivés (ancien format)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS tirages_keno_archive (
                    id SERIAL PRIMARY KEY,
                    date_tirage DATE NOT NULL,
                    heure_tirage TIME,
                    numero_1 INTEGER NOT NULL CHECK (numero_1 BETWEEN 1 AND 70),
                    numero_2 INTEGER NOT NULL CHECK (numero_2 BETWEEN 1 AND 70),
                    numero_3 INTEGER NOT NULL CHECK (numero_3 BETWEEN 1 AND 70),
                    numero_4 INTEGER NOT NULL CHECK (numero_4 BETWEEN 1 AND 70),
                    numero_5 INTEGER NOT NULL CHECK (numero_5 BETWEEN 1 AND 70),
                    numero_6 INTEGER NOT NULL CHECK (numero_6 BETWEEN 1 AND 70),
                    numero_7 INTEGER NOT NULL CHECK (numero_7 BETWEEN 1 AND 70),
                    numero_8 INTEGER NOT NULL CHECK (numero_8 BETWEEN 1 AND 70),
                    numero_9 INTEGER NOT NULL CHECK (numero_9 BETWEEN 1 AND 70),
                    numero_10 INTEGER NOT NULL CHECK (numero_10 BETWEEN 1 AND 70),
                    numero_11 INTEGER NOT NULL CHECK (numero_11 BETWEEN 1 AND 70),
                    numero_12 INTEGER NOT NULL CHECK (numero_12 BETWEEN 1 AND 70),
                    numero_13 INTEGER NOT NULL CHECK (numero_13 BETWEEN 1 AND 70),
                    numero_14 INTEGER NOT NULL CHECK (numero_14 BETWEEN 1 AND 70),
                    numero_15 INTEGER NOT NULL CHECK (numero_15 BETWEEN 1 AND 70),
                    numero_16 INTEGER NOT NULL CHECK (numero_16 BETWEEN 1 AND 70),
                    numero_17 INTEGER NOT NULL CHECK (numero_17 BETWEEN 1 AND 70),
                    numero_18 INTEGER NOT NULL CHECK (numero_18 BETWEEN 1 AND 70),
                    numero_19 INTEGER NOT NULL CHECK (numero_19 BETWEEN 1 AND 70),
                    numero_20 INTEGER NOT NULL CHECK (numero_20 BETWEEN 1 AND 70),
                    multiplicateur INTEGER,
                    joker VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    migrated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date_tirage, heure_tirage)
                );
                
                COMMENT ON TABLE tirages_keno_archive IS 'Archive des tirages Keno ancien format (20/70)';
            """))
            
            # Table pour les tirages 2025 (nouveau format)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS tirages_keno_2025 (
                    id SERIAL PRIMARY KEY,
                    date_tirage DATE NOT NULL,
                    heure_tirage TIME,
                    numero_1 INTEGER NOT NULL CHECK (numero_1 BETWEEN 1 AND 56),
                    numero_2 INTEGER NOT NULL CHECK (numero_2 BETWEEN 1 AND 56),
                    numero_3 INTEGER NOT NULL CHECK (numero_3 BETWEEN 1 AND 56),
                    numero_4 INTEGER NOT NULL CHECK (numero_4 BETWEEN 1 AND 56),
                    numero_5 INTEGER NOT NULL CHECK (numero_5 BETWEEN 1 AND 56),
                    numero_6 INTEGER NOT NULL CHECK (numero_6 BETWEEN 1 AND 56),
                    numero_7 INTEGER NOT NULL CHECK (numero_7 BETWEEN 1 AND 56),
                    numero_8 INTEGER NOT NULL CHECK (numero_8 BETWEEN 1 AND 56),
                    numero_9 INTEGER NOT NULL CHECK (numero_9 BETWEEN 1 AND 56),
                    numero_10 INTEGER NOT NULL CHECK (numero_10 BETWEEN 1 AND 56),
                    numero_11 INTEGER NOT NULL CHECK (numero_11 BETWEEN 1 AND 56),
                    numero_12 INTEGER NOT NULL CHECK (numero_12 BETWEEN 1 AND 56),
                    numero_13 INTEGER NOT NULL CHECK (numero_13 BETWEEN 1 AND 56),
                    numero_14 INTEGER NOT NULL CHECK (numero_14 BETWEEN 1 AND 56),
                    numero_15 INTEGER NOT NULL CHECK (numero_15 BETWEEN 1 AND 56),
                    numero_16 INTEGER NOT NULL CHECK (numero_16 BETWEEN 1 AND 56),
                    multiplicateur INTEGER,
                    joker VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    version VARCHAR(20) DEFAULT '2025',
                    UNIQUE(date_tirage, heure_tirage)
                );
                
                COMMENT ON TABLE tirages_keno_2025 IS 'Tirages Keno nouveau format FDJ 2025 (16/56)';
            """))
            
            # Index pour optimiser les recherches
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_tirages_archive_date 
                ON tirages_keno_archive(date_tirage DESC);
                
                CREATE INDEX IF NOT EXISTS idx_tirages_2025_date 
                ON tirages_keno_2025(date_tirage DESC);
            """))
            
            conn.commit()
        
        logger.info("✅ Nouvelles tables créées avec succès")
    
    def archive_old_tirages(self):
        """Archive les anciens tirages dans la table d'archive"""
        logger.info("Archivage des anciens tirages...")
        
        with self.engine.connect() as conn:
            # Vérifier si la table originale existe
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'tirages_keno'
                );
            """))
            
            table_exists = result.scalar()
            
            if not table_exists:
                logger.warning("Table tirages_keno n'existe pas, pas d'archive à créer")
                return
            
            # Copier les anciens tirages (avant la date de transition) dans l'archive
            conn.execute(text(f"""
                INSERT INTO tirages_keno_archive (
                    date_tirage, heure_tirage,
                    numero_1, numero_2, numero_3, numero_4, numero_5,
                    numero_6, numero_7, numero_8, numero_9, numero_10,
                    numero_11, numero_12, numero_13, numero_14, numero_15,
                    numero_16, numero_17, numero_18, numero_19, numero_20,
                    multiplicateur, joker, created_at, migrated_at
                )
                SELECT 
                    date_tirage, heure_tirage,
                    numero_1, numero_2, numero_3, numero_4, numero_5,
                    numero_6, numero_7, numero_8, numero_9, numero_10,
                    numero_11, numero_12, numero_13, numero_14, numero_15,
                    numero_16, numero_17, numero_18, numero_19, numero_20,
                    multiplicateur, joker, created_at, CURRENT_TIMESTAMP
                FROM tirages_keno
                WHERE date_tirage < :transition_date
                ON CONFLICT (date_tirage, heure_tirage) DO NOTHING;
            """), {"transition_date": self.transition_date})
            
            archived_count = conn.execute(text("""
                SELECT COUNT(*) FROM tirages_keno_archive;
            """)).scalar()
            
            conn.commit()
            
            logger.info(f"✅ {archived_count} tirages archivés avec succès")
    
    def migrate_new_tirages(self):
        """Migre les tirages après la date de transition vers la nouvelle table"""
        logger.info("Migration des tirages 2025...")
        
        with self.engine.connect() as conn:
            # Vérifier si la table originale existe
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'tirages_keno'
                );
            """))
            
            table_exists = result.scalar()
            
            if not table_exists:
                logger.warning("Table tirages_keno n'existe pas, pas de migration à effectuer")
                return
            
            # Copier les nouveaux tirages (après la date de transition) dans la nouvelle table
            # Note: Les numéros > 56 seront filtrés lors de la migration
            conn.execute(text(f"""
                INSERT INTO tirages_keno_2025 (
                    date_tirage, heure_tirage,
                    numero_1, numero_2, numero_3, numero_4, numero_5,
                    numero_6, numero_7, numero_8, numero_9, numero_10,
                    numero_11, numero_12, numero_13, numero_14, numero_15,
                    numero_16, multiplicateur, joker, created_at, version
                )
                SELECT 
                    date_tirage, heure_tirage,
                    CASE WHEN numero_1 <= 56 THEN numero_1 ELSE NULL END,
                    CASE WHEN numero_2 <= 56 THEN numero_2 ELSE NULL END,
                    CASE WHEN numero_3 <= 56 THEN numero_3 ELSE NULL END,
                    CASE WHEN numero_4 <= 56 THEN numero_4 ELSE NULL END,
                    CASE WHEN numero_5 <= 56 THEN numero_5 ELSE NULL END,
                    CASE WHEN numero_6 <= 56 THEN numero_6 ELSE NULL END,
                    CASE WHEN numero_7 <= 56 THEN numero_7 ELSE NULL END,
                    CASE WHEN numero_8 <= 56 THEN numero_8 ELSE NULL END,
                    CASE WHEN numero_9 <= 56 THEN numero_9 ELSE NULL END,
                    CASE WHEN numero_10 <= 56 THEN numero_10 ELSE NULL END,
                    CASE WHEN numero_11 <= 56 THEN numero_11 ELSE NULL END,
                    CASE WHEN numero_12 <= 56 THEN numero_12 ELSE NULL END,
                    CASE WHEN numero_13 <= 56 THEN numero_13 ELSE NULL END,
                    CASE WHEN numero_14 <= 56 THEN numero_14 ELSE NULL END,
                    CASE WHEN numero_15 <= 56 THEN numero_15 ELSE NULL END,
                    CASE WHEN numero_16 <= 56 THEN numero_16 ELSE NULL END,
                    multiplicateur, joker, created_at, '2025'
                FROM tirages_keno
                WHERE date_tirage >= :transition_date
                AND numero_1 <= 56 AND numero_2 <= 56 AND numero_3 <= 56 AND numero_4 <= 56
                AND numero_5 <= 56 AND numero_6 <= 56 AND numero_7 <= 56 AND numero_8 <= 56
                AND numero_9 <= 56 AND numero_10 <= 56 AND numero_11 <= 56 AND numero_12 <= 56
                AND numero_13 <= 56 AND numero_14 <= 56 AND numero_15 <= 56 AND numero_16 <= 56
                ON CONFLICT (date_tirage, heure_tirage) DO NOTHING;
            """), {"transition_date": self.transition_date})
            
            migrated_count = conn.execute(text("""
                SELECT COUNT(*) FROM tirages_keno_2025;
            """)).scalar()
            
            conn.commit()
            
            logger.info(f"✅ {migrated_count} tirages 2025 migrés avec succès")
    
    def create_view_unified(self):
        """Crée une vue unifiée pour faciliter les requêtes"""
        logger.info("Création de la vue unifiée...")
        
        with self.engine.connect() as conn:
            conn.execute(text("""
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
            """))
            
            conn.commit()
        
        logger.info("✅ Vue unifiée créée avec succès")
    
    def run_migration(self, dry_run=False):
        """
        Exécute la migration complète
        
        Args:
            dry_run: Si True, simule la migration sans appliquer les changements
        """
        logger.info("=" * 60)
        logger.info("DÉBUT DE LA MIGRATION KENO 2025")
        logger.info("=" * 60)
        
        if dry_run:
            logger.warning("⚠️  MODE DRY RUN - Aucun changement ne sera appliqué")
        
        try:
            # 1. Créer les nouvelles tables
            if not dry_run:
                self.create_new_tables()
            
            # 2. Archiver les anciens tirages
            if not dry_run:
                self.archive_old_tirages()
            
            # 3. Migrer les nouveaux tirages
            if not dry_run:
                self.migrate_new_tirages()
            
            # 4. Créer la vue unifiée
            if not dry_run:
                self.create_view_unified()
            
            logger.info("=" * 60)
            logger.info("✅ MIGRATION TERMINÉE AVEC SUCCÈS")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la migration: {e}")
            return False


def main():
    """Fonction principale du script de migration"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migration base de données Keno 2025")
    parser.add_argument('--dry-run', action='store_true',
                       help='Simule la migration sans appliquer les changements')
    parser.add_argument('--database-url', type=str,
                       help='URL de connexion à la base de données (override DATABASE_URL)')
    
    args = parser.parse_args()
    
    try:
        migrator = KenoDatabaseMigrator(database_url=args.database_url)
        success = migrator.run_migration(dry_run=args.dry_run)
        
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

