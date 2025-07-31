"""
Script de diagnostic de base de données ultra-simplifié
pour éviter les problèmes d'encodage sous Windows.
"""
import os
import sys
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

def main():
    # Charger les variables d'environnement
    env_path = Path(__file__).parent.parent / '.env'
    if not env_path.exists():
        print("ERREUR: Fichier .env introuvable")
        return 1
    
    load_dotenv(dotenv_path=env_path)
    
    # Récupérer l'URL de la base de données
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("ERREUR: DATABASE_URL non définie")
        return 1
    
    # Masquer le mot de passe pour l'affichage
    db_display = db_url
    if '@' in db_display:
        parts = db_display.split('@')
        if '//' in parts[0]:
            protocol = parts[0].split('//')[0] + '//'
            credentials = parts[0].split('//')[1]
            if ':' in credentials:
                user = credentials.split(':')[0]
                db_display = f"{protocol}{user}:********@{'@'.join(parts[1:])}"
    
    print(f"\n=== CONFIGURATION DE LA BASE DE DONNÉES ===\n")
    print(f"URL de la base de données: {db_display}")
    
    try:
        # Connexion à la base de données
        print("\nConnexion à la base de données...")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Vérifier la version de PostgreSQL
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"\n=== VERSION DE POSTGRESQL ===\n{version}")
        
        # Lister les tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        print(f"\n=== TABLES DISPONIBLES ({len(tables)}) ===")
        for table in tables:
            print(f"- {table}")
        
        # Vérifier la table users
        if 'users' in tables:
            print("\n=== TABLE USERS ===")
            
            # Colonnes
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users'
            """)
            
            print("\nColonnes:")
            for col_name, col_type in cursor.fetchall():
                print(f"- {col_name}: {col_type}")
            
            # Nombre d'utilisateurs
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            print(f"\nNombre total d'utilisateurs: {user_count}")
            
            # Afficher quelques utilisateurs
            if user_count > 0:
                cursor.execute("""
                    SELECT id, username, email, is_admin, is_active 
                    FROM users 
                    ORDER BY id 
                    LIMIT 3
                """)
                
                print("\nQuelques utilisateurs:")
                for user in cursor.fetchall():
                    user_id, username, email, is_admin, is_active = user
                    print(f"- ID: {user_id}, {username} ({email})")
                    print(f"  Admin: {is_admin}, Actif: {is_active}")
        
        # Vérifier les autres tables importantes
        for table in ['tirages', 'predictions', 'user_predictions']:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"\n- {table}: {count} enregistrements")
        
        cursor.close()
        conn.close()
        
        print("\n=== DIAGNOSTIC TERMINÉ AVEC SUCCÈS ===")
        return 0
        
    except Exception as e:
        print(f"\n=== ERREUR ===\n")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {str(e)}")
        
        # Détails supplémentaires pour les erreurs de connexion
        if isinstance(e, psycopg2.OperationalError):
            print("\nDétails de l'erreur de connexion:")
            print(f"- Hôte: {e.pgconn.host if hasattr(e, 'pgconn') else 'Inconnu'}")
            print(f"- Port: {e.pgconn.port if hasattr(e, 'pgconn') else 'Inconnu'}")
            print(f"- Base de données: {e.pgconn.dbname if hasattr(e, 'pgconn') else 'Inconnue'}")
            print(f"- Utilisateur: {e.pgconn.user if hasattr(e, 'pgconn') else 'Inconnu'}")
            print("\nVérifiez que:")
            print("1. Le serveur PostgreSQL est en cours d'exécution")
            print("2. Les informations de connexion dans .env sont correctes")
            print("3. Le pare-feu autorise les connexions sur le port PostgreSQL (par défaut 5432)")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())
