"""
Script simple pour vérifier la connexion à la base de données PostgreSQL
et afficher des informations de base sur la structure.
"""
import os
import sys
import json
from pathlib import Path
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

def print_section(title, width=80):
    """Affiche un titre de section formaté."""
    print("\n" + "=" * width)
    print(f" {title.upper()} ".center(width, '='))
    print("=" * width)

def safe_print_dict(data, indent=2):
    """Affiche un dictionnaire de manière sécurisée pour éviter les problèmes d'encodage."""
    try:
        print(json.dumps(data, indent=indent, ensure_ascii=False))
    except (TypeError, ValueError):
        # Si le JSON échoue, afficher une représentation plus simple
        for key, value in data.items():
            print(f"{key}: {value}")

def main():
    # Configuration de l'encodage
    if sys.platform == 'win32':
        import io
        import sys
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    # Charger les variables d'environnement
    env_path = Path(__file__).parent.parent / '.env'
    if not env_path.exists():
        print(f"ERREUR: Fichier .env introuvable à l'emplacement: {env_path}")
        return 1
    
    load_dotenv(dotenv_path=env_path)
    
    # Récupérer l'URL de la base de données
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("ERREUR: La variable d'environnement DATABASE_URL n'est pas définie")
        return 1
    
    # Masquer le mot de passe dans les logs
    db_display = db_url
    if '@' in db_display:
        parts = db_display.split('@')
        if '//' in parts[0]:
            protocol = parts[0].split('//')[0] + '//'
            credentials = parts[0].split('//')[1]
            if ':' in credentials:
                user = credentials.split(':')[0]
                db_display = f"{protocol}{user}:********@{'@'.join(parts[1:])}"
    
    print_section("Configuration de la base de données")
    print(f"URL de la base de données: {db_display}")
    
    try:
        # Connexion à la base de données
        print("\nConnexion à la base de données...")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Vérifier la version de PostgreSQL
        cursor.execute("SELECT version() AS version")
        db_version = cursor.fetchone()
        print_section("Informations sur le serveur")
        safe_print_dict(dict(db_version))
        
        # Lister les tables
        cursor.execute("""
            SELECT table_name, 
                   pg_size_pretty(pg_total_relation_size(table_name)) as size,
                   pg_total_relation_size(table_name) as size_bytes
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY pg_total_relation_size(table_name) DESC
        """)
        
        tables = cursor.fetchall()
        print_section("Tables de la base de données")
        print(f"Nombre de tables trouvées: {len(tables)}")
        
        for table in tables:
            print(f"\nTable: {table['table_name']} (Taille: {table['size']})")
            
            # Afficher les colonnes de la table
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table['table_name'],))
            
            columns = cursor.fetchall()
            print(f"Colonnes ({len(columns)}):")
            for col in columns:
                print(f"  - {col['column_name']}: {col['data_type']} "
                      f"({'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'}) "
                      f"{f'DEFAULT {col['column_default']}' if col['column_default'] else ''}")
            
            # Afficher le nombre de lignes pour les petites tables
            if table['size_bytes'] < 10 * 1024 * 1024:  # Moins de 10 Mo
                try:
                    cursor.execute(sql.SQL("SELECT COUNT(*) as count FROM {}").format(
                        sql.Identifier(table['table_name'])))
                    count = cursor.fetchone()['count']
                    print(f"  Nombre d'enregistrements: {count:,}")
                    
                    # Afficher un échantillon pour la table users
                    if table['table_name'] == 'users' and count > 0:
                        cursor.execute("""
                            SELECT id, username, email, is_admin, is_active, 
                                   created_at, last_active
                            FROM users 
                            ORDER BY id 
                            LIMIT 3
                        """)
                        users = cursor.fetchall()
                        print("  Exemple d'utilisateurs:")
                        for user in users:
                            print(f"    - ID: {user['id']}, {user['username']} ({user['email']}) "
                                  f"Admin: {user['is_admin']}, Actif: {user['is_active']}")
                except Exception as e:
                    print(f"  Impossible de compter les enregistrements: {str(e)}")
        
        # Vérifier les connexions actives
        cursor.execute("""
            SELECT 
                pid, 
                usename, 
                application_name, 
                client_addr, 
                state, 
                query_start,
                now() - query_start as query_duration,
                query
            FROM pg_stat_activity 
            WHERE state = 'active' 
            ORDER BY query_start
        """)
        
        active_connections = cursor.fetchall()
        if active_connections:
            print_section("Connexions actives")
            for conn_info in active_connections:
                print(f"\nConnexion {conn_info['pid']}:")
                print(f"  Utilisateur: {conn_info['usename']}")
                print(f"  Application: {conn_info['application_name']}")
                print(f"  Adresse: {conn_info['client_addr']}")
                print(f"  Début: {conn_info['query_start']} (il y a {conn_info['query_duration']})")
                print(f"  Requête: {conn_info['query'][:100]}...")
        
        cursor.close()
        conn.close()
        
        print_section("Vérification terminée avec succès")
        return 0
        
    except Exception as e:
        import traceback
        print_section("ERREUR")
        print(f"Erreur lors de la connexion à la base de données: {str(e)}\n")
        print("Détails de l'erreur:")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
