"""
Script de validation de l'intégration des modèles ML dans le backend.
Vérifie que toutes les modifications ont été correctement appliquées et que les relations sont fonctionnelles.
"""
import os
import sys
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

def check_database_connection():
    """Vérifie la connexion à la base de données."""
    try:
        env_path = Path(__file__).parent.parent / '.env'
        load_dotenv(dotenv_path=env_path)
        
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            return False, "La variable d'environnement DATABASE_URL n'est pas définie"
            
        conn = psycopg2.connect(database_url)
        conn.close()
        return True, "Connexion à la base de données réussie"
    except Exception as e:
        return False, f"Erreur de connexion à la base de données: {e}"

def validate_ml_models_table():
    """Valide la structure de la table ml_models."""
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()
        
        # Vérifier les colonnes requises
        required_columns = [
            'id', 'model_name', 'model_type', 'model_binary', 'training_score',
            'test_score', 'r2_score', 'training_time_seconds', 'created_at',
            'trained_at', 'model_version', 'is_production', 'description', 'metadata'
        ]
        
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'ml_models'
        """)
        
        existing_columns = {row[0]: row[1] for row in cur.fetchall()}
        missing_columns = [col for col in required_columns if col not in existing_columns]
        
        if missing_columns:
            return False, f"Colonnes manquantes dans ml_models: {', '.join(missing_columns)}"
            
        # Vérifier les contraintes
        cur.execute("""
            SELECT conname, conkey, confkey
            FROM pg_constraint
            WHERE conrelid = 'ml_models'::regclass
        """)
        
        constraints = cur.fetchall()
        has_pk = any('pkey' in con[0] for con in constraints)
        
        if not has_pk:
            return False, "Pas de clé primaire sur la table ml_models"
            
        # Vérifier qu'il y a au moins un modèle
        cur.execute("SELECT COUNT(*) FROM ml_models")
        count = cur.fetchone()[0]
        
        if count == 0:
            return False, "Aucun modèle trouvé dans la table ml_models"
            
        return True, f"Structure de ml_models valide ({count} modèles trouvés)"
        
    except Exception as e:
        return False, f"Erreur lors de la validation de ml_models: {e}"
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

def validate_model_metrics_table():
    """Valide la structure de la table model_metrics."""
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()
        
        # Vérifier que la table existe
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'model_metrics'
            )
        """)
        
        if not cur.fetchone()[0]:
            return False, "La table model_metrics n'existe pas"
            
        # Vérifier les colonnes requises
        required_columns = {
            'id': 'integer',
            'model_id': 'integer',
            'metric_name': 'character varying',
            'metric_value': 'numeric',
            'created_at': 'timestamp with time zone',
            'metadata': 'jsonb'
        }
        
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'model_metrics'
        """)
        
        existing_columns = {row[0]: row[1] for row in cur.fetchall()}
        
        for col, col_type in required_columns.items():
            if col not in existing_columns:
                return False, f"Colonne manquante dans model_metrics: {col}"
            if existing_columns[col] != col_type:
                return False, f"Type incorrect pour la colonne {col} dans model_metrics: {existing_columns[col]} au lieu de {col_type}"
        
        # Vérifier la clé étrangère vers ml_models
        cur.execute("""
            SELECT 
                tc.constraint_name,
                kcu.column_name, 
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name 
            FROM 
                information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
            WHERE 
                tc.table_name = 'model_metrics'
                AND tc.constraint_type = 'FOREIGN KEY'
                AND ccu.table_name = 'ml_models'
        """)
        
        fk = cur.fetchone()
        if not fk:
            return False, "Clé étrangère manquante de model_metrics vers ml_models"
            
        return True, "Structure de model_metrics valide"
        
    except Exception as e:
        return False, f"Erreur lors de la validation de model_metrics: {e}"
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

def validate_training_runs_table():
    """Valide la structure de la table model_training_runs."""
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()
        
        # Vérifier que la table existe
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'model_training_runs'
            )
        """)
        
        if not cur.fetchone()[0]:
            return False, "La table model_training_runs n'existe pas"
            
        # Vérifier les colonnes requises
        required_columns = {
            'id': 'integer',
            'model_id': 'integer',
            'start_time': 'timestamp with time zone',
            'end_time': 'timestamp with time zone',
            'status': 'character varying',
            'training_params': 'jsonb',
            'metrics': 'jsonb',
            'error_message': 'text',
            'created_at': 'timestamp with time zone'
        }
        
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'model_training_runs'
        """)
        
        existing_columns = {row[0]: row[1] for row in cur.fetchall()}
        
        for col, col_type in required_columns.items():
            if col not in existing_columns:
                return False, f"Colonne manquante dans model_training_runs: {col}"
            if existing_columns[col] != col_type:
                return False, f"Type incorrect pour la colonne {col} dans model_training_runs: {existing_columns[col]} au lieu de {col_type}"
        
        # Vérifier la contrainte CHECK sur le statut
        cur.execute("""
            SELECT conname, pg_get_constraintdef(oid) as consrc
            FROM pg_constraint
            WHERE conrelid = 'model_training_runs'::regclass
            AND contype = 'c'
        """)
        
        has_status_check = False
        for conname, consrc in cur.fetchall():
            if 'status' in str(consrc) and any(s in str(consrc) for s in ["'started'", "'completed'", "'failed'"]):
                has_status_check = True
                break
                
        if not has_status_check:
            return False, "Contrainte CHECK manquante sur la colonne status de model_training_runs"
            
        return True, "Structure de model_training_runs valide"
        
    except Exception as e:
        return False, f"Erreur lors de la validation de model_training_runs: {e}"
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

def validate_predictions_table():
    """Valide la colonne model_id dans la table predictions."""
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()
        
        # Vérifier que la colonne model_id existe
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'predictions'
            AND column_name = 'model_id'
        """)
        
        if not cur.fetchone():
            return False, "La colonne model_id est manquante dans la table predictions"
            
        # Vérifier la clé étrangère vers ml_models
        cur.execute("""
            SELECT 
                tc.constraint_name,
                kcu.column_name, 
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name 
            FROM 
                information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
            WHERE 
                tc.table_name = 'predictions'
                AND tc.constraint_type = 'FOREIGN KEY'
                AND kcu.column_name = 'model_id'
                AND ccu.table_name = 'ml_models'
        """)
        
        fk = cur.fetchone()
        if not fk:
            return False, "Clé étrangère manquante de predictions.model_id vers ml_models.id"
            
        return True, "Colonne model_id valide dans predictions"
        
    except Exception as e:
        return False, f"Erreur lors de la validation de la table predictions: {e}"
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

