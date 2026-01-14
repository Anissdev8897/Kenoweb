#!/usr/bin/env python3
"""
Script de test pour vérifier la connexion avec la base de données PostgreSQL
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Tester la connexion à la base de données PostgreSQL"""
    
    # Récupérer l'URL de connexion depuis les variables d'environnement
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("La variable d'environnement DATABASE_URL n'est pas définie")
        print("ERREUR: La variable d'environnement DATABASE_URL est requise")
        return False
    
    try:
        logger.info("Test de connexion à la base de données...")
        logger.info(f"URL de la base de données: {database_url[:30]}...")  # Ne pas logger l'URL complète pour des raisons de sécurité
        
        # Connexion à la base de données
        conn = psycopg2.connect(database_url)
        
        # Créer un curseur
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Vérifier la version de PostgreSQL
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        logger.info(f"Version PostgreSQL: {version['version']}")
        
        # Vérifier l'existence de la table users
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users'
            )
        """)
        table_exists = cursor.fetchone()['exists']
        logger.info(f"Table 'users' existe: {table_exists}")
        
        if table_exists:
            # Obtenir la structure de la table users
            cursor.execute("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            logger.info("Structure de la table 'users':")
            for col in columns:
                logger.info(f"  {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")
            
            # Compter le nombre d'utilisateurs
            cursor.execute("SELECT COUNT(*) as count FROM users")
            user_count = cursor.fetchone()['count']
            logger.info(f"Nombre d'utilisateurs: {user_count}")
            
            # Afficher quelques utilisateurs
            if user_count > 0:
                cursor.execute("SELECT id, username, email, created_at FROM users LIMIT 5")
                users = cursor.fetchall()
                logger.info("Premiers utilisateurs:")
                for user in users:
                    logger.info(f"  ID: {user['id']}, Username: {user['username']}, Email: {user['email']}")
        
        # Fermer la connexion
        cursor.close()
        conn.close()
        
        logger.info("✅ Connexion réussie à la base de données PostgreSQL")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur de connexion: {e}")
        return False

def test_user_creation():
    """Tester la création d'un utilisateur"""
    
    try:
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        from auth_system import AuthSystem
        
        auth_system = AuthSystem()
        
        # Créer un utilisateur de test
        test_user = {
            'username': 'test_user',
            'email': 'test@example.com',
            'password': 'test123',
            'is_admin': False,
            'is_moderator': False
        }
        
        user_id = auth_system.create_user(test_user)
        
        if user_id:
            logger.info(f"✅ Utilisateur créé avec succès: ID={user_id}")
            
            # Tester l'authentification
            authenticated_user = auth_system.authenticate_user('test_user', 'test123')
            if authenticated_user:
                logger.info(f"✅ Authentification réussie: {authenticated_user['username']}")
                return True
            else:
                logger.error("❌ Échec de l'authentification")
                return False
        else:
            logger.error("❌ Échec de la création de l'utilisateur")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erreur lors du test de création d'utilisateur: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TEST DE CONNEXION À LA BASE DE DONNÉES")
    print("=" * 60)
    
    # Test 1: Connexion à la base de données
    db_test = test_database_connection()
    
    print()
    print("=" * 60)
    print("TEST DE CRÉATION D'UTILISATEUR")
    print("=" * 60)
    
    # Test 2: Création d'utilisateur
    user_test = test_user_creation()
    
    print()
    print("=" * 60)
    print("RÉSUMÉ DES TESTS")
    print("=" * 60)
    print(f"Connexion DB: {'✅ PASS' if db_test else '❌ FAIL'}")
    print(f"Création user: {'✅ PASS' if user_test else '❌ FAIL'}")
    
    if db_test and user_test:
        print("\n🎉 Tous les tests ont réussi !")
    else:
        print("\n⚠️  Certains tests ont échoué")
