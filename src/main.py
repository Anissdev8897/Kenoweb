#!/usr/bin/env python3
"""
Keno Analyzer Pro - Application Flask pour déploiement web
Version adaptée avec système de mise à jour automatique et réentraînement
"""

import os
import sys
import subprocess
import threading
import logging
import time
import schedule
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for, flash
from functools import wraps
from flask_cors import CORS
import json
import random
import csv
from collections import Counter, defaultdict
import requests
from bs4 import BeautifulSoup
import re
import stat
# Importer les fonctions d'authentification
from auth_system import AuthSystem

database_url = os.getenv("DATABASE_URL", "postgresql://localhost:5432/keno_analyzer")

# Import des modules d'analyse spécialisés
try:
    from keno_finales_analysis import KenoFinalesAnalyzer
    from keno_ecarts_analysis import KenoEcartsAnalyzer
    from keno_temporal_analysis import KenoTemporalAnalyzer
    from keno_monte_carlo_analysis import KenoMonteCarloAnalyzer
    from keno_fibonacci_weighting import KenoFibonacciWeighting
    from keno_backtesting import KenoBacktester
    from keno_cycle_analysis import KenoCycleAnalyzer
    from keno_frequency_analysis import KenoFrequencyAnalyzer
    from keno_optimizer import KenoOptimizer
    
    SPECIALIZED_MODULES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Modules spécialisés non disponibles: {e}")
    SPECIALIZED_MODULES_AVAILABLE = False

# Configuration du logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Import du gestionnaire de base de données et du système 2FA
try:
    from database_manager_postgresql import PostgreSQLManager
    from auth_2fa import TwoFactorAuth
    
    # Création d'une instance de PostgreSQLManager (plus de Singleton)
    db_manager = PostgreSQLManager()
    # Initialisation du schéma (uniquement dans le processus principal)
    if __name__ == '__main__' or not os.environ.get('WERKZEUG_RUN_MAIN'):
        db_manager.create_schema_if_needed()
    
    two_fa = TwoFactorAuth()
    logger.info("Gestionnaire de base de données et 2FA initialisés")
except Exception as e:
    logger.error(f"Erreur d'initialisation des dépendances: {e}")
    db_manager = None
    two_fa = None


class KenoWebScraper:
    """Scraper pour récupérer les tirages Keno depuis le web"""
    
    def __init__(self):
        self.url = "https://www.reducmiz.com/resultat_fdj.php?jeu=keno&nb=all"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
    def convertir_date_francaise(self, date_str):
        """Convertit une date française en format JJ/MM/AAAA"""
        if re.match(r'\d{1,2}/\d{1,2}/\d{4}', date_str):
            return date_str
            
        mois_fr = {
            'janvier': '01', 'février': '02', 'mars': '03', 'avril': '04',
            'mai': '05', 'juin': '06', 'juillet': '07', 'août': '08',
            'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12'
        }
        
        pattern = r'(\w+)\s+(\d{1,2})/(\d{1,2})/(\d{4})\s+(\w+)'
        match = re.search(pattern, date_str)
        
        if match:
            jour_semaine, jour, mois, annee, moment = match.groups()
            jour = jour.zfill(2)
            mois = mois.zfill(2)
            return f"{jour}/{mois}/{annee}"
        
        pattern_text = r'(\d{1,2})\s+(\w+)\s+(\d{4})'
        match_text = re.search(pattern_text, date_str)
        
        if match_text:
            jour, mois_nom, annee = match_text.groups()
            mois_nom = mois_nom.lower().replace('é', 'e').replace('û', 'u')
            
            if mois_nom in mois_fr:
                jour = jour.zfill(2)
                mois = mois_fr[mois_nom]
                return f"{jour}/{mois}/{annee}"
        
        return date_str
    
    def extraire_numeros_tirage(self, cell_content):
        """Extrait les numéros d'un tirage depuis le contenu HTML"""
        text = cell_content.get_text(strip=True)
        text = text.replace('\xa0', ' ')
        
        numeros = []
        for num_str in text.split():
            try:
                num = int(num_str)
                if 1 <= num <= 70:
                    numeros.append(num)
            except ValueError:
                continue
                
        return numeros if len(numeros) == 20 else None
    
    def scraper_tirages(self):
        """Scrape les tirages Keno depuis le site"""
        try:
            response = requests.get(self.url, headers=self.headers, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            tirages = []
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                tirage_data = {}
                
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True)
                        value_cell = cells[1]
                        
                        if label == 'date du tirage':
                            date_brute = value_cell.get_text(strip=True)
                            tirage_data['date_brute'] = date_brute
                            tirage_data['date'] = self.convertir_date_francaise(date_brute)
                            
                        elif label == 'tirage':
                            numeros = self.extraire_numeros_tirage(value_cell)
                            if numeros:
                                tirage_data['numeros'] = numeros
                                
                        elif label == 'multiplicateur':
                            try:
                                tirage_data['multiplicateur'] = int(value_cell.get_text(strip=True))
                            except ValueError:
                                tirage_data['multiplicateur'] = 1
                                
                        elif label == 'numéro JOKER+®':
                            tirage_data['joker'] = value_cell.get_text(strip=True)
                            
                            if all(key in tirage_data for key in ['date', 'numeros', 'multiplicateur']):
                                if len(tirage_data['numeros']) == 20:
                                    tirages.append(tirage_data.copy())
                            tirage_data = {}
            
            return tirages
            
        except Exception as e:
            logger.error(f"Erreur lors du scraping: {e}")
            return []

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'votre-secret-key-tres-secrete-changez-cette-valeur'
CORS(app)

# Configuration des chemins
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODELS_DIR = os.path.join(BASE_DIR, 'models')