def main():
    print("=== VALIDATION DE L'INTÉGRATION DES MODÈLES ML ===\n")
    
    # Vérifier la connexion à la base de données
    print("1. Vérification de la connexion à la base de données...")
    db_ok, db_msg = check_database_connection()
    print(f"   - {db_msg}")
    if not db_ok:
        print("\n❌ La validation a échoué. Veuillez corriger les erreurs et réessayer.")
        return False
    
    # Valider la table ml_models
    print("\n2. Validation de la table ml_models...")
    ml_models_ok, ml_models_msg = validate_ml_models_table()
    print(f"   - {ml_models_msg}")
    
    # Valider la table model_metrics
    print("\n3. Validation de la table model_metrics...")
    metrics_ok, metrics_msg = validate_model_metrics_table()
    print(f"   - {metrics_msg}")
    
    # Valider la table model_training_runs
    print("\n4. Validation de la table model_training_runs...")
    runs_ok, runs_msg = validate_training_runs_table()
    print(f"   - {runs_msg}")
    
    # Valider la colonne model_id dans predictions
    print("\n5. Validation de la colonne model_id dans predictions...")
    pred_ok, pred_msg = validate_predictions_table()
    print(f"   - {pred_msg}")
    
    # Afficher le résumé
    all_ok = all([db_ok, ml_models_ok, metrics_ok, runs_ok, pred_ok])
    
    print("\n=== RÉSULTAT DE LA VALIDATION ===")
    if all_ok:
        print("✅ Tous les tests d'intégration ML ont réussi !")
        print("   La base de données est correctement configurée pour l'utilisation des modèles ML.")
    else:
        print("❌ Certains tests ont échoué. Veuillez corriger les problèmes signalés ci-dessus.")
    
    return all_ok

if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
