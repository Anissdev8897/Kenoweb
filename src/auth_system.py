import os
import logging
import bcrypt
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import uuid
from functools import wraps
from flask import session, redirect, url_for, flash

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthSystem:
    """Système d'authentification PostgreSQL ONLY (fallback JSON supprimé)"""
    
    def __init__(self):
        # Utiliser uniquement la variable d'environnement, sans valeur par défaut
        self.database_url = os.environ.get("DATABASE_URL")
        if not self.database_url:
            logger.error("La variable d'environnement DATABASE_URL n'est pas définie")
            raise ValueError("La variable d'environnement DATABASE_URL est requise pour se connecter à la base de données")
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
    
    def _hash_password(self, password: str) -> Tuple[bytes, bytes]:
        """Hache le mot de passe avec bcrypt"""
        # Générer un sel et hacher le mot de passe
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed, salt
    
    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """Vérifie le mot de passe avec bcrypt"""
        if not password or not hashed_password:
            return False
        try:
            # Si le mot de passe haché est stocké comme chaîne, le convertir en bytes
            if isinstance(hashed_password, str):
                hashed_password = hashed_password.encode('utf-8')
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password)
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du mot de passe: {e}")
            return False

    
    def create_user(self, user_data: Dict[str, Any]) -> Optional[str]:
        """Créer un nouvel utilisateur"""
        try:
            username = user_data['username']
            email = user_data['email']
            password = user_data['password']
            is_admin = user_data.get('is_admin', False)
            is_moderator = user_data.get('is_moderator', False)
            
            # Ne pas hacher le mot de passe ici, il sera haché dans _create_user_postgresql
            user_id = str(uuid.uuid4())
            
            if self.use_postgresql:
                return self._create_user_postgresql(user_id, username, email, password, is_admin, is_moderator)
            else:
                return self._create_user_json(user_id, username, email, password, is_admin, is_moderator)
                
        except Exception as e:
            logger.error(f"Erreur création utilisateur: {e}")
            return None
    
    def _create_user_postgresql(self, user_id: str, username: str, email: str, password: str, is_admin: bool, is_moderator: bool) -> Optional[str]:
        """Crée un utilisateur dans PostgreSQL avec mot de passe haché"""
        """Créer un utilisateur dans PostgreSQL avec vérification unicité email"""
        try:
            import psycopg2
            from psycopg2.errors import UniqueViolation
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            
            # Vérifier l'unicité de l'email et du username en une seule requête
            cursor.execute("""
                SELECT 
                    EXISTS(SELECT 1 FROM users WHERE email = %s) as email_exists,
                    EXISTS(SELECT 1 FROM users WHERE username = %s) as username_exists
            """, (email, username))
            
            email_exists, username_exists = cursor.fetchone()
            
            if email_exists or username_exists:
                cursor.close()
                conn.close()
                if email_exists:
                    logger.error(f"Email déjà utilisé: {email}")
                if username_exists:
                    logger.error(f"Username déjà utilisé: {username}")
                return None
            
            # Hacher le mot de passe s'il ne l'est pas déjà
            if isinstance(password, tuple):  # Si déjà haché par _hash_password
                hashed_password = password[0]  # Prendre le premier élément du tuple (le hash)
            else:
                hashed_password, _ = self._hash_password(password)
            
            # Créer l'utilisateur avec le mot de passe haché
            cursor.execute("""
                INSERT INTO users (username, email, password, is_admin, is_moderator, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id
            """, (username, email, hashed_password.decode('utf-8'), is_admin, is_moderator))
            
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
        if not username or not password:
            return None
            
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Récupérer l'utilisateur avec son mot de passe haché
            cursor.execute("""
                SELECT id, username, email, password, is_admin, is_moderator, is_active
                FROM users 
                WHERE username = %s AND is_active = TRUE
            """, (username,))
            
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            
            # Vérifier si l'utilisateur existe et que le mot de passe est correct
            if user and self._verify_password(password, user['password']):
                logger.info(f"Authentification PostgreSQL réussie: {username}")
                return {
                    'id': str(user['id']),
                    'username': user['username'],
                    'email': user['email'],
                    'is_admin': user['is_admin'],
                    'is_moderator': user['is_moderator']
                }
            
            # Journaliser les échecs de connexion (sans le mot de passe)
            logger.warning(f"Échec d'authentification pour l'utilisateur: {username}")
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
    
    def update_last_login(self, user_id: str) -> bool:
        """Met à jour la date de dernière connexion d'un utilisateur"""
        try:
            import psycopg2
            from datetime import datetime
            
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            
            # Mettre à jour à la fois last_active et updated_at
            cursor.execute("""
                UPDATE users 
                SET last_active = %s, 
                    updated_at = %s
                WHERE id = %s
            """, (datetime.now(), datetime.now(), user_id))
            
            conn.commit()
            updated_rows = cursor.rowcount
            cursor.close()
            conn.close()
            
            if updated_rows > 0:
                logger.info(f"Mise à jour de la dernière connexion pour l'utilisateur ID: {user_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la dernière connexion: {e}")
            return False

    def _get_all_users_postgresql(self) -> list:
        """Obtenir tous les utilisateurs PostgreSQL"""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT id, username, email, is_admin, is_moderator, created_at, last_active
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
