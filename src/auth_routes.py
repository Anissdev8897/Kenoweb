from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import os
import sys

# Ajouter le chemin src au sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from auth_system import AuthSystem

auth_bp = Blueprint('keno_auth', __name__, url_prefix='/auth')
auth_system = AuthSystem()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Veuillez remplir tous les champs', 'error')
            return render_template('index.html')
        
        user = auth_system.authenticate_user(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            session['is_moderator'] = user['is_moderator']
            
            flash('Connexion réussie!', 'success')
            return redirect('/analyser')
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect', 'error')
    
    return render_template('index.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
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

@auth_bp.route('/logout')
def logout():
    """Déconnexion"""
    session.clear()
    flash('Vous avez été déconnecté', 'success')
    return redirect('/login')

@auth_bp.route('/current_user')
def current_user():
    """Obtenir l'utilisateur actuel"""
    if 'user_id' in session:
        return jsonify({
            'username': session.get('username'),
            'is_admin': session.get('is_admin', False),
            'is_moderator': session.get('is_moderator', False)
        })
    return jsonify({'error': 'Non connecté'}), 401
