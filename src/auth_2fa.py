import os
import random
import string
import time
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from database_manager_postgresql import PostgreSQLManager

class TwoFactorAuth:
    def __init__(self):
        self.sg = SendGridAPIClient(os.environ.get("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"))
        self.db = PostgreSQLManager()  # Création directe d'une instance
        self.token_expiry_minutes = 15

    def generate_reset_token(self, email):
        """Génère un jeton de réinitialisation unique"""
        # Vérifier si l'email existe
        user = self.db.get_user_by_email(email)
        if not user:
            return None

        # Générer un token alphanumérique de 8 caractères
        token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        expiry = datetime.utcnow() + timedelta(minutes=self.token_expiry_minutes)

        # Sauvegarder le token dans la base de données
        with self.db.engine.connect() as conn:
            conn.execute(
                """
                INSERT INTO password_reset_tokens (user_id, token, expires_at)
                VALUES (:user_id, :token, :expires_at)
                ON CONFLICT (user_id) 
                DO UPDATE SET token = :token, 
                             expires_at = :expires_at,
                             created_at = CURRENT_TIMESTAMP
                """,
                {"user_id": user['id'], "token": token, "expires_at": expiry}
            )
            conn.commit()

        return token

    def send_reset_email(self, email, token):
        """Envoie l'email de réinitialisation avec le code 2FA"""
        message = Mail(
            from_email='no-reply@keno-analyzer.com',
            to_emails=email,
            subject='Réinitialisation de votre mot de passe - Keno Analyzer',
            html_content=f"""
            <h2>Réinitialisation de votre mot de passe</h2>
            <p>Voici votre code de vérification :</p>
            <h3 style="font-size: 24px; letter-spacing: 4px;">{token}</h3>
            <p>Ce code expirera dans {self.token_expiry_minutes} minutes.</p>
            <p>Si vous n'avez pas demandé de réinitialisation, veuillez ignorer cet email.</p>
            """
        )
        
        try:
            self.sg.send(message)
            return True
        except Exception as e:
            print(f"Erreur lors de l'envoi de l'email : {e}")
            return False

    def verify_token(self, email, token):
        """Vérifie si le token est valide"""
        with self.db.engine.connect() as conn:
            result = conn.execute(
                """
                SELECT * FROM password_reset_tokens prt
                JOIN users u ON prt.user_id = u.id
                WHERE u.email = :email 
                AND prt.token = :token 
                AND prt.expires_at > CURRENT_TIMESTAMP
                AND prt.used = FALSE
                """,
                {"email": email, "token": token}
            ).fetchone()
            
            if result:
                return True
            return False

    def mark_token_used(self, email, token):
        """Marque un token comme utilisé"""
        with self.db.engine.connect() as conn:
            conn.execute(
                """
                UPDATE password_reset_tokens
                SET used = TRUE
                WHERE token = :token
                AND user_id IN (SELECT id FROM users WHERE email = :email)
                """,
                {"email": email, "token": token}
            )
            conn.commit()

    def reset_password(self, email, token, new_password):
        """Réinitialise le mot de passe si le token est valide"""
        if not self.verify_token(email, token):
            return False
            
        # Mettre à jour le mot de passe
        with self.db.engine.connect() as conn:
            conn.execute(
                """
                UPDATE users 
                SET password_hash = crypt(:new_password, gen_salt('bf'))
                WHERE email = :email
                """,
                {"email": email, "new_password": new_password}
            )
            
            # Marquer le token comme utilisé
            self.mark_token_used(email, token)
            conn.commit()
            
        return True

# Utilisation dans l'application Flask
# from auth_2fa import TwoFactorAuth
# two_fa = TwoFactorAuth()
