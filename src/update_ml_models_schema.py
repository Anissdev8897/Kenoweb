"""
Script pour mettre à jour le schéma de la table ml_models
et ajouter les colonnes manquantes (model_binary, metadata).
"""
import os
import sys
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

def main():
    try:
        # Charger les variables d'environnement
        env_path = Path(__file__).parent.parent / '.env'
        load_dotenv(dotenv_path=env_path)
        
        # Connexion à la base de données
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        conn.autocommit = True
        cur = conn.cursor()
        
        # Vérifier si les colonnes existent déjà
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'ml_models' 
            AND column_name IN ('model_binary', 'metadata')
        """)
        
        existing_columns = [row[0] for row in cur.fetchall()]
        
        # Préparer les requêtes d'ajout
        alter_queries = []
        
        if 'model_binary' not in existing_columns:
            alter_queries.append("ADD COLUMN IF NOT EXISTS model_binary BYTEA")
        
        if 'metadata' not in existing_columns:
            alter_queries.append("ADD COLUMN IF NOT EXISTS metadata JSONB")
        
        # Exécuter les requêtes si nécessaire
        if alter_queries:
            alter_sql = f"ALTER TABLE ml_models {', '.join(alter_queries)}"
            print(f"Exécution de la requête SQL: {alter_sql}")
            
            cur.execute(alter_sql)
            print("✅ La table ml_models a été mise à jour avec succès.")
            
            # Afficher la nouvelle structure
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'ml_models'
                ORDER BY ordinal_position
            """)
            
            print("\nNouvelle structure de la table ml_models:")
            print("-" * 60)
            print(f"{'Colonne':<20} {'Type':<20} {'Nullable'}")
            print("-" * 60)
            
            for col in cur.fetchall():
                print(f"{col[0]:<20} {col[1]:<20} {col[2]}")
        else:
            print("✅ La table ml_models est déjà à jour. Aucune modification nécessaire.")
        
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour de la table ml_models: {e}")
        sys.exit(1)
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("=== Mise à jour du schéma de la table ml_models ===\n")
    main()
    print("\n=== Opération terminée ===")