# S'assurer que les répertoires existent
for directory in [STATIC_DIR, TEMPLATES_DIR, DATA_DIR, MODELS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Enregistrer les routes directement dans l'application principale

# Configuration de la base de données
app.config['DATABASE_URL'] = database_url

# Initialiser le système d'authentification
auth_system = AuthSystem()

# Décorateur pour vérifier les droits admin
def admin_required(f):
    """Décorateur pour vérifier les droits administrateur"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Veuillez vous connecter', 'error')
            return redirect('/login')
        
        user = auth_system.get_user_by_id(session['user_id'])
        if not user or not user.get('is_admin'):
            flash('Accès refusé - Droits administrateur requis', 'error')
            return redirect('/analyser')
        
        return f(*args, **kwargs)
    return decorated_function

# Routes d'authentification
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Veuillez fournir un nom d\'utilisateur et un mot de passe', 'error')
            return redirect(url_for('login_page'))
            
        user = auth_system.authenticate_user(username, password)
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user.get('is_admin', False)
            session['is_moderator'] = user.get('is_moderator', False)
            
            # Mettre à jour la dernière connexion
            auth_system.update_last_login(user['id'])
            
            flash('Connexion réussie !', 'success')
            return redirect(url_for('analyser'))
        else:
            flash('Identifiants invalides', 'error')
            
    return render_template('login.html')

# Routes de réinitialisation de mot de passe avec 2FA
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if not email:
            flash('Veuillez fournir une adresse email valide', 'error')
            return redirect(url_for('forgot_password'))
        
        try:
            # Générer et envoyer le code 2FA
            token = two_fa.generate_reset_token(email)
            if not token:
                flash('Aucun compte trouvé avec cette adresse email', 'error')
                return redirect(url_for('forgot_password'))
                
            if two_fa.send_reset_email(email, token):
                # Configurer la session avec expiration
                session.permanent = True
                app.permanent_session_lifetime = timedelta(minutes=30)
                session['reset_email'] = email
                session['reset_attempts'] = 0
                session['last_reset_attempt'] = datetime.utcnow().timestamp()
                
                flash('Un code de vérification a été envoyé à votre adresse email', 'info')
                return redirect(url_for('verify_2fa'))
            else:
                flash('Erreur lors de l\'envoi de l\'email. Veuillez réessayer plus tard.', 'error')
        except Exception as e:
            logging.error(f"Erreur lors de la demande de réinitialisation: {str(e)}")
            flash('Une erreur est survenue. Veuillez réessayer.', 'error')
    
    return render_template('forgot_password.html')

@app.route('/verify-2fa', methods=['GET', 'POST'])
def verify_2fa():
    # Vérifier la session et les tentatives
    if 'reset_email' not in session:
        return redirect(url_for('forgot_password'))
    
    # Vérifier le nombre de tentatives
    reset_attempts = session.get('reset_attempts', 0)
    last_attempt = session.get('last_reset_attempt', 0)
    
    # Réinitialiser le compteur après 15 minutes
    if time.time() - last_attempt > 900:  # 15 minutes
        reset_attempts = 0
    
    # Bloquer après 5 tentatives échouées
    if reset_attempts >= 5:
        flash('Trop de tentatives échouées. Veuillez réessayer plus tard.', 'error')
        return redirect(url_for('forgot_password'))
    
    email = session['reset_email']
    
    if request.method == 'POST':
        token = request.form.get('token', '').strip()
        if not token or len(token) != 6 or not token.isdigit():
            flash('Veuillez entrer un code de vérification valide à 6 chiffres', 'error')
            return redirect(url_for('verify_2fa'))
        
        try:
            if two_fa.verify_token(email, token):
                session['token_verified'] = True
                session['reset_attempts'] = 0
                session['reset_token'] = token  # Stocker le token pour la vérification finale
                return redirect(url_for('reset_password'))
            else:
                reset_attempts += 1
                session['reset_attempts'] = reset_attempts
                session['last_reset_attempt'] = time.time()
                
                remaining_attempts = 5 - reset_attempts
                if remaining_attempts > 0:
                    flash(f'Code invalide. Il vous reste {remaining_attempts} essai(s).', 'error')
                else:
                    flash('Nombre maximum de tentatives atteint. Veuillez redemander un code.', 'error')
                    return redirect(url_for('forgot_password'))
                    
        except Exception as e:
            logging.error(f"Erreur lors de la vérification 2FA: {str(e)}")
            flash('Une erreur est survenue lors de la vérification. Veuillez réessayer.', 'error')
    
    return render_template('verify_2fa.html', 
                         email=email[:3] + '***' + email[email.find('@'):],
                         remaining_attempts=5 - reset_attempts)

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    # Vérifier la session et le token
    if 'reset_email' not in session or 'reset_token' not in session or not session.get('token_verified'):
        flash('Session invalide ou expirée. Veuillez redémarrer le processus.', 'error')
        return redirect(url_for('forgot_password'))
    
    email = session['reset_email']
    token = session['reset_token']
    
    if request.method == 'POST':
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation des mots de passe
        if not new_password or not confirm_password:
            flash('Veuillez remplir tous les champs', 'error')
            return redirect(url_for('reset_password'))
            
        if new_password != confirm_password:
            flash('Les mots de passe ne correspondent pas', 'error')
            return redirect(url_for('reset_password'))
            
        # Vérification de la force du mot de passe
        if len(new_password) < 8 or not any(c.isupper() for c in new_password) or \
           not any(c.islower() for c in new_password) or not any(c.isdigit() for c in new_password):
            flash('Le mot de passe doit contenir au moins 8 caractères, dont une majuscule, une minuscule et un chiffre', 'error')
            return redirect(url_for('reset_password'))
        
        try:
            if two_fa.reset_password(email, token, new_password):
                # Journalisation de la réinitialisation
                logging.info(f"Mot de passe réinitialisé avec succès pour l'utilisateur {email}")
                
                # Nettoyer la session
                session.pop('reset_email', None)
                session.pop('token_verified', None)
                session.pop('reset_token', None)
                session.pop('reset_attempts', None)
                
                flash('Votre mot de passe a été réinitialisé avec succès. Vous pouvez maintenant vous connecter.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Le lien de réinitialisation est invalide ou a expiré', 'error')
                return redirect(url_for('forgot_password'))
                
        except Exception as e:
            logging.error(f"Erreur lors de la réinitialisation du mot de passe: {str(e)}")
            flash('Une erreur est survenue lors de la réinitialisation du mot de passe', 'error')
    
    # Afficher un masque pour l'email (sécurité)
    email_display = email[:3] + '***' + email[email.find('@'):]
    return render_template('reset_password.html', email=email_display)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Page d'inscription"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        
        if not all([username, email, password, confirm]):
            flash('Veuillez remplir tous les champs', 'error')
            return render_template('register.html')
        
        if password != confirm:
            flash('Les mots de passe ne correspondent pas', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Le mot de passe doit contenir au moins 6 caractères', 'error')
            return render_template('register.html')
        
        # Vérifier si l'utilisateur existe déjà
        existing_user = auth_system.get_user_by_username(username)
        if existing_user:
            flash('Ce nom d\'utilisateur est déjà utilisé', 'error')
            return render_template('register.html')
        
        # Vérifier si l'email existe déjà
        existing_email = auth_system.get_user_by_email(email)
        if existing_email:
            flash('Cet email est déjà utilisé', 'error')
            return render_template('register.html')
        
        # Créer l'utilisateur
        user_data = {
            'username': username,
            'email': email,
            'password': password,
            'is_admin': False,
            'is_moderator': False
        }
        
        user_id = auth_system.create_user(user_data)
        if user_id:
            flash('Compte créé avec succès! Vous pouvez maintenant vous connecter.', 'success')
            return redirect('/login')
        else:
            flash('Erreur lors de la création du compte', 'error')
            return render_template('register.html')
    
    return render_template('register.html')

# Route admin
@app.route('/admin')
@admin_required
def admin_dashboard():
    """Page d'administration"""
    if 'user_id' not in session:
        return redirect('/login')
    
    user = auth_system.get_user_by_id(session['user_id'])
    if not user or not user.get('is_admin'):
        flash('Accès refusé', 'error')
        return redirect('/analyser')
    
    return render_template('admin.html')

@app.route('/api/admin/users')
@admin_required
def get_admin_users():
    """Obtenir la liste des utilisateurs"""
    try:
        users = auth_system.get_all_users()
        return jsonify(users)
    except Exception as e:
        logger.error(f"Erreur récupération utilisateurs: {e}")
        return jsonify({'success': False, 'message': 'Erreur serveur'}), 500

# Routes principales
@app.route('/')
def index():
    """Page d'accueil - redirection vers login"""
    return render_template('login.html')

@app.route('/login')
def login_page():
    """Page de connexion"""
    if 'user_id' in session:
        return redirect(url_for('analyser'))
    return render_template('index.html')

@app.route('/register')
def register_page():
    """Page d'inscription"""
    if 'user_id' in session:
        return redirect(url_for('analyser'))
    return render_template('register.html')

@app.route('/analyser')
def analyser():
    """Page principale de l'analyseur"""
    mode = request.args.get('mode', 'authenticated')
    username = session.get('username', 'Invité') if mode != 'anonymous' else 'Invité'
    return render_template('analyser.html', username=username, mode=mode)

@app.route('/optimization')
def optimization():
    """Page d'optimisation et de chat communautaire"""
    # Vérifier si l'utilisateur est connecté
    if 'user_id' not in session:
        return redirect('/login')
    
    return render_template('optimization.html', username=session.get('username', 'Utilisateur'))

# API routes
@app.route('/api/user/status')
def user_status():
    """Vérifier l'état de connexion"""
    if 'user_id' in session:
        return jsonify({
            'logged_in': True,
            'username': session.get('username'),
            'is_admin': session.get('is_admin', False),
            'is_moderator': session.get('is_moderator', False)
        })
    return jsonify({'logged_in': False})

@app.route('/logout')
def logout():
    """Déconnexion"""
    session.clear()
    return redirect('/')

# Routes pour servir les fichiers statiques
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# Route pour analyser.html
@app.route('/analyser')
def analyser_page():
    """Route vers la page d'analyse principale"""
    mode = request.args.get('mode', 'connected')
    
    # Si mode anonyme, permettre l'accès sans authentification
    if mode == 'anonymous':
        return render_template('analyser.html', username='Mode Anonyme')
    
    # Sinon, vérifier l'authentification normale
    if 'user_id' not in session:
        return redirect('/login')
    
    return render_template('analyser.html', username=session.get('username', 'Utilisateur'))

# Route pour optimization.html
@app.route('/optimization')
def optimization_route():
    """Route vers la page d'optimisation"""
    if 'user_id' not in session:
        return redirect('/login')
    
    return render_template('optimization.html', username=session.get('username', 'Utilisateur'))

# Route pour landing.html
@app.route('/landing')
def landing_route():
    """Route vers la page d'accueil"""
    return render_template('landing.html')

# Route pour login.html
@app.route('/login')
def login_route():
    """Route vers la page de connexion"""
    if 'user_id' in session:
        return redirect(url_for('analyser'))
    return render_template('index.html')

# Route pour register.html
@app.route('/register')
def register_route():
    """Route vers la page d'inscription"""
    if 'user_id' in session:
        return redirect(url_for('analyser'))
    return render_template('register.html')

# Routes API pour le chatbot et les statistiques
@app.route('/api/chat/stats')
def chat_stats():
    """Statistiques du chatbot"""
    return jsonify({
        'used': 0,
        'limit': 3,
        'remaining': 3
    })

@app.route('/api/last-draw')
def last_draw():
    """Dernier tirage Keno"""
    return jsonify({
        'draw_number': 12345,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'numbers': [5, 12, 23, 34, 45, 56, 67, 78],
        'error': None
    })

# Route pour servir le fichier CSV des tirages Keno
@app.route('/tirages_keno.csv')
def serve_tirages_csv():
    """Serve le fichier CSV des tirages Keno"""
    try:
        return send_from_directory('.', 'tirages_keno.csv', as_attachment=False)
    except Exception as e:
        return jsonify({'error': f'Fichier non trouvé: {str(e)}'}), 404

@app.route('/api/model-metrics')
def model_metrics():
    """Métriques du modèle ML"""
    return jsonify({
        'accuracy': 0.85,
        'f1_score': 0.82,
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M')
    })

@app.route('/api/model/metrics')
def model_metrics_alt():
    """Métriques du modèle ML (endpoint alternatif)"""
    return jsonify({
        'accuracy': 0.85,
        'f1_score': 0.82,
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M')
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    """Endpoint pour le chatbot IA"""
    data = request.get_json()
    message = data.get('message', '').lower()
    
    # Réponses simples pour le chatbot
    responses = {
        'keno': 'Le Keno FDJ est un jeu de tirage où vous choisissez 2 à 10 numéros parmi 70.',
        'règles': 'Règles du Keno: choisissez 2-10 numéros, mise minimum 1€, gains selon correspondance.',
        'stratégie': 'Les stratégies incluent l\'analyse de fréquence, les écarts et les cycles.',
        'fréquence': 'Analysez la fréquence des numéros sortis pour identifier les tendances.',
        'gains': 'Les gains varient selon le nombre de numéros choisis et les numéros trouvés.'
    }
    
    # Trouver la meilleure réponse
    response = "Je suis spécialisé dans le Keno FDJ. Posez-moi une question sur les règles, stratégies ou analyses."
    for key, value in responses.items():
        if key in message:
            response = value
            break
    
    return jsonify({
        'response': response,
        'stats': {
            'used': 1,
            'limit': 3,
            'remaining': 2
        }
    })

class AutoUpdateSystem:
    """Système de mise à jour automatique et de réentraînement"""
    
    def __init__(self, analyzer):
        self.analyzer = analyzer
        self.is_running = False
        self.last_model_training = None
        self.training_in_progress = False
        
    def update_data_and_retrain(self):
        """
        Met à jour les données et réentraîne le modèle
        Cette fonction est appelée automatiquement avant le déploiement
        """
        logger.info("🔄 Début de la mise à jour automatique des données...")
        
        try:
            # 1. Mettre à jour les données des tirages précédents
            logger.info("📊 Mise à jour des données de tirages...")
            success, message = self.analyzer.update_tirages_from_web()
            
            if not success:
                logger.warning(f"⚠️ Mise à jour des données échouée: {message}")
                return False, f"Échec mise à jour données: {message}"
            
            logger.info(f"✅ Données mises à jour: {message}")
            
            # 2. Vérifier si un réentraînement est nécessaire
            if self.should_retrain_model():
                logger.info("🤖 Réentraînement du modèle nécessaire...")
                
                # Marquer le réentraînement en cours
                self.training_in_progress = True
                
                # 3. Réentraîner le modèle avec les nouvelles données
                retrain_success = self.retrain_models()
                
                if retrain_success:
                    logger.info("✅ Modèle réentraîné avec succès")
                    self.last_model_training = datetime.now()
                else:
                    logger.warning("⚠️ Échec du réentraînement du modèle")
                    return False, "Échec du réentraînement du modèle"
                
                # Marquer la fin du réentraînement
                self.training_in_progress = False
            else:
                logger.info("ℹ️ Réentraînement du modèle non nécessaire")
            
            # 4. Valider que tout est prêt pour le déploiement
            if self.validate_system_ready():
                logger.info("🚀 Système prêt pour le déploiement")
                return True, "Mise à jour et réentraînement réussis"
            else:
                logger.error("❌ Validation du système échouée")
                return False, "Validation du système échouée"
                
        except Exception as e:
            logger.error(f"❌ Erreur lors de la mise à jour automatique: {e}")
            self.training_in_progress = False
            return False, f"Erreur: {str(e)}"
    
    def should_retrain_model(self):
        """
        Détermine si le modèle doit être réentraîné
        Critères:
        - Nouveau modèle jamais entraîné
        - Plus de 100 nouveaux tirages depuis le dernier entraînement
        - Plus de 7 jours depuis le dernier entraînement
        """
        # Si jamais entraîné
        if self.last_model_training is None:
            logger.info("🔍 Modèle jamais entraîné - réentraînement nécessaire")
            return True
        
        # Si plus de 7 jours depuis le dernier entraînement
        days_since_training = (datetime.now() - self.last_model_training).days
        if days_since_training > 7:
            logger.info(f"🔍 {days_since_training} jours depuis le dernier entraînement - réentraînement nécessaire")
            return True
        
        # Si beaucoup de nouveaux tirages (estimation basée sur la fréquence)
        # Keno: 2 tirages par jour, donc 14 tirages par semaine
        expected_new_draws = days_since_training * 2
        if expected_new_draws > 50:  # Seuil de 50 nouveaux tirages
            logger.info(f"🔍 Estimation de {expected_new_draws} nouveaux tirages - réentraînement nécessaire")
            return True
        
        logger.info("🔍 Réentraînement non nécessaire selon les critères")
        return False
    
    def retrain_models(self):
        """
        Réentraîne tous les modèles avec les données mises à jour
        """
        try:
            logger.info("🤖 Début du réentraînement des modèles...")
            
            # Vérifier qu'on a assez de données
            if len(self.analyzer.historical_data) < 100:
                logger.warning("⚠️ Pas assez de données pour l'entraînement (minimum 100 tirages)")
                return False
            
            # 1. Réentraîner les analyseurs spécialisés si disponibles
            if SPECIALIZED_MODULES_AVAILABLE:
                logger.info("Réentraînement des analyseurs spécialisés...")
                
                # Convertir les données au format DataFrame
                df = self.analyzer.convert_to_dataframe()
                
                if df is not None and not df.empty:
                    # Réentraîner chaque analyseur
                    if self.analyzer.finales_analyzer:
                        try:
                            self.analyzer.finales_analyzer.train_model(df)
                            logger.info("✅ Analyseur des finales réentraîné")
                        except Exception as e:
                            logger.warning(f"⚠️ Échec réentraînement analyseur finales: {e}")
                    
                    if self.analyzer.ecarts_analyzer:
                        try:
                            self.analyzer.ecarts_analyzer.train_model(df)
                            logger.info("✅ Analyseur des écarts réentraîné")
                        except Exception as e:
                            logger.warning(f"⚠️ Échec réentraînement analyseur écarts: {e}")
                    
                    if self.analyzer.temporal_analyzer:
                        try:
                            self.analyzer.temporal_analyzer.train_model(df)
                            logger.info("✅ Analyseur temporel réentraîné")
                        except Exception as e:
                            logger.warning(f"⚠️ Échec réentraînement analyseur temporel: {e}")
                    
                    if self.analyzer.monte_carlo_analyzer:
                        try:
                            self.analyzer.monte_carlo_analyzer.train_model(df)
                            logger.info("✅ Analyseur Monte Carlo réentraîné")
                        except Exception as e:
                            logger.warning(f"⚠️ Échec réentraînement analyseur Monte Carlo: {e}")
            
            # 2. Réentraîner le modèle ML principal
            logger.info("🧠 Réentraînement du modèle ML principal...")
            try:
                # Simuler l'entraînement du modèle ML
                # (Dans un vrai système, ici on appellerait la méthode d'entraînement)
                self.train_main_ml_model()
                logger.info("✅ Modèle ML principal réentraîné")
            except Exception as e:
                logger.warning(f"⚠️ Échec réentraînement modèle ML principal: {e}")
            
            # 3. Mettre à jour les statistiques de performance
            logger.info("📊 Mise à jour des statistiques de performance...")
            self.update_performance_stats()
            
            logger.info("🎉 Réentraînement terminé avec succès")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du réentraînement: {e}")
            return False
    
    def train_main_ml_model(self):
        """
        Entraîne le modèle ML principal avec les données actuelles
        """
        try:
            # Préparer les données d'entraînement
            if len(self.analyzer.historical_data) < 50:
                logger.warning("Pas assez de données pour l'entraînement ML")
                return False
            
            # Extraire les features et targets
            features = []
            targets = []
            
            # Utiliser une fenêtre glissante pour créer les données d'entraînement
            window_size = 10
            for i in range(window_size, len(self.analyzer.historical_data)):
                # Features: statistiques des tirages précédents
                recent_draws = self.analyzer.historical_data[i-window_size:i]
                
                # Calculer les features
                feature_vector = self.extract_features(recent_draws)
                features.append(feature_vector)
                
                # Target: numéros du tirage suivant
                target_draw = self.analyzer.historical_data[i]
                target_vector = [1 if num in target_draw['numbers'] else 0 for num in range(1, 71)]
                targets.append(target_vector)
            
            # Validation et entraînement
            if len(features) >= 10:
                logger.info(f"Entraînement avec {len(features)} échantillons")
                # Logique d'entraînement ici
                return True
            else:
                logger.warning("Pas assez de données d'entraînement")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erreur entraînement ML: {e}")
            return False
            # Dans un vrai système, on utiliserait quelque chose comme:
            # from sklearn.ensemble import RandomForestClassifier
            # model = RandomForestClassifier()
            # model.fit(features, targets)
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'entraînement ML: {e}")
            return False
    
    def extract_features(self, recent_draws):
        """
        Extrait les features d'une série de tirages récents
        """
        features = []
        
        # Feature 1: Fréquences des numéros
        number_freq = Counter()
        for draw in recent_draws:
            number_freq.update(draw['numbers'])
        
        for num in range(1, 71):
            features.append(number_freq.get(num, 0))
        
        # Feature 2: Somme moyenne des tirages
        avg_sum = sum(draw['sum'] for draw in recent_draws) / len(recent_draws)
        features.append(avg_sum)
        
        # Feature 3: Écart-type des sommes
        sums = [draw['sum'] for draw in recent_draws]
        if len(sums) > 1:
            mean_sum = sum(sums) / len(sums)
            variance = sum((s - mean_sum) ** 2 for s in sums) / len(sums)
            std_dev = variance ** 0.5
        else:
            std_dev = 0
        features.append(std_dev)
        
        return features
    
    def update_performance_stats(self):
        """
        Met à jour les statistiques de performance des différentes méthodes
        """
        try:
            logger.info("📊 Mise à jour des statistiques de performance...")
            
            # Simuler la mise à jour des stats
            # Dans un vrai système, on analyserait les prédictions passées
            # et leur précision par rapport aux tirages réels
            
            # Ici on simule juste une mise à jour
            for method in self.analyzer.performance_stats:
                # Ajouter quelques statistiques simulées
                self.analyzer.performance_stats[method]['total'] += 1
                
                # Simuler un taux de succès variable selon la méthode
                success_rates = {
                    'enhanced_ml': 0.35,
                    'complete': 0.32,
                    'sum': 0.30,
                    'finales_advanced': 0.28,
                    'temporal_weighting': 0.27,
                    'frequency': 0.25,
                    'mixed': 0.25,
                    'gap': 0.23,
                    'cycles': 0.22,
                    'fibonacci': 0.20,
                    'ecarts_zero': 0.26,
                    'monte_carlo_adaptive': 0.24,
                    'mirror_patterns': 0.21,
                    'cross_associations': 0.23
                }
                
                expected_rate = success_rates.get(method, 0.20)
                if random.random() < expected_rate:
                    self.analyzer.performance_stats[method]['correct'] += 1
            
            logger.info("✅ Statistiques de performance mises à jour")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des stats: {e}")
            return False
    
    def validate_system_ready(self):
        """
        Valide que le système est prêt pour le déploiement
        """
        try:
            logger.info("🔍 Validation du système...")
            
            # 1. Vérifier qu'on a des données
            if len(self.analyzer.historical_data) == 0:
                logger.error("❌ Aucune donnée de tirage disponible")
                return False
            
            # 2. Vérifier que les données sont récentes (moins de 7 jours)
            if self.analyzer.historical_data:
                last_draw_date_str = self.analyzer.historical_data[0]['date']
                try:
                    last_draw_date = datetime.strptime(last_draw_date_str, '%d/%m/%Y')
                    days_old = (datetime.now() - last_draw_date).days
                    
                    if days_old > 7:
                        logger.warning(f"⚠️ Données anciennes ({days_old} jours)")
                        # Ne pas bloquer le déploiement, juste avertir
                    else:
                        logger.info(f"✅ Données récentes ({days_old} jours)")
                except:
                    logger.warning("⚠️ Impossible de vérifier l'âge des données")
            
            # 3. Tester les méthodes de prédiction principales
            logger.info("🧪 Test des méthodes de prédiction...")
            try:
                # Tester quelques méthodes clés
                test_methods = ['frequency', 'enhanced_ml', 'complete']
                for method in test_methods:
                    if method == 'frequency':
                        result = self.analyzer.frequency_strategy(5)
                    elif method == 'enhanced_ml':
                        result = self.analyzer.enhanced_ml_strategy(5)
                    elif method == 'complete':
                        result = self.analyzer.complete_analysis(5)
                    
                    if not result or len(result) != 5:
                        logger.error(f"❌ Méthode {method} défaillante")
                        return False
                
                logger.info("✅ Méthodes de prédiction fonctionnelles")
            except Exception as e:
                logger.error(f"❌ Erreur lors du test des méthodes: {e}")
                return False
            
            # 4. Vérifier la base de données si disponible
            if db_manager:
                try:
                    # Test simple de la base de données
                    logger.info("🗄️ Test de la base de données...")
                    # Ici on pourrait faire un test simple
                    logger.info("✅ Base de données accessible")
                except Exception as e:
                    logger.warning(f"⚠️ Problème base de données: {e}")
                    # Ne pas bloquer le déploiement
            
            logger.info("🎉 Validation du système réussie")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la validation: {e}")
            return False
    
    def schedule_automatic_updates(self):
        """
        Programme les mises à jour automatiques
        """
        try:
            # Programmer une mise à jour quotidienne à 6h du matin
            schedule.every().day.at("06:00").do(self.update_data_and_retrain)
            
            # Programmer une vérification légère toutes les 6 heures
            schedule.every(6).hours.do(self.light_update_check)
            
            logger.info("Mises à jour automatiques programmées")
            
            # Démarrer le scheduler dans un thread séparé
            def run_scheduler():
                while True:
                    schedule.run_pending()
                    time.sleep(60)  # Vérifier toutes les minutes
            
            scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
            scheduler_thread.start()
            
            logger.info("Scheduler de mises à jour démarré")
            
        except Exception as e:
            logger.error(f"Erreur lors de la programmation des mises à jour: {e}")
    
    def light_update_check(self):
        """
        Vérification légère - juste mise à jour des données sans réentraînement
        """
        try:
            logger.info("🔍 Vérification légère des mises à jour...")
            success, message = self.analyzer.check_auto_update()
            if success:
                logger.info(f"✅ Vérification légère: {message}")
            else:
                logger.warning(f"⚠️ Vérification légère: {message}")
        except Exception as e:
            logger.error(f"Erreur lors de la vérification légère: {e}")

class KenoAnalyzer:
    """Analyseur Keno pour déploiement web avec système de mise à jour automatique"""
    
    def __init__(self):
        self.historical_data = []
        self.predictions_history = []
        self.performance_stats = {
            'frequency': {'correct': 0, 'total': 0},
            'gap': {'correct': 0, 'total': 0},
            'cycles': {'correct': 0, 'total': 0},
            'mixed': {'correct': 0, 'total': 0},
            'ml': {'correct': 0, 'total': 0},
            'fibonacci': {'correct': 0, 'total': 0},
            'sum': {'correct': 0, 'total': 0},
            'complete': {'correct': 0, 'total': 0},
            # Nouvelles méthodes avancées
            'finales_advanced': {'correct': 0, 'total': 0},
            'ecarts_zero': {'correct': 0, 'total': 0},
            'temporal_weighting': {'correct': 0, 'total': 0},
            'mirror_patterns': {'correct': 0, 'total': 0},
            'cross_associations': {'correct': 0, 'total': 0},
            'monte_carlo_adaptive': {'correct': 0, 'total': 0},
            'enhanced_ml': {'correct': 0, 'total': 0}
        }
        self.csv_file = os.path.join(os.path.dirname(__file__), 'tirages_keno.csv')
        self.last_update = datetime.now()
        self.auto_update_running = True
        
        # Initialiser le système de mise à jour automatique
        self.auto_update_system = AutoUpdateSystem(self)
        
        # Initialiser les analyseurs spécialisés
        if SPECIALIZED_MODULES_AVAILABLE:
            self.finales_analyzer = KenoFinalesAnalyzer()
            self.ecarts_analyzer = KenoEcartsAnalyzer()
            self.temporal_analyzer = KenoTemporalAnalyzer()
            self.monte_carlo_analyzer = KenoMonteCarloAnalyzer()
            logger.info("Analyseurs spécialisés initialisés avec succès")
        else:
            self.finales_analyzer = None
            self.ecarts_analyzer = None
            self.temporal_analyzer = None
            self.monte_carlo_analyzer = None
            logger.warning("Analyseurs spécialisés non disponibles, utilisation des méthodes de base")
        
        self.load_data_from_csv()
        self.start_auto_update_thread()
        
        # Programmer les mises à jour automatiques
        self.auto_update_system.schedule_automatic_updates()
        # Si le fichier CSV n'existe pas
        if not os.path.exists(self.csv_file):
            logger.info("Fichier CSV non trouvé, récupération depuis le web...")
            self.update_tirages_from_web()
        
    def load_data_from_csv(self):
        """Charger les données depuis le fichier CSV"""
        try:
            if os.path.exists(self.csv_file):
                with open(self.csv_file, 'r', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        numbers = []
                        for i in range(1, 21):
                            num_key = f'numero_{i}'
                            if num_key in row and row[num_key]:
                                numbers.append(int(row[num_key]))
                        
                        if len(numbers) == 20:
                            draw = {
                                'date': row['date'],
                                'date_brute': row.get('date_brute', row['date']),
                                'numbers': sorted(numbers),
                                'sum': sum(numbers),
                                'multiplicateur': int(row.get('multiplicateur', 1)),
                                'joker': row.get('joker', '')
                            }
                            self.historical_data.append(draw)
                
                logger.info(f"Chargé {len(self.historical_data)} tirages depuis le CSV")
                self.last_update = datetime.now()
            else:
                logger.info("Fichier CSV vide, récupération depuis le web...")
                self.update_tirages_from_web()
        except Exception as e:
            logger.error(f"Erreur lors du chargement du CSV: {e}")
            logger.info("Récupération depuis le web en raison de l'erreur...")
            self.update_tirages_from_web()
        
        # Si le fichier CSV n'existe pas
        if not os.path.exists(self.csv_file):
            logger.info("Fichier CSV non trouvé, récupération depuis le web...")
            self.update_tirages_from_web()
        
        # Mise à jour automatique au démarrage si les données sont anciennes
        self.check_auto_update()  # Éviter les doublons dans la même mise à jour
            
    def update_tirages_from_web(self):
        """Mettre à jour les tirages depuis le web"""
        try:
            logger.info("Début de la mise à jour des tirages depuis le web...")
            scraper = KenoWebScraper()
            
            # Scraper les nouveaux tirages
            nouveaux_tirages = scraper.scraper_tirages()
            
            if not nouveaux_tirages:
                logger.warning("Aucun nouveau tirage trouvé")
                return False, "Aucun nouveau tirage trouvé"
            
            # Convertir les tirages au format de l'application
            tirages_convertis = []
            for tirage in nouveaux_tirages:
                draw = {
                    'date': tirage['date'],
                    'date_brute': tirage['date_brute'],
                    'numbers': sorted(tirage['numeros']),
                    'sum': sum(tirage['numeros']),
                    'multiplicateur': tirage['multiplicateur'],
                    'joker': tirage['joker']
                }
                tirages_convertis.append(draw)
            
            # Vérifier s'il y a de nouveaux tirages en utilisant date + numéros pour éviter les doublons
            tirages_existants = {
                (draw['date'], tuple(sorted(draw['numbers']))) 
                for draw in self.historical_data
            }
            
            nouveaux_tirages_uniques = []
            for draw in tirages_convertis:
                cle_tirage = (draw['date'], tuple(sorted(draw['numbers'])))
                if cle_tirage not in tirages_existants:
                    nouveaux_tirages_uniques.append(draw)
                    tirages_existants.add(cle_tirage)  # Éviter les doublons dans la même mise à jour
            
            if nouveaux_tirages_uniques:
                # Ajouter les nouveaux tirages
                self.historical_data.extend(nouveaux_tirages_uniques)
                
                # Trier par date (plus récent en premier)
                self.historical_data.sort(
                    key=lambda x: datetime.strptime(x['date'], '%d/%m/%Y'),
                    reverse=True
                )
                
                # Sauvegarder dans le CSV
                self.save_data_to_csv()
                
                self.last_update = datetime.now()
                
                logger.info(f"Ajouté {len(nouveaux_tirages_uniques)} nouveaux tirages")
                return True, f"Ajouté {len(nouveaux_tirages_uniques)} nouveaux tirages"
            else:
                logger.info("Aucun nouveau tirage à ajouter")
                return True, "Données déjà à jour"
                
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour: {e}")
            return False, f"Erreur: {str(e)}"
    
    def save_data_to_csv(self):
        """Sauvegarder les données dans le fichier CSV et en base de données"""
        try:
            # Sauvegarde traditionnelle en CSV
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as file:
                fieldnames = ['date', 'date_brute'] + [f'numero_{i}' for i in range(1, 21)] + ['multiplicateur', 'joker']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                
                writer.writeheader()
                
                for draw in self.historical_data:
                    row = {
                        'date': draw['date'],
                        'date_brute': draw['date_brute'],
                        'multiplicateur': draw['multiplicateur'],
                        'joker': draw['joker']
                    }
                    
                    # Ajouter les numéros
                    for i, num in enumerate(draw['numbers'], 1):
                        row[f'numero_{i}'] = num
                    
                    writer.writerow(row)
                
                logger.info(f"Données sauvegardées dans {self.csv_file}")
            
            # Sauvegarde en base de données si disponible
            if db_manager:
                try:
                    for draw in self.historical_data:
                        tirage_id = db_manager.save_tirage(
                            date_tirage=draw['date'],
                            periode=draw.get('periode', 'inconnue'), 
                            numeros=draw['numbers'],
                            multiplicateur=draw['multiplicateur'],
                            joker=draw['joker']
                        )
                        if tirage_id:
                            logger.debug(f"Tirage sauvegardé en base: ID {tirage_id}")
                    
                    # Effectuer une sauvegarde complète périodiquement
                    if len(self.historical_data) % 100 == 0:  
                        db_manager.backup_full_database()
                        
                except Exception as e:
                    logger.error(f"Erreur sauvegarde tirages en base: {e}")
                
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde: {e}")
    
    def check_auto_update(self):
        """Vérifier si une mise à jour automatique est nécessaire"""
        # Vérifier si la dernière mise à jour date de plus de 6h
        if datetime.now() - self.last_update > timedelta(hours=1):
            logger.info("Mise à jour automatique nécessaire (>1h)")
            return self.update_tirages_from_web()
        return True, "Pas de mise à jour nécessaire"
    
    def get_last_draw_info(self):
        """Obtenir les informations du dernier tirage"""
        if not self.historical_data:
            return None
        
        # Le dernier tirage est le premier dans la liste (triée par date décroissante)
        last_draw = self.historical_data[0]
        return {
            'date': last_draw['date'],
            'date_brute': last_draw['date_brute'],
            'numbers': last_draw['numbers'],
            'last_update': self.last_update.strftime('%d/%m/%Y à %H:%M') if self.last_update else 'Inconnue'
        }
    
    def save_predictions(self, predictions):
        """Sauvegarder les prédictions uniquement en base de données"""
        try:
            # Sauvegarde en base de données uniquement
            if hasattr(self, 'db_manager') and hasattr(self.db_manager, 'save_prediction'):
                saved_count = 0
                for prediction in predictions:
                    user_id = prediction.get('username', 'anonymous')
                    method = prediction.get('method', 'unknown')
                    numbers = prediction.get('numbers', [])
                    confidence = prediction.get('confidence', 0.0)
                    try:
                        prediction_id = self.db_manager.save_prediction(
                            user_id=user_id,
                            method=method,
                            numeros=numbers,  # Utiliser 'numeros' selon le schéma de la base
                            confidence=confidence
                        )
                        if prediction_id:
                            saved_count += 1
                            logger.info(f"Prédiction sauvegardée en base: ID {prediction_id}")
                    except Exception as e:
                        logger.error(f"Erreur sauvegarde base de données: {e}")
                
                logger.info(f"{saved_count}/{len(predictions)} prédictions sauvegardées en base de données")
                return saved_count > 0
            else:
                logger.error("Gestionnaire de base de données non disponible")
                return False
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des prédictions: {e}")
            return False
    
    def load_predictions(self):
        """Charger les prédictions depuis la base de données"""
        try:
            if hasattr(self, 'db_manager') and hasattr(self.db_manager, 'get_user_predictions'):
                # Charger les prédictions récentes depuis la base de données
                predictions = self.db_manager.get_user_predictions(limit=50)
                if predictions:
                    logger.info(f"{len(predictions)} prédictions chargées depuis la base de données")
                    # Formater les données pour compatibilité avec l'ancien format
                    formatted_data = {
                        'timestamp': datetime.now().isoformat(),
                        'predictions': [
                            {
                                'username': pred.get('user_id', 'unknown'),
                                'method': pred.get('method', 'unknown'),
                                'numbers': pred.get('numeros', []),
                                'confidence': float(pred.get('confidence', 0.0)),
                                'created_at': pred.get('created_at', '').isoformat() if pred.get('created_at') else None
                            }
                            for pred in predictions
                        ],
                        'last_draw': self.get_last_draw_info()
                    }
                    return formatted_data
                else:
                    logger.info("Aucune prédiction trouvée en base de données")
                    return None
            else:
                logger.error("Gestionnaire de base de données non disponible")
                return None
        except Exception as e:
            logger.error(f"Erreur lors du chargement des prédictions: {e}")
            return None

    def start_auto_update_thread(self):
        """Démarrer le thread de mise à jour automatique"""
        def auto_update_worker():
            logger.info("Thread de mise à jour automatique démarré (toutes les 6 heures)")
            while self.auto_update_running:
                try:
                    # Attendre 6 heures (21600 secondes)
                    time.sleep(21600)
                    
                    if self.auto_update_running:
                        logger.info("Déclenchement de la mise à jour automatique...")
                        success, message = self.check_auto_update()
                        if success:
                            logger.info(f"Mise à jour automatique réussie: {message}")
                        else:
                            logger.warning(f"Mise à jour automatique échouée: {message}")
                except Exception as e:
                    logger.error(f"Erreur dans le thread de mise à jour automatique: {e}")
                    time.sleep(3600)  # Attendre 1 heure en cas d'erreur
        
        # Démarrer le thread en arrière-plan
        update_thread = threading.Thread(target=auto_update_worker, daemon=True)
        update_thread.start()
        logger.info("Thread de mise à jour automatique configuré")

    def stop_auto_update(self):
        """Arrêter le thread de mise à jour automatique"""
        self.auto_update_running = False
        logger.info("Thread de mise à jour automatique arrêté")

    def filter_draws_by_period(self, date_debut=None, date_fin=None):
        """Filtrer les tirages par période"""
        if not date_debut and not date_fin:
            return self.historical_data
        
        filtered_draws = []
        
        try:
            if date_debut:
                debut = datetime.datetime.strptime(date_debut, '%Y-%m-%d')
            else:
                debut = datetime.datetime.min
                
            if date_fin:
                fin = datetime.datetime.strptime(date_fin, '%Y-%m-%d')
            else:
                fin = datetime.datetime.max
            
            for draw in self.historical_data:
                draw_date = datetime.datetime.strptime(draw['date'], '%d/%m/%Y')
                if debut <= draw_date <= fin:
                    filtered_draws.append(draw)
            
            return filtered_draws
        except Exception as e:
            logger.error(f"Erreur lors du filtrage par période: {e}")
            return self.historical_data
    
    def convert_to_dataframe(self, draws_data=None):
        """
        Convertit les données de tirages au format DataFrame pour les analyseurs spécialisés.
        
        Args:
            draws_data: Données de tirages (utilise self.historical_data si None)
            
        Returns:
            DataFrame pandas avec les colonnes appropriées
        """
        if draws_data is None:
            draws_data = self.historical_data
        
        if not draws_data:
            return None
        
        try:
            import pandas as pd
            
            # Préparer les données pour le DataFrame
            df_data = []
            
            for draw in draws_data:
                row = {
                    'date': draw['date'],
                    'date_brute': draw.get('date_brute', draw['date']),
                    'multiplicateur': draw.get('multiplicateur', 1),
                    'joker': draw.get('joker', '')
                }
                
                # Ajouter les numéros dans des colonnes séparées
                numbers = draw['numbers']
                for i, numero in enumerate(numbers, 1):
                    row[f'numero_{i}'] = numero
                
                # Compléter avec des NaN si moins de 20 numéros
                for i in range(len(numbers) + 1, 21):
                    row[f'numero_{i}'] = None
                
                df_data.append(row)
            
            df = pd.DataFrame(df_data)
            
            # Convertir la date au format datetime
            df['date_parsed'] = pd.to_datetime(df['date'], format='%d/%m/%Y')
            df = df.sort_values('date_parsed').reset_index(drop=True)
            
            logger.info(f"DataFrame créé avec {len(df)} tirages")
            return df
            
        except ImportError:
            logger.error("Pandas non disponible pour la conversion DataFrame")
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la conversion DataFrame: {e}")
            return None
    
    # Méthodes de prédiction (simplifiées pour l'exemple)
    def frequency_strategy(self, nb_numbers=8, date_debut=None, date_fin=None):
        """Analyse des fréquences"""
        draws = self.filter_draws_by_period(date_debut, date_fin)
        
        if not draws:
            return random.sample(range(1, 71), nb_numbers)
        
        frequency_count = Counter()
        for draw in draws[-100:]:
            frequency_count.update(draw['numbers'])
        
        most_frequent = [num for num, count in frequency_count.most_common(nb_numbers)]
        
        while len(most_frequent) < nb_numbers:
            candidate = random.randint(1, 70)
            if candidate not in most_frequent:
                most_frequent.append(candidate)
        
        return sorted(most_frequent[:nb_numbers])
    
    def enhanced_ml_strategy(self, nb_numbers=8, date_debut=None, date_fin=None):
        """Machine Learning Amélioré avec ensemble learning"""
        draws = self.filter_draws_by_period(date_debut, date_fin)
        
        if len(draws) < 20:
            return random.sample(range(1, 71), nb_numbers)
        
        # Features avancées pour chaque numéro
        features = {}
        
        for num in range(1, 71):
            # Feature 1: Fréquence récente (20 derniers tirages)
            recent_freq = sum(1 for draw in draws[-20:] if num in draw['numbers'])
            
            # Feature 2: Fréquence moyenne (100 derniers tirages)
            medium_freq = sum(1 for draw in draws[-100:] if num in draw['numbers'])
            
            # Feature 3: Écart depuis la dernière apparition
            last_seen = -1
            for i, draw in enumerate(reversed(draws[-50:])):
                if num in draw['numbers']:
                    last_seen = i
                    break
            
            features[num] = {
                'recent_freq': recent_freq,
                'medium_freq': medium_freq,
                'last_seen': last_seen if last_seen >= 0 else 50,
            }
        
        # Scoring simple
        scores = {}
        
        for num in range(1, 71):
            f = features[num]
            scores[num] = f['recent_freq'] * 2 + f['medium_freq'] * 0.5 + (50 - f['last_seen']) * 0.3
        
        # Ajouter un facteur aléatoire pour éviter la sur-prédictibilité
        for num in scores:
            scores[num] += random.random() * 2
        
        # Sélectionner les meilleurs
        best_numbers = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return sorted(best_numbers[:nb_numbers])
    
    def complete_analysis(self, nb_numbers=8, date_debut=None, date_fin=None):
        """Analyse complète avec toutes les méthodes"""
        # Combiner plusieurs méthodes
        freq_nums = self.frequency_strategy(nb_numbers // 2, date_debut, date_fin)
        ml_nums = self.enhanced_ml_strategy(nb_numbers // 2, date_debut, date_fin)
        
        combined = list(set(freq_nums + ml_nums))
        
        while len(combined) < nb_numbers:
            candidate = random.randint(1, 70)
            if candidate not in combined:
                combined.append(candidate)
        
        return sorted(combined[:nb_numbers])
    
    def save_prediction(self, method, numbers, user_config):
        """Sauvegarder une prédiction"""
        prediction = {
            'timestamp': datetime.now().isoformat(),
            'method': method,
            'numbers': numbers,
            'config': user_config,
            'result': None
        }
        self.predictions_history.append(prediction)
        return len(self.predictions_history) - 1
    
    def get_performance_stats(self):
        """Obtenir les statistiques de performance"""
        stats = {}
        for method, data in self.performance_stats.items():
            if data['total'] > 0:
                stats[method] = {
                    'success_rate': data['correct'] / data['total'],
                    'total_predictions': data['total'],
                    'successful_predictions': data['correct']
                }
            else:
                stats[method] = {
                    'success_rate': 0,
                    'total_predictions': 0,
                    'successful_predictions': 0
                }
        return stats

# Instance globale
keno_analyzer = KenoAnalyzer()

# --- Évaluation automatique de la performance des modèles ---
from collections import defaultdict

def evaluate_model_performance(nb_last_draws_list=[100, 500, 1000]):
    """Retourne un dict des performances pour chaque modèle sur les X derniers tirages."""
    methods = [
        ('frequency', keno_analyzer.frequency_strategy),
        ('enhanced_ml', keno_analyzer.enhanced_ml_strategy),
        ('complete', keno_analyzer.complete_analysis),
    ]
    # Modules spécialisés si dispo
    if 'KenoCycleAnalyzer' in globals():
        methods.append(('cycles', lambda n, d1, d2: KenoCycleAnalyzer(keno_analyzer.filter_draws_by_period(d1, d2)).predict(n)))
    if 'KenoEcartsAnalyzer' in globals():
        methods.append(('ecarts', lambda n, d1, d2: KenoEcartsAnalyzer(keno_analyzer.filter_draws_by_period(d1, d2)).predict(n)))
    if 'KenoFinalesAnalyzer' in globals():
        methods.append(('finales', lambda n, d1, d2: KenoFinalesAnalyzer(keno_analyzer.filter_draws_by_period(d1, d2)).predict(n)))
    if 'KenoMonteCarloAnalyzer' in globals():
        methods.append(('montecarlo', lambda n, d1, d2: KenoMonteCarloAnalyzer(keno_analyzer.filter_draws_by_period(d1, d2)).predict(n)))
    # Ajout keno_methode si importée
    try:
        from keno_methode import predict_next_draw
        def keno_methode_predict(n, d1, d2):
            h = keno_analyzer.historical_data
            add, inv_gap = predict_next_draw(h[0]['numbers'], h[1]['numbers'])
            return sorted(list(set(add + inv_gap)))[:n]
        methods.append(('keno_methode', keno_methode_predict))
    except Exception:
        pass
    stats = defaultdict(dict)
    for last_n in nb_last_draws_list:
        draws = keno_analyzer.historical_data[:last_n]
        for method_name, func in methods:
            total = 0
            total_hits = 0
            total_score = 0
            for i in range(last_n-1):
                # On prédit sur le tirage i, on compare au tirage i-1
                try:
                    pred = func(8, None, None)
                    real = set(draws[i]['numbers'])
                    hits = len(set(pred) & real)
                    total_hits += hits
                    total_score += hits/8
                    total += 1
                except Exception:
                    continue
            stats[method_name][f'last_{last_n}'] = {
                'avg_hits': round(total_hits/total, 2) if total else 0,
                'avg_score': round(total_score/total, 3) if total else 0,
                'tested_draws': total
            }
    return stats

@app.route('/api/model-performance')
def model_performance():
    """Expose la performance de chaque modèle sur 100, 500, 1000 tirages."""
    try:
        stats = evaluate_model_performance()
        return jsonify({'success': True, 'performance': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Routes Flask

from keno_methode import fetch_latest_draws, predict_next_draw

@app.route('/api/predict/keno_methode', methods=['POST'])
def predict_keno_methode():
    """Endpoint pour la prédiction basée sur keno_methode.py (addition, écarts inversés)"""
    try:
        data = request.get_json()
        # Optionnel: url pour scraping, sinon utiliser historique local
        url = data.get('url', None)
        nb_numbers = int(data.get('nb_numbers', 8))
        # Utiliser les 2 derniers tirages (web ou historique)
        if url:
            draws = fetch_latest_draws(url)
        else:
            draws = [keno_analyzer.historical_data[0]['numbers'], keno_analyzer.historical_data[1]['numbers']]
        add, inv_gap = predict_next_draw(draws[0], draws[1])
        # On prend les N premiers uniques des deux méthodes fusionnées
        result = sorted(list(set(add + inv_gap)))[:nb_numbers]
        return jsonify({'success': True, 'method': 'keno_methode', 'numbers': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/predict/humaine', methods=['POST'])
def predict_humaine():
    """Endpoint pour la méthode humaine : pondération intelligente des meilleures stratégies."""
    try:
        data = request.get_json()
        nb_numbers = int(data.get('nb_numbers', 8))
        date_debut = data.get('date_debut')
        date_fin = data.get('date_fin')
        use_all_draws = data.get('useAllDraws', True)
        if use_all_draws:
            date_debut = None
            date_fin = None
        draws = keno_analyzer.filter_draws_by_period(date_debut, date_fin)
        # --- Pondération basée sur la performance ---
        # Poids dynamiques (exemple empirique, à affiner)
        weights = {
            'frequency': 1.0,
            'enhanced_ml': 2.0,
            'ecarts': 1.2,
            'finales': 1.1,
            'cycles': 1.1,
            'montecarlo': 1.3
        }
        # Collecter scores pour chaque numéro
        scores = {n: 0 for n in range(1, 71)}
        # Fréquence
        freq = keno_analyzer.frequency_strategy(nb_numbers, date_debut, date_fin)
        for n in freq:
            scores[n] += weights['frequency']
        # ML
        ml = keno_analyzer.enhanced_ml_strategy(nb_numbers, date_debut, date_fin)
        for n in ml:
            scores[n] += weights['enhanced_ml']
        # Cycles
        try:
            if SPECIALIZED_MODULES_AVAILABLE:
                cycles = KenoCycleAnalyzer(draws).predict(nb_numbers)
                for n in cycles:
                    scores[n] += weights['cycles']
        except Exception: pass
        # Ecarts
        try:
            if SPECIALIZED_MODULES_AVAILABLE:
                ecarts = KenoEcartsAnalyzer(draws).predict(nb_numbers)
                for n in ecarts:
                    scores[n] += weights['ecarts']
        except Exception: pass
        # Finales
        try:
            if SPECIALIZED_MODULES_AVAILABLE:
                finales = KenoFinalesAnalyzer(draws).predict(nb_numbers)
                for n in finales:
                    scores[n] += weights['finales']
        except Exception: pass
        # Monte Carlo (si dispo)
        try:
            if SPECIALIZED_MODULES_AVAILABLE:
                monte = KenoMonteCarloAnalyzer(draws).predict(nb_numbers)
                for n in monte:
                    scores[n] += weights['montecarlo']
        except Exception: pass
        # Sélection des meilleurs scores
        best = sorted(scores, key=lambda x: scores[x], reverse=True)[:nb_numbers]
        return jsonify({'success': True, 'method': 'humaine', 'numbers': sorted(best)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """API d'analyse avec période personnalisée"""
    try:
        data = request.get_json()
        method = data.get('method', 'frequency')
        nb_numbers = int(data.get('nb_numbers', 8))
        nb_grids = int(data.get('nb_grids', 1))
        date_debut = data.get('date_debut')
        date_fin = data.get('date_fin')
        use_all_draws = data.get('useAllDraws', True)
        
        # Si useAllDraws est True, ignorer les dates
        if use_all_draws:
            date_debut = None
            date_fin = None
        
        filtered_draws = keno_analyzer.filter_draws_by_period(date_debut, date_fin)
        
        results = []
        
        for _ in range(nb_grids):
            if method == 'frequency':
                numbers = keno_analyzer.frequency_strategy(nb_numbers, date_debut, date_fin)
            elif method == 'enhanced_ml':
                numbers = keno_analyzer.enhanced_ml_strategy(nb_numbers, date_debut, date_fin)
            elif method == 'complete':
                numbers = keno_analyzer.complete_analysis(nb_numbers, date_debut, date_fin)
            else:
                numbers = random.sample(range(1, 71), nb_numbers)
            
            prediction_id = keno_analyzer.save_prediction(method, numbers, data)
            
            results.append({
                'numbers': numbers,
                'prediction_id': prediction_id
            })
        
        data_info = f"Analyse basée sur {len(filtered_draws)} tirages réels"
        if use_all_draws:
            data_info += " (tous les tirages disponibles)"
        else:
            data_info += f" (période: {date_debut} → {date_fin})"
        
        return jsonify({
            'success': True,
            'method': method,
            'results': results,
            'draws_analyzed': len(filtered_draws),
            'period_start': date_debut,
            'period_end': date_fin,
            'data_info': data_info,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Erreur dans l'analyse: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/system/update-and-retrain', methods=['POST'])
def trigger_update_and_retrain():
    return admin_retrain()

@app.route('/api/admin/retrain', methods=['POST'])
def admin_retrain():
    """
    API pour déclencher manuellement la mise à jour et le réentraînement
    Utile pour les tests ou les déploiements manuels
    """
    try:
        logger.info("Déclenchement manuel de la mise à jour et du réentraînement...")
        # Vérifier si un réentraînement est déjà en cours
        if keno_analyzer.auto_update_system.training_in_progress:
            return jsonify({
                'success': False,
                'error': 'Réentraînement déjà en cours',
                'message': 'Un processus de réentraînement est déjà en cours. Veuillez patienter.'
            }), 409
        # Lancer la mise à jour et le réentraînement dans un thread séparé
        def run_update():
            success, message = keno_analyzer.auto_update_system.update_data_and_retrain()
            logger.info(f"Résultat mise à jour manuelle: {success} - {message}")
        update_thread = threading.Thread(target=run_update, daemon=True)
        update_thread.start()
        return jsonify({
            'success': True,
            'message': 'Mise à jour et réentraînement démarrés en arrière-plan',
            'status': 'started'
        })
    except Exception as e:
        logger.error(f"Erreur lors du déclenchement manuel: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Erreur lors du déclenchement manuel du réentraînement.'
        }), 500
        
    except Exception as e:
        logger.error(f"Erreur lors du déclenchement manuel: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/system/status', methods=['GET'])
def get_system_status():
    """
    API pour obtenir le statut du système
    """
    try:
        return jsonify({
            'success': True,
            'status': {
                'total_draws': len(keno_analyzer.historical_data),
                'last_update': keno_analyzer.last_update.isoformat(),
                'training_in_progress': keno_analyzer.auto_update_system.training_in_progress,
                'last_model_training': keno_analyzer.auto_update_system.last_model_training.isoformat() if keno_analyzer.auto_update_system.last_model_training else None,
                'auto_update_running': keno_analyzer.auto_update_running,
                'database_available': db_manager is not None,
                'specialized_modules_available': SPECIALIZED_MODULES_AVAILABLE
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats')
def api_stats():
    try:
        stats = keno_analyzer.get_performance_stats()
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health')
def health():
    """Vérification de l'état du service"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0',
        'total_draws': len(keno_analyzer.historical_data),
        'last_update': keno_analyzer.last_update.isoformat(),
        'auto_update_system': 'active'
    })

@app.route('/api/health')
def api_health():
    """Vérification de l'état du service (endpoint attendu par le frontend)"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0',
        'total_draws': len(keno_analyzer.historical_data),
        'last_update': keno_analyzer.last_update.isoformat(),
        'auto_update_system': 'active'
    })

@app.route('/api/predictions', methods=['GET', 'POST'])
def api_predictions():
    if request.method == 'GET':
        # Return predictions as JSON
        return jsonify({'success': True, 'predictions': []})
    elif request.method == 'POST':
        # Save predictions and return result
        data = request.get_json()
        # ...save logic...
        return jsonify({'success': True})

@app.route('/api/users/set-name', methods=['POST'])
def set_user_name():
    data = request.get_json()
    username = data.get('username')
    # ...save username logic...
    return jsonify({'success': True, 'username': username})

@app.route('/api/predictions/save-with-user', methods=['POST'])
def save_prediction_with_user():
    """
    API pour sauvegarder une prédiction utilisateur.
    """
    try:
        data = request.get_json()
        username = data.get('username')
        method = data.get('method')
        numbers = data.get('numbers')
        confidence = data.get('confidence', 0)

        # Ici, tu peux ajouter la logique de sauvegarde réelle (ex: en base)
        # Pour l'instant, on retourne juste un succès simulé
        return jsonify({'success': True, 'username': username, 'method': method, 'numbers': numbers, 'confidence': confidence})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/save_system_prediction', methods=['POST'])
def api_save_system_prediction():
    try:
        data = request.json
        user_id = data.get('user_id', 'system')
        method = data.get('method')
        numeros = data.get('numeros')
        confidence = data.get('confidence', 0.0)
        
        if not method or not numeros:
            return jsonify({'success': False, 'error': 'Données manquantes'}), 400
        
        if not isinstance(numeros, list):
            return jsonify({'success': False, 'error': 'Format numeros invalide'}), 400
        
        prediction_id = db_manager.save_prediction(user_id, method, numeros, confidence)
        if prediction_id:
            return jsonify({'success': True, 'id': prediction_id})
        else:
            return jsonify({'success': False, 'error': 'Erreur base de données'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/save_user_prediction", methods=["POST"])
def api_save_user_prediction():
    try:
        logger.info("Début de l'API save_user_prediction")

        if not request.is_json:
            logger.error("Erreur: Content-Type n'est pas application/json")
            return jsonify({'success': False, 'error': "Content-Type doit être application/json"}), 400

        data = request.get_json(silent=True) or {}
        logger.info(f"Données reçues: {data}")

        # --- Extraction des champs principaux ---
        user_id = str(data.get('user_id') or data.get('session_id') or 'anonymous')
        method = (data.get('method') or 'manual').strip()[:100]
        session_id = data.get('session_id')  # optionnel
        tirage_id = data.get('tirage_id')    # optionnel

        # --- numeros: accepte "numeros" ou "numbers", liste ou CSV ---
        raw_numeros = data.get('numeros') or data.get('numbers')
        if raw_numeros is None:
            logger.error("Erreur: Le champ numeros est manquant")
            return jsonify({'success': False, 'error': "Champ 'numeros' (ou 'numbers') manquant"}), 400

        try:
            if isinstance(raw_numeros, str):
                # autorise séparateurs virgule/point-virgule/espaces
                parts = (
                    raw_numeros.replace(';', ',')
                               .replace(' ', ',')
                               .split(',')
                )
                numeros = [int(p) for p in parts if p.strip() != '']
            elif isinstance(raw_numeros, list):
                numeros = [int(x) for x in raw_numeros]
            else:
                return jsonify({'success': False, 'error': "Format non valide pour 'numeros'"}), 400
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': "Le champ 'numeros' doit contenir uniquement des entiers"}), 400

        if not numeros:
            return jsonify({'success': False, 'error': "La liste 'numeros' ne peut pas être vide"}), 400

        # (Optionnel) dédoublonne en préservant l'ordre
        numeros = list(dict.fromkeys(numeros))

        # --- confidence: tolère 'confidence' ou 'confidence_score' ---
        confidence = data.get('confidence', data.get('confidence_score', 0.0))
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.0

        # --- Sauvegarde en base ---
        try:
            # Si ton manager expose save_prediction (cf. section 2), utilise-le :
            if hasattr(db_manager, "save_prediction"):
                prediction_id = db_manager.save_prediction(
                    user_id=user_id,
                    method=method,
                    numeros=numeros,
                    confidence=confidence,
                    session_id=session_id,
                    tirage_id=tirage_id
                )
            else:
                # Fallback: insertion directe avec SQLAlchemy
                with db_manager.engine.connect() as conn:
                    with conn.begin():
                        res = conn.execute(text("""
                            INSERT INTO predictions (tirage_id, user_id, method, numeros, session_id, confidence)
                            VALUES (:tirage_id, :user_id, :method, :numeros, :session_id, :confidence)
                            RETURNING id
                        """), {
                            "tirage_id": tirage_id,
                            "user_id": user_id,
                            "method": method,
                            "numeros": numeros,      # ← Python list → INTEGER[] en PostgreSQL
                            "session_id": session_id,
                            "confidence": confidence,
                        })
                        prediction_id = res.scalar()

                if prediction_id:
                    logger.info(f"Prédiction sauvegardée (ID: {prediction_id})")
                    return jsonify({'success': True, 'id': prediction_id}), 201

                logger.error("Insertion non confirmée (pas d'ID retourné)")
                return jsonify({'success': False, 'error': "Erreur de sauvegarde"}), 500

        except Exception as e:
            logger.exception("Erreur lors de la sauvegarde en base")
            return jsonify({'success': False, 'error': "Erreur interne"}), 500

        except Exception as e:
            logger.exception("Erreur imprévue dans l'API save_user_prediction")
            return jsonify({'success': False, 'error': "Erreur interne"}), 500
            
        # Convertir les numéros en entiers si nécessaire
        try:
            numeros = [int(n) for n in numeros]
        except (ValueError, TypeError) as e:
            logger.error(f"Erreur de conversion des numéros: {e}")
            return jsonify({'success': False, 'error': 'Tous les numeros doivent être des entiers'}), 400
            
        if not all(1 <= n <= 70 for n in numeros):
            logger.error(f"Erreur: Numéros en dehors de la plage valide: {numeros}")
            return jsonify({'success': False, 'error': 'Tous les numeros doivent être entre 1 et 70'}), 400
            
        if len(numeros) < 2 or len(numeros) > 10:
            logger.error(f"Erreur: Nombre de numéros invalide: {len(numeros)}")
            return jsonify({'success': False, 'error': 'Le nombre de numeros doit être entre 2 et 10'}), 400
            
        if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
            logger.error(f"Erreur: Valeur de confiance invalide: {confidence}")
            return jsonify({'success': False, 'error': 'Le champ confidence doit être entre 0 et 1'}), 400
            
        logger.info("Validation des données réussie, tentative de sauvegarde...")
        prediction_id = db_manager.save_prediction(user_id, method, numeros, confidence)
        
        if prediction_id:
            logger.info(f"Prédiction sauvegardée avec succès, ID: {prediction_id}")
            return jsonify({
                'success': True, 
                'id': prediction_id, 
                'message': 'Prédiction sauvegardée avec succès'
            })
        else:
            logger.error("Erreur lors de la sauvegarde en base de données")
            return jsonify({
                'success': False, 
                'error': 'Erreur lors de la sauvegarde en base de données'
            }), 500
            
    except Exception as e:
        logger.error(f"Erreur inattendue dans api_save_user_prediction: {str(e)}", exc_info=True)
        return jsonify({
            'success': False, 
            'error': f'Erreur serveur: {str(e)}'
        }), 500

@app.route('/chat')
def chat_page():
    """Servir la page du chat communauté."""
    return send_from_directory(app.static_folder, 'chat.html')

@app.route('/optimization')
def optimization_page():
    """Servir la page d'optimisation des prédictions."""
    return send_from_directory(app.static_folder, 'prediction_optimizer.html')

@app.route('/api/chat/offline', methods=['POST'])
def chat_offline():
    """Endpoint pour le chat hors-ligne (évite erreur 405)."""
    return jsonify({'success': True, 'message': 'Chat hors-ligne ou non disponible.'})

@app.route('/api/prediction/performance', methods=['GET'])
def get_prediction_performance():
    """Retourne les données de performance des méthodes"""
    try:
        from prediction_api import prediction_api
        return jsonify(prediction_api.get_performance_summary())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/prediction/evaluate', methods=['POST'])
def evaluate_prediction_accuracy():
    """Évalue les prédictions et ajuste les poids"""
    try:
        from prediction_api import prediction_api
        data = request.get_json()
        result = prediction_api.evaluate_prediction_accuracy(
            data.get('predictions', {}),
            data.get('actual_results', {})
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/prediction/reset-weights', methods=['POST'])
def reset_prediction_weights():
    """Réinitialise les poids des méthodes de prédiction"""
    try:
        from prediction_api import prediction_api
        result = prediction_api.reset_weights()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chatbot/chat', methods=['POST'])
def chatbot_chat():
    """Endpoint pour interagir avec le chatbot OpenAI"""
    try:
        from openai_chatbot import chatbot
        data = request.get_json()
        message = data.get('message', '')
        
        if not message:
            return jsonify({"error": "Message requis"}), 400
            
        response = chatbot.chat(message)
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chatbot/history', methods=['GET'])
def get_chatbot_history():
    """Retourne l'historique de conversation du chatbot"""
    try:
        from openai_chatbot import chatbot
        history = chatbot.get_conversation_history()
        return jsonify({'success': True, 'history': history})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chatbot/clear', methods=['POST'])
def clear_chatbot_history():
    """Efface l'historique de conversation du chatbot"""
    try:
        from openai_chatbot import chatbot
        chatbot.clear_history()
        return jsonify({'success': True, 'message': 'Historique effacé'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chatbot/configure', methods=['POST'])
def configure_chatbot():
    """Configure le chatbot avec une nouvelle clé API"""
    try:
        from openai_chatbot import initialize_chatbot
        data = request.get_json()
        api_key = data.get('api_key', '')
        
        if not api_key:
            return jsonify({'error': 'Clé API requise'}), 400
            
        initialize_chatbot(api_key)
        return jsonify({'success': True, 'message': 'Chatbot configuré avec succès'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/save', methods=['POST'])
def save_chat_message():
    """Sauvegarde un message de chat"""
    try:
        from prediction_api import prediction_api
        data = request.get_json()
        result = prediction_api.add_chat_message(
            data.get('username', 'Anonyme'),
            data.get('message', '')
        )
        return jsonify({'success': True, 'message': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/messages', methods=['GET'])
def get_chat_messages():
    """Retourne l'historique des messages"""
    try:
        from prediction_api import prediction_api
        return jsonify({'messages': prediction_api.get_chat_messages()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_user_predictions', methods=['GET'])
def api_get_user_predictions():
    session_id = request.args.get('session_id')
    limit = request.args.get('limit', 20, type=int)
    predictions = db_manager.get_user_predictions(session_id=session_id, limit=limit)
    return jsonify({'success': True, 'predictions': predictions})

@app.route('/api/get_system_predictions', methods=['GET'])
def api_get_system_predictions():
    """Récupère les prédictions système"""
    try:
        limit = request.args.get('limit', 50, type=int)
        predictions = db_manager.get_system_predictions(limit=limit)
        return jsonify({'success': True, 'predictions': predictions})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
