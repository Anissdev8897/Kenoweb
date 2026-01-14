"""
Script pour appliquer les améliorations d'intégration des modèles ML.
Ce script exécute le fichier SQL d'amélioration de l'intégration ML.
"""
import os
import sys
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

def load_sql_file(file_path):
    """Charge le contenu d'un fichier SQL."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du fichier SQL: {e}")
        return None

def execute_sql_script(sql_content):
    """Exécute un script SQL sur la base de données."""
    # Charger les variables d'environnement
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ La variable d'environnement DATABASE_URL n'est pas définie")
        return False
    
    try:
        # Se connecter à la base de données
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("✅ Connexion à la base de données établie")
        
        # Exécuter le script SQL
        print("🔧 Exécution du script SQL d'amélioration de l'intégration ML...")
        cur.execute(sql_content)
        
        # Récupérer et afficher les résultats de vérification
        print("\n📋 Vérification des modifications appliquées :")
        print("-" * 80)
        cur.execute("""
            SELECT 
                table_name, 
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
        """)
        
        # Afficher les résultats
        print(f"\n{'Table':<20} {'Colonne':<20} {'Type':<20} {'Nullable'}")
        print("-" * 70)
        for row in cur.fetchall():
            print(f"{row[0]:<20} {row[1]:<20} {row[2]:<20} {row[3]}")
        
        # Vérifier si la colonne model_id a été ajoutée à predictions
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'predictions' AND column_name = 'model_id';
        """)
        
        if cur.fetchone():
            print("\n✅ La colonne 'model_id' a été ajoutée à la table 'predictions'")
        else:
            print("\n❌ La colonne 'model_id' n'a pas pu être ajoutée à la table 'predictions'")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de l'exécution du script SQL: {e}")
        return False
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

def main():
    print("=== AMÉLIORATION DE L'INTÉGRATION DES MODÈLES ML ===\n")
    
    # Chemin vers le fichier SQL
    sql_file = Path(__file__).parent / 'improve_ml_integration.sql'
    
    # Vérifier que le fichier existe
    if not sql_file.exists():
        print(f"❌ Le fichier {sql_file} est introuvable")
        return False
    
    # Charger le contenu du fichier SQL
    sql_content = load_sql_file(sql_file)
    if not sql_content:
        return False
    
    # Exécuter le script SQL
    success = execute_sql_script(sql_content)
    
    if success:
        print("\n✅ Améliorations d'intégration ML appliquées avec succès !")
    else:
        print("\n❌ Échec de l'application des améliorations d'intégration ML")
    
    return success

if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
