"""
Script pour auditer l'intégration des modèles ML avec le reste du schéma de la base de données.
"""
import os
import sys
import json
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

def get_database_connection():
    """Établit une connexion à la base de données."""
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ La variable d'environnement DATABASE_URL n'est pas définie")
        sys.exit(1)
        
    try:
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"❌ Erreur de connexion à la base de données: {e}")
        sys.exit(1)

def check_table_relations(conn, table_name):
    """Vérifie les relations d'une table avec les autres tables."""
    with conn.cursor() as cur:
        # Récupérer les contraintes de clé étrangère
        cur.execute("""
            SELECT
                tc.constraint_name,
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM
                information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                  AND ccu.table_schema = tc.table_schema
            WHERE
                tc.constraint_type = 'FOREIGN KEY'
                AND (tc.table_name = %s OR ccu.table_name = %s)
        """, (table_name, table_name))
        
        relations = cur.fetchall()
        return relations

def check_ml_models_integration():
    """Vérifie l'intégration de la table ml_models avec le reste du schéma."""
    print("🔍 Audit de l'intégration des modèles ML...\n")
    
    conn = get_database_connection()
    
    try:
        # 1. Vérifier les relations directes avec ml_models
        print("=== RELATIONS DIRECTES AVEC ML_MODELS ===")
        relations = check_table_relations(conn, 'ml_models')
        
        if not relations:
            print("ℹ️ Aucune relation directe trouvée pour la table ml_models")
        else:
            for rel in relations:
                print(f"- {rel[1]}.{rel[2]} → {rel[3]}.{rel[4]}")
        
        # 2. Vérifier les tables qui devraient potentiellement référencer ml_models
        print("\n=== TABLES POTENTIELLES POUR L'INTÉGRATION ===")
        tables_to_check = ['predictions', 'user_predictions', 'method_stats', 'analysis_results']
        
        for table in tables_to_check:
            relations = check_table_relations(conn, table)
            print(f"\nRelations pour {table}:")
            
            if not relations:
                print(f"  ℹ️ Aucune relation trouvée pour {table}")
            else:
                for rel in relations:
                    print(f"  - {rel[1]}.{rel[2]} → {rel[3]}.{rel[4]}")
        
        # 3. Vérifier la structure de la table ml_models
        print("\n=== STRUCTURE DE LA TABLE ML_MODELS ===")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'ml_models'
                ORDER BY ordinal_position
            """)
            
            print("\nColonnes de ml_models:")
            print("-" * 50)
            print(f"{'Colonne':<20} {'Type':<20} {'Nullable'}")
            print("-" * 50)
            for col in cur.fetchall():
                print(f"{col[0]:<20} {col[1]:<20} {col[2]}")
        
        # 4. Vérifier s'il y a des modèles enregistrés
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM ml_models")
            count = cur.fetchone()[0]
            print(f"\nNombre de modèles enregistrés: {count}")
            
            if count > 0:
                cur.execute("""
                    SELECT id, model_name, model_type, created_at, trained_at 
                    FROM ml_models 
                    ORDER BY created_at DESC 
                    LIMIT 5
                """)
                
                print("\nDerniers modèles enregistrés:")
                print("-" * 100)
                print(f"{'ID':<5} {'Nom':<20} {'Type':<30} {'Créé le':<25} {'Entraîné le'}")
                print("-" * 100)
                for row in cur.fetchall():
                    print(f"{row[0]:<5} {row[1]:<20} {row[2]:<30} {str(row[3]):<25} {str(row[4])}")
        
        # 5. Vérifier les opportunités d'intégration manquantes
        print("\n=== OPPORTUNITÉS D'AMÉLIORATION ===")
        improvements = [
            "1. Ajouter une colonne 'model_id' dans la table 'predictions' pour suivre quel modèle a généré chaque prédiction",
            "2. Créer une table 'model_metrics' pour stocker les métriques détaillées des modèles au fil du temps",
            "3. Ajouter une colonne 'model_version' dans 'ml_models' pour gérer différentes versions d'un même modèle",
            "4. Créer une table 'model_training_runs' pour suivre les sessions d'entraînement",
            "5. Ajouter une colonne 'is_production' dans 'ml_models' pour marquer les modèles en production"
        ]
        
        print("\nSuggestions d'amélioration de l'intégration ML:")
        for imp in improvements:
            print(f"- {imp}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    check_ml_models_integration()
    print("\n✅ Audit terminé")
