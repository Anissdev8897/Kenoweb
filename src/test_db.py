import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def main():
    # Charger les variables d'environnement
    env_path = Path(__file__).parent.parent / '.env'
    print(f"Chargement du fichier .env depuis: {env_path}")
    
    if not env_path.exists():
        print("Erreur: Fichier .env non trouvé")
        return 1
        
    load_dotenv(dotenv_path=env_path)
    
    # Afficher les variables d'environnement (sans les valeurs sensibles)
    print("\nVariables d'environnement chargées:")
    for key in os.environ:
        if 'PASS' in key or 'SECRET' in key or 'KEY' in key or 'TOKEN' in key:
            print(f"- {key}: ********")
        else:
            print(f"- {key}: {os.environ[key]}")
    
    # Tester la connexion à la base de données
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            print("\nErreur: DATABASE_URL non définie dans .env")
            return 1
            
        print(f"\nTentative de connexion à la base de données...")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Tester une requête simple
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        print(f"\nConnexion réussie à PostgreSQL!")
        print(f"Version du serveur: {version['version']}")
        
        # Lister les tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        tables = [row['table_name'] for row in cursor.fetchall()]
        print(f"\nTables trouvées: {', '.join(tables) if tables else 'Aucune table'}")
        
        # Afficher les utilisateurs si la table users existe
        if 'users' in tables:
            cursor.execute("SELECT COUNT(*) as count FROM users")
            count = cursor.fetchone()['count']
            print(f"\nNombre d'utilisateurs: {count}")
            
            if count > 0:
                cursor.execute("SELECT id, username, email, is_admin, is_active FROM users ORDER BY id LIMIT 3")
                print("\nQuelques utilisateurs:")
                for user in cursor.fetchall():
                    print(f"- ID: {user['id']}, {user['username']} ({user['email']}) - Admin: {user['is_admin']}, Actif: {user['is_active']}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\nERREUR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
