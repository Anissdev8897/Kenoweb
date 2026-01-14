from flask import Blueprint, jsonify, request
import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from models.user import User, db
except ImportError:
    # Fallback si models.user n'existe pas ou si db n'est pas défini
    User = None
    db = None

user_bp = Blueprint('user', __name__)

@user_bp.route('/users', methods=['GET'])
def get_users():
    if User is None or db is None:
        return jsonify({"error": "Modèle utilisateur non disponible"}), 503
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@user_bp.route('/users', methods=['POST'])
def create_user():
    if User is None or db is None:
        return jsonify({"error": "Modèle utilisateur non disponible"}), 503
    data = request.json
    user = User(username=data['username'], email=data['email'])
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201

@user_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    if User is None or db is None:
        return jsonify({"error": "Modèle utilisateur non disponible"}), 503
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())

@user_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    if User is None or db is None:
        return jsonify({"error": "Modèle utilisateur non disponible"}), 503
    user = User.query.get_or_404(user_id)
    data = request.json
    user.username = data.get('username', user.username)
    user.email = data.get('email', user.email)
    db.session.commit()
    return jsonify(user.to_dict())

@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    if User is None or db is None:
        return jsonify({"error": "Modèle utilisateur non disponible"}), 503
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return '', 204
