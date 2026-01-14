#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de migration MySQL pour Keno 2025
Crée les tables et migre les données vers MySQL
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
from keno_config import KenoConfig

class KenoMySQLMigrator:
    """Migrateur MySQL pour la transition Keno 2025"""
    
    def __init__(self, database_url=None):
        """
        Initialise le migrateur MySQL
        
        Args:
            database_url: URL de connexion MySQL (None = variable d'environnement)
        """
        self.database_url = database_url or os.environ.get("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set or not provided")
        
        # Vérifier que c'est MySQL
        if not self.database_url.startswith('mysql'):
            raise ValueError("L'URL doit être MySQL. Format: mysql+pymysql://user:pass@host/db")
        
        self.engine = create_engine(self.database_url)
        self.transition_date = KenoConfig.TRANSITION_DATE
        
        logger.info(f"Migrateur MySQL initialisé avec transition date: {self.transition_date}")
    
    def execute_sql_file(self, sql_file_path: str):
        """
        Exécute un fichier SQL
        
        Args:
            sql_file_path: Chemin vers le fichier SQL
        """
        logger.info(f"Exécution du fichier SQL: {sql_file_path}")
        
        if not os.path.exists(sql_file_path):
            logger.error(f"Fichier SQL introuvable: {sql_file_path}")
            return False
        
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Diviser le contenu en commandes individuelles
        statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]
        
        with self.engine.connect() as conn:
            for statement in statements:
                if statement:
                    try:
                        conn.execute(text(statement))
                        logger.debug(f"Exécuté: {statement[:50]}...")
                    except Exception as e:
                        logger.warning(f"Erreur lors de l'exécution: {e}")
                        logger.debug(f"Statement: {statement[:100]}")
            
            conn.commit()
        
        logger.info("✅ Fichier SQL exécuté avec succès")
        return True
    
    def create_tables_from_schema(self):
        """Crée les tables depuis le fichier schema_mysql_keno_2025.sql"""
        schema_path = os.path.join(os.path.dirname(__file__), 'schema_mysql_keno_2025.sql')
        return self.execute_sql_file(schema_path)
    
    def migrate_from_postgresql(self, postgresql_url: str):
        """
        Migre les données depuis PostgreSQL vers MySQL
        
        Args:
            postgresql_url: URL de connexion PostgreSQL source
        """
        logger.info("Migration des données depuis PostgreSQL vers MySQL...")
        
        try:
            from sqlalchemy import create_engine as create_pg_engine
            pg_engine = create_pg_engine(postgresql_url)
            
            # Récupérer les tirages archivés (ancien format)
            logger.info("Récupération des tirages archivés...")
            df_archive = pd.read_sql("""
                SELECT * FROM tirages_keno_archive
                ORDER BY date_tirage DESC
            """, pg_engine)
            
            logger.info(f"{len(df_archive)} tirages archivés trouvés")
            
            # Insérer dans MySQL
            if not df_archive.empty:
                with self.engine.connect() as conn:
                    for _, row in df_archive.iterrows():
                        try:
                            conn.execute(text("""
                                INSERT IGNORE INTO tirages_keno_archive (
                                    date_tirage, heure_tirage,
                                    numero_1, numero_2, numero_3, numero_4, numero_5,
                                    numero_6, numero_7, numero_8, numero_9, numero_10,
                                    numero_11, numero_12, numero_13, numero_14, numero_15,
                                    numero_16, numero_17, numero_18, numero_19, numero_20,
                                    multiplicateur, joker, created_at, migrated_at
                                ) VALUES (
                                    :date_tirage, :heure_tirage,
                                    :num1, :num2, :num3, :num4, :num5,
                                    :num6, :num7, :num8, :num9, :num10,
                                    :num11, :num12, :num13, :num14, :num15,
                                    :num16, :num17, :num18, :num19, :num20,
                                    :multiplicateur, :joker, :created_at, :migrated_at
                                )
                            """), {
                                'date_tirage': row['date_tirage'],
                                'heure_tirage': row.get('heure_tirage'),
                                'num1': row['numero_1'], 'num2': row['numero_2'],
                                'num3': row['numero_3'], 'num4': row['numero_4'],
                                'num5': row['numero_5'], 'num6': row['numero_6'],
                                'num7': row['numero_7'], 'num8': row['numero_8'],
                                'num9': row['numero_9'], 'num10': row['numero_10'],
                                'num11': row['numero_11'], 'num12': row['numero_12'],
                                'num13': row['numero_13'], 'num14': row['numero_14'],
                                'num15': row['numero_15'], 'num16': row['numero_16'],
                                'num17': row['numero_17'], 'num18': row['numero_18'],
                                'num19': row['numero_19'], 'num20': row['numero_20'],
                                'multiplicateur': row.get('multiplicateur'),
                                'joker': row.get('joker'),
                                'created_at': row.get('created_at'),
                                'migrated_at': datetime.now()
                            })
                        except Exception as e:
                            logger.warning(f"Erreur lors de l'insertion d'un tirage: {e}")
                            continue
                    
                    conn.commit()
            
            # Récupérer les tirages 2025
            logger.info("Récupération des tirages 2025...")
            df_2025 = pd.read_sql("""
                SELECT * FROM tirages_keno_2025
                ORDER BY date_tirage DESC
            """, pg_engine)
            
            logger.info(f"{len(df_2025)} tirages 2025 trouvés")
            
            # Insérer dans MySQL
            if not df_2025.empty:
                with self.engine.connect() as conn:
                    for _, row in df_2025.iterrows():
                        try:
                            conn.execute(text("""
                                INSERT IGNORE INTO tirages_keno_2025 (
                                    date_tirage, heure_tirage,
                                    numero_1, numero_2, numero_3, numero_4, numero_5,
                                    numero_6, numero_7, numero_8, numero_9, numero_10,
                                    numero_11, numero_12, numero_13, numero_14, numero_15,
                                    numero_16, multiplicateur, joker, created_at, version
                                ) VALUES (
                                    :date_tirage, :heure_tirage,
                                    :num1, :num2, :num3, :num4, :num5,
                                    :num6, :num7, :num8, :num9, :num10,
                                    :num11, :num12, :num13, :num14, :num15,
                                    :num16, :multiplicateur, :joker, :created_at, :version
                                )
                            """), {
                                'date_tirage': row['date_tirage'],
                                'heure_tirage': row.get('heure_tirage'),
                                'num1': row['numero_1'], 'num2': row['numero_2'],
                                'num3': row['numero_3'], 'num4': row['numero_4'],
                                'num5': row['numero_5'], 'num6': row['numero_6'],
                                'num7': row['numero_7'], 'num8': row['numero_8'],
                                'num9': row['numero_9'], 'num10': row['numero_10'],
                                'num11': row['numero_11'], 'num12': row['numero_12'],
                                'num13': row['numero_13'], 'num14': row['numero_14'],
                                'num15': row['numero_15'], 'num16': row['numero_16'],
                                'multiplicateur': row.get('multiplicateur'),
                                'joker': row.get('joker'),
                                'created_at': row.get('created_at'),
                                'version': row.get('version', '2025')
                            })
                        except Exception as e:
                            logger.warning(f"Erreur lors de l'insertion d'un tirage 2025: {e}")
                            continue
                    
                    conn.commit()
            
            logger.info("✅ Migration des données terminée avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la migration: {e}")
            return False
    
    def run_migration(self, dry_run=False, from_postgresql=None):
        """
        Exécute la migration complète
        
        Args:
            dry_run: Si True, simule la migration sans appliquer les changements
            from_postgresql: URL PostgreSQL source pour migration (optionnel)
        """
        logger.info("=" * 60)
        logger.info("DÉBUT DE LA MIGRATION MYSQL KENO 2025")
        logger.info("=" * 60)
        
        if dry_run:
            logger.warning("⚠️  MODE DRY RUN - Aucun changement ne sera appliqué")
        
        try:
            # 1. Créer les tables depuis le schéma
            if not dry_run:
                self.create_tables_from_schema()
            
            # 2. Migrer depuis PostgreSQL si demandé
            if from_postgresql and not dry_run:
                self.migrate_from_postgresql(from_postgresql)
            
            logger.info("=" * 60)
            logger.info("✅ MIGRATION MYSQL TERMINÉE AVEC SUCCÈS")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la migration: {e}")
            return False


def main():
    """Fonction principale du script de migration MySQL"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migration MySQL Keno 2025")
    parser.add_argument('--dry-run', action='store_true',
                       help='Simule la migration sans appliquer les changements')
    parser.add_argument('--database-url', type=str,
                       help='URL de connexion MySQL (override DATABASE_URL)')
    parser.add_argument('--from-postgresql', type=str,
                       help='URL PostgreSQL source pour migration des données')
    
    args = parser.parse_args()
    
    try:
        migrator = KenoMySQLMigrator(database_url=args.database_url)
        success = migrator.run_migration(
            dry_run=args.dry_run,
            from_postgresql=args.from_postgresql
        )
        
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

