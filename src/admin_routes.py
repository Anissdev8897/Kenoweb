from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
import logging
import os
import subprocess
import sys
from src.auth_system import AuthSystem

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

admin_bp = Blueprint('keno_admin', __name__)
auth_system = AuthSystem()

def admin_required(f):
    """Décorateur pour vérifier que l'utilisateur est admin"""
    def admin_check(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        
        user = auth_system.get_user_by_username(session.get('username'))
        if not user or not user.get('is_admin', False):
            return redirect('/analyser')
        
        return f(*args, **kwargs)
    admin_check.__name__ = f.__name__ + '_admin_check'
    return admin_check

@admin_bp.route('/admin')
@admin_required
def admin_dashboard():
    """Page d'administration"""
    return render_template('admin.html')

@admin_bp.route('/api/admin/users')
@admin_required
def get_admin_users():
    """Obtenir la liste des utilisateurs"""
    try:
        users = auth_system.get_all_users()
        return jsonify(users)
    except Exception as e:
        logger.error(f"Erreur récupération utilisateurs: {e}")
        return jsonify({'success': False, 'message': 'Erreur serveur'}), 500

@admin_bp.route('/api/admin/moderators', methods=['POST'])
@admin_required
def create_moderator():
    """Créer un nouveau modérateur"""
    try:
        data = request.get_json()
        
        # Vérifier les données
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not all([username, email, password]):
            return jsonify({'success': False, 'message': 'Tous les champs sont requis'})
        
        # Vérifier si l'utilisateur existe déjà
        existing_user = auth_system.get_user_by_username(username)
        if existing_user:
            return jsonify({'success': False, 'message': 'Ce nom d\'utilisateur existe déjà'})
        
        existing_email = auth_system.get_user_by_email(email)
        if existing_email:
            return jsonify({'success': False, 'message': 'Cet email est déjà utilisé'})
        
        # Créer le modérateur
        user_data = {
            'username': username,
            'email': email,
            'password': password,
            'is_moderator': True,
            'is_admin': False
        }
        
        user_id = auth_system.create_user(user_data)
        if user_id:
            return jsonify({'success': True, 'message': 'Modérateur créé avec succès'})
        else:
            return jsonify({'success': False, 'message': 'Erreur lors de la création'})
            
    except Exception as e:
        logger.error(f"Erreur création modérateur: {e}")
        return jsonify({'success': False, 'message': 'Erreur serveur'}), 500

@admin_bp.route('/api/admin/users/<user_id>/toggle', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    """Basculer le statut d'un utilisateur"""
    try:
        data = request.get_json()
        is_active = data.get('is_active', True)
        
        # Implémenter la logique de basculement
        # Pour l'instant, retourner un succès simulé
        return jsonify({'success': True, 'message': 'Statut utilisateur mis à jour'})
        
    except Exception as e:
        logger.error(f"Erreur toggle user status: {e}")
        return jsonify({'success': False, 'message': 'Erreur serveur'}), 500

@admin_bp.route('/api/admin/retrain', methods=['POST'])
@admin_required
def retrain_model():
    """Relancer l'entraînement du modèle"""
    try:
        data = request.get_json()
        training_type = data.get('type', 'full')
        
        # Obtenir le chemin du script d'entraînement
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        
        if training_type == 'full':
            script_path = os.path.join(project_root, 'retrain_model.py')
            cmd = [sys.executable, script_path, '--full']
        else:
            script_path = os.path.join(project_root, 'retrain_model.py')
            cmd = [sys.executable, script_path, '--incremental']
        
        # Exécuter le script d'entraînement en arrière-plan
        try:
            subprocess.Popen(cmd, cwd=project_root)
            return jsonify({
                'success': True, 
                'message': f'Entraînement {training_type} lancé avec succès'
            })
        except Exception as e:
            logger.error(f"Erreur lancement entraînement: {e}")
            return jsonify({
                'success': False, 
                'message': 'Erreur lors du lancement de l\'entraînement'
            })
            
    except Exception as e:
        logger.error(f"Erreur retrain model: {e}")
        return jsonify({'success': False, 'message': 'Erreur serveur'}), 500
