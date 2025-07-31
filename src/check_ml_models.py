"""
Script pour vérifier le contenu de la table ml_models
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

# Charger les variables d'environnement
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Connexion à la base de données
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

try:
    # Vérifier le nombre d'entrées dans ml_models
    cur.execute('SELECT COUNT(*) FROM ml_models')
    count = cur.fetchone()[0]
    print(f'Nombre de modèles ML: {count}')
    
    # Afficher la structure de la table
    print('\nStructure de la table ml_models:')
    cur.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = 'ml_models'
        ORDER BY ordinal_position
    """)
    
    print('\nColonnes:')
    for col in cur.fetchall():
        print(f"- {col[0]}: {col[1]} (Nullable: {col[2]}, Default: {col[3]})")
    
    # Si la table n'est pas vide, afficher un aperçu
    if count > 0:
        print('\nAperçu des modèles ML:')
        cur.execute('SELECT * FROM ml_models LIMIT 3')
        for row in cur.fetchall():
            print(f"\nModèle: {row[0] if row else 'N/A'}")
            print(f"Détails: {row}")
    
    # Vérifier s'il y a des entrées dans la table model_metrics
    try:
        cur.execute('SELECT COUNT(*) FROM model_metrics')
        metrics_count = cur.fetchone()[0]
        print(f'\nNombre de métriques de modèles: {metrics_count}')
    except:
        print('\nLa table model_metrics n\'existe pas')
        
except Exception as e:
    print(f'\nErreur lors de la vérification des modèles ML: {e}')

finally:
    cur.close()
    conn.close()
