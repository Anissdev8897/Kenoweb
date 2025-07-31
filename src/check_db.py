import os
import sys
import io
import locale
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Configurer l'encodage de la sortie standard pour Windows
if sys.platform == 'win32':
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    # Configurer la locale pour éviter les problèmes d'encodage
    if os.name == 'nt':
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleCP(65001)
        kernel32.SetConsoleOutputCP(65001)

# Fonction pour afficher du texte de manière sécurisée
def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # Si l'encodage échoue, essayer avec une méthode plus simple
        text = ' '.join(str(arg) for arg in args)
        print(text.encode('ascii', errors='replace').decode('ascii'), **kwargs)

# Charger les variables d'environnement depuis le fichier .env
env_path = Path(__file__).parent.parent / '.env'
safe_print(f"Chargement des variables d'environnement depuis: {env_path}")

if not env_path.exists():
    safe_print(f"Erreur: Le fichier .env n'existe pas à l'emplacement: {env_path}")
    exit(1)

# Charger les variables d'environnement
load_dotenv(dotenv_path=env_path)

# Récupérer l'URL de la base de données depuis les variables d'environnement
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    safe_print("Erreur: La variable d'environnement DATABASE_URL n'est pas définie dans le fichier .env")
    exit(1)

# Afficher une version masquée de l'URL pour des raisons de sécurité
db_url_display = database_url
if '@' in db_url_display:
    # Masquer le mot de passe dans l'URL pour la journalisation
    parts = db_url_display.split('@')
    if '//' in parts[0]:
        protocol = parts[0].split('//')[0] + '//'
        credentials = parts[0].split('//')[1]
        if ':' in credentials:
            user = credentials.split(':')[0]
            db_url_display = f"{protocol}{user}:********@{'@'.join(parts[1:])}"

safe_print(f"Connexion à la base de données: {db_url_display}")

try:
    # Se connecter à la base de données
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Vérifier si la table users existe
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'users'
    """)
    
    users_table_exists = cursor.fetchone() is not None
    safe_print(f"La table 'users' existe: {users_table_exists}")
    
    if users_table_exists:
        # Afficher la structure de la table users
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)
        
        safe_print("\nStructure de la table 'users':")
        safe_print("-" * 60)
        safe_print(f"{'Colonne':<20} {'Type':<20} {'Nullable':<10} {'Default'}")
        safe_print("-" * 60)
        
        for col in cursor.fetchall():
            safe_print(f"{col['column_name']:<20} {col['data_type']:<20} {col['is_nullable']:<10} {col['column_default']}")
        
        # Compter le nombre d'utilisateurs
        cursor.execute("SELECT COUNT(*) as count FROM users")
        count = cursor.fetchone()['count']
        safe_print(f"\nNombre d'utilisateurs dans la table: {count}")
        
        # Afficher les premiers utilisateurs (sans les mots de passe)
        if count > 0:
            cursor.execute("SELECT id, username, email, is_admin, is_moderator, is_active FROM users ORDER BY id ASC LIMIT 5")
            users = cursor.fetchall()
            safe_print("\nQuelques utilisateurs (sans les mots de passe):")
            for user in users:
                safe_print(f"- ID: {user['id']}, {user['username']} ({user['email']}) - Admin: {user['is_admin']}, Modérateur: {user['is_moderator']}, Actif: {user['is_active']}")
    
    # Vérifier les autres tables
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    
    tables = [row['table_name'] for row in cursor.fetchall()]
    safe_print(f"\nTables dans la base de données: {', '.join(tables) if tables else 'Aucune table trouvée'}")
    
    # Afficher des informations supplémentaires sur chaque table
    if tables:
        safe_print("\nDétails des tables:")
        for table in tables:
            try:
                # Compter le nombre de lignes
                cursor.execute(f"SELECT COUNT(*) as count FROM \"{table}\"")
                count = cursor.fetchone()['count']
                
                # Obtenir les colonnes
                cursor.execute(f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = %s 
                    ORDER BY ordinal_position
                """, (table,))
                columns = [f"{col['column_name']} ({col['data_type']})" for col in cursor.fetchall()]
                
                safe_print(f"\nTable: {table} (lignes: {count})")
                safe_print(f"Colonnes: {', '.join(columns)}")
                
            except Exception as e:
                safe_print(f"  Erreur lors de la lecture de la table {table}: {str(e)[:100]}...")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    import traceback
    safe_print("\n" + "="*80)
    safe_print("ERREUR LORS DE LA CONNEXION À LA BASE DE DONNÉES")
    safe_print("="*80)
    safe_print(f"Type d'erreur: {type(e).__name__}")
    safe_print(f"Message d'erreur: {str(e)}")
    safe_print("\nStack trace:")
    traceback.print_exc(file=sys.stdout)
    
    # Afficher des informations supplémentaires sur la connexion
    safe_print("\nInformations de connexion:")
    safe_print(f"- Type de base de données: {'PostgreSQL' if 'psycopg2' in str(type(e)) else 'Inconnu'}")
    safe_print(f"- Module psycopg2 disponible: {'Oui' if 'psycopg2' in sys.modules else 'Non'}")
    
    # Vérifier si le module psycopg2 est correctement installé
    try:
        import psycopg2
        safe_print(f"- Version de psycopg2: {psycopg2.__version__ if hasattr(psycopg2, '__version__') else 'Inconnue'}")
    except Exception as pe:
        safe_print(f"- Erreur lors de l'import de psycopg2: {pe}")
    
    # Afficher les variables d'environnement pertinentes
    safe_print("\nVariables d'environnement:")
    for var in ['DATABASE_URL', 'PGHOST', 'PGPORT', 'PGDATABASE', 'PGUSER', 'PGPASSWORD']:
        if var in os.environ:
            value = os.environ[var]
            if 'PASS' in var or 'PWD' in var or 'PASSWORD' in var:
                value = '********' if value else '(vide)'
            safe_print(f"- {var}: {value}")
    
    safe_print("\nConseils de dépannage:")
    safe_print("1. Vérifiez que la base de données est en cours d'exécution et accessible")
    safe_print("2. Vérifiez que les identifiants dans DATABASE_URL sont corrects")
    safe_print("3. Vérifiez que l'utilisateur a les permissions nécessaires")
    safe_print("4. Vérifiez que le pare-feu autorise les connexions sur le port spécifié")
    safe_print("5. Pour les problèmes d'encodage, assurez-vous d'utiliser UTF-8 partout")
    safe_print("\nSi le problème persiste, contactez l'administrateur système avec ces informations.")
