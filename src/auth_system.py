import os
import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
import uuid

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthSystem:
    """Système d'authentification PostgreSQL ONLY (fallback JSON supprimé)"""
    
    def __init__(self):
        self.database_url = os.environ.get(
            "DATABASE_URL", 
            "postgresql://kenos_user:qYGSudoftPvnoxaT9Seh5IP4itP1kK0a@dpg-d1umeoer433s73eu3d7g-a.frankfurt-postgres.render.com/kenos_vs92"
        )
        self.use_postgresql = True
    
    def _test_postgresql_connection(self):
        """Connexion PostgreSQL obligatoire : lève une erreur si la connexion échoue"""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(self.database_url)
            self._check_postgresql_structure(conn)
            conn.close()
            self.use_postgresql = True
        except Exception as e:
            raise RuntimeError(f"Connexion PostgreSQL obligatoire échouée : {e}")
            
            # Vérifier la structure de la table
            self._check_postgresql_structure(conn)
            
            conn.close()
            self.use_postgresql = True
            self.use_json_fallback = False
            
        except Exception as e:
            logger.error(f"Erreur PostgreSQL: {e}")
        logger.info("Passage en mode JSON fallback")
        self.use_postgresql = False
        self.use_json_fallback = True
    
    def _check_postgresql_structure(self, conn):
        """Vérifier et créer la structure de la table users avec le nouveau schéma corrigé"""
        try:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Supprimer la table existante et recréer avec la nouvelle structure
            cursor.execute("""
                DROP TABLE IF EXISTS public.users CASCADE;
                CREATE TABLE IF NOT EXISTS public.users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    is_admin BOOLEAN DEFAULT FALSE,
                    is_moderator BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_users_username ON public.users(username);
                CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
                CREATE INDEX IF NOT EXISTS idx_users_active ON public.users(is_active);
            """)
            conn.commit()
            logger.info("Table 'users' créée avec succès avec structure corrigée")
            
            cursor.close()
            
        except Exception as e:
            logger.error(f"Erreur structure PostgreSQL: {e}")
    
    def _hash_password(self, password: str) -> str:
        """Retourner le mot de passe en clair (pas de hash, non sécurisé)"""
        return password

    
    def _verify_password(self, password: str, password_db: str) -> bool:
        """Vérifier le mot de passe en clair (non sécurisé)"""
        return password == password_db

    
    def create_user(self, user_data: Dict[str, Any]) -> Optional[str]:
        """Créer un nouvel utilisateur"""
        try:
            username = user_data['username']
            email = user_data['email']
            password = user_data['password']
            is_admin = user_data.get('is_admin', False)
            is_moderator = user_data.get('is_moderator', False)
            
            password = self._hash_password(password)
            user_id = str(uuid.uuid4())
            
            if self.use_postgresql:
                return self._create_user_postgresql(user_id, username, email, password, is_admin, is_moderator)
            else:
                return self._create_user_json(user_id, username, email, password, is_admin, is_moderator)
                
        except Exception as e:
            logger.error(f"Erreur création utilisateur: {e}")
            return None
    
    def _create_user_postgresql(self, user_id: str, username: str, email: str, password: str, is_admin: bool, is_moderator: bool) -> Optional[str]:
        """Créer un utilisateur dans PostgreSQL avec vérification unicité email"""
        try:
            import psycopg2
            from psycopg2.errors import UniqueViolation
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            
            # Vérifier l'unicité de l'email
            cursor.execute("SELECT COUNT(*) FROM users WHERE email = %s", (email,))
            email_exists = cursor.fetchone()[0] > 0
            
            if email_exists:
                cursor.close()
                conn.close()
                logger.error(f"Email déjà utilisé: {email}")
                return None
            
            # Vérifier l'unicité du username
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = %s", (username,))
            username_exists = cursor.fetchone()[0] > 0
            
            if username_exists:
                cursor.close()
                conn.close()
                logger.error(f"Username déjà utilisé: {username}")
                return None
            
            cursor.execute("""
                INSERT INTO users (username, email, password, is_admin, is_moderator)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """, (username, email, password, is_admin, is_moderator))
            
            user_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Utilisateur PostgreSQL créé: {username}")
            return str(user_id)
            
        except Exception as e:
            logger.error(f"Erreur création PostgreSQL: {e}")
            return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authentifier un utilisateur"""
        try:
            if self.use_postgresql:
                return self._authenticate_postgresql(username, password)
            else:
                return self._authenticate_json(username, password)
                
        except Exception as e:
            logger.error(f"Erreur authentification: {e}")
            return None
    
    def _authenticate_postgresql(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authentifier avec PostgreSQL"""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT id, username, email, password, is_admin, is_moderator
                FROM users WHERE username = %s
            """, (username,))
            
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if user and self._verify_password(password, user['password']):
                logger.info(f"Authentification PostgreSQL réussie: {username}")
                return {
                    'id': str(user['id']),
                    'username': user['username'],
                    'email': user['email'],
                    'is_admin': user['is_admin'],
                    'is_moderator': user['is_moderator']
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur authentification PostgreSQL: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Obtenir un utilisateur par nom d'utilisateur"""
        try:
            if self.use_postgresql:
                return self._get_user_postgresql(username)
            else:
                return self._get_user_json(username)
                
        except Exception as e:
            logger.error(f"Erreur récupération utilisateur: {e}")
            return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Obtenir un utilisateur par id (PostgreSQL only)"""
        try:
            if self.use_postgresql:
                import psycopg2
                from psycopg2.extras import RealDictCursor
                conn = psycopg2.connect(self.database_url)
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("""
                    SELECT id, username, email, password, is_admin, is_moderator, is_active, created_at, updated_at, last_active
                    FROM users WHERE id = %s
                """, (user_id,))
                user = cursor.fetchone()
                cursor.close()
                conn.close()
                if user:
                    return dict(user)
                return None
            else:
                return None
        except Exception as e:
            logger.error(f"Erreur récupération utilisateur par id: {e}")
            return None


    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Obtenir un utilisateur par email"""
        try:
            if self.use_postgresql:
                return self._get_user_by_email_postgresql(email)
            else:
                return self._get_user_by_email_json(email)
                
        except Exception as e:
            logger.error(f"Erreur récupération utilisateur par email: {e}")
            return None
    
    def _get_user_postgresql(self, username: str) -> Optional[Dict[str, Any]]:
        """Obtenir un utilisateur PostgreSQL"""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT id, username, email, is_admin, is_moderator, is_active, created_at, updated_at, last_active
                FROM users WHERE username = %s
            """, (username,))
            
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if user:
                return dict(user)
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur récupération PostgreSQL: {e}")
            return None

    def _get_user_by_email_postgresql(self, email: str) -> Optional[Dict[str, Any]]:
        """Obtenir un utilisateur PostgreSQL par email"""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT id, username, email, password, is_admin, is_moderator, created_at, updated_at, last_login, is_active
                FROM users WHERE email = %s
            """, (email,))
            
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if user:
                return {
                    'id': str(user['id']),
                    'username': user['username'],
                    'email': user['email'],
                    'is_admin': user['is_admin'],
                    'is_moderator': user['is_moderator']
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur récupération PostgreSQL par email: {e}")
            return None
    
    # Méthode supprimée : fallback JSON désactivé
        """Obtenir un utilisateur JSON"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for user in data['users']:
                if user['username'] == username:
                    return {
                        'id': user['id'],
                        'username': user['username'],
                        'email': user['email'],
                        'is_admin': user['is_admin'],
                        'is_moderator': user['is_moderator']
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur récupération JSON: {e}")
            return None

    # Méthode supprimée : fallback JSON désactivé
        """Obtenir un utilisateur JSON par email"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for user in data['users']:
                if user['email'] == email:
                    return {
                        'id': user['id'],
                        'username': user['username'],
                        'email': user['email'],
                        'is_admin': user['is_admin'],
                        'is_moderator': user['is_moderator']
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur récupération JSON par email: {e}")
            return None
    
    def get_all_users(self) -> list:
        """Obtenir tous les utilisateurs (PostgreSQL only)"""
        try:
            return self._get_all_users_postgresql()
        except Exception as e:
            logger.error(f"Erreur récupération tous les utilisateurs: {e}")
            return []
    
    def _get_all_users_postgresql(self) -> list:
        """Obtenir tous les utilisateurs PostgreSQL"""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT id, username, email, is_admin, is_moderator, created_at
                FROM users ORDER BY created_at DESC
            """)
            
            users = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return [dict(user) for user in users]
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération tous PostgreSQL: {e}")
            return []
    
    # Méthode supprimée : fallback JSON désactivé
        """Obtenir tous les utilisateurs JSON"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data['users']
            
        except Exception as e:
            logger.error(f"Erreur récupération tous JSON: {e}")
            return []
