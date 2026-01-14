import openai
import json
import os
from datetime import datetime

class OpenAIChatbot:
    def __init__(self, api_key=None):
        """Initialise le chatbot OpenAI"""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if self.api_key:
            openai.api_key = self.api_key
        self.conversation_history = []
        
    def set_api_key(self, api_key):
        """Met à jour la clé API"""
        self.api_key = api_key
        openai.api_key = api_key
        
    def chat(self, message, context=None):
        """Envoie un message au chatbot et retourne la réponse exclusivement pour Keno FDJ"""
        try:
            if not self.api_key:
                return {"error": "Clé API OpenAI non configurée"}
                
            # Vérifier si le message est lié au Keno FDJ
            keno_keywords = ['keno', 'fdj', 'française des jeux', 'loterie', 'tirage', 'numéros', 'gains', 'mise', 'pronostics']
            message_lower = message.lower()
            
            # Toujours répondre sur le Keno FDJ
            system_message = {
                "role": "system",
                "content": """Tu es Assistant IA - Chatbot kenoai, un assistant spécialisé EXCLUSIVEMENT dans le Keno FDJ (Française des Jeux). Ta mission est :

1. **EXCLUSIVITÉ KENO FDJ**: Répondre UNIQUEMENT aux questions concernant le Keno FDJ
2. **EXPLICATION DES BUTS**: Toujours expliquer que le Keno FDJ est un jeu de tirage où les joueurs choisissent 2-10 numéros parmi 70, avec des gains selon les numéros trouvés
3. **BUT DE LA LOTERIE**: Le but principal est de divertir les joueurs et leur permettre de tester leur chance avec des gains potentiels
4. **PAS DE QUESTIONS HORS SUJET**: Refuser poliment toute question non liée au Keno FDJ

Structure des réponses:
- Toujours mentionner que c'est le Keno FDJ
- Expliquer les règles du jeu
- Mentionner les buts de divertissement et gains potentiels
- Garder les réponses concises et informatives"""
            }
            
            # Préparer les messages avec le contexte système
            messages = [system_message]
            messages.extend(self.conversation_history)
            messages.append({"role": "user", "content": message})
            
            response = openai.ChatCompletion.create(
                model="gpt-4.1",
                messages=messages,
                max_tokens=300,
                temperature=0.7
            )
            
            bot_response = response.choices[0].message.content
            
            # Limiter l'historique à 10 messages
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]
                
            used_requests = self.get_user_usage_count(user_id)
            remaining = self.max_requests_per_user - used_requests
            
            # Message d'accueil personnalisé
            welcome_message = """📊 Assistant Chabot KenoAI
0/3 requêtes utilisées
Il vous reste 3 requêtes aujourd'hui
🎯 Mission du Chatbot
Assistant IA - Chatbot kenoai est spécialisé EXCLUSIVEMENT dans le Keno FDJ (Française des Jeux).

📋 But du Keno FDJ :
• Jeu de tirage où vous choisissez 2 à 10 numéros parmi 70
• Gains selon le nombre de numéros trouvés
• Objectif : Divertir et permettre de tester votre chance avec des gains potentiels

🚫 Hors sujet : Le chatbot refusera poliment toute question non liée au Keno FDJ

🤖 Bienvenue ! Posez-moi une question sur le Keno FDJ, les règles ou les stratégies."""
            
            return welcome_message
            
        except Exception as e:
            return {"error": str(e)}
            
    def get_conversation_history(self):
        """Retourne l'historique de conversation"""
        return self.conversation_history
        
    def clear_history(self):
        """Efface l'historique de conversation"""
        self.conversation_history = []

# Instance globale du chatbot
chatbot = OpenAIChatbot()

def initialize_chatbot(api_key):
    """Initialise le chatbot avec une clé API"""
    global chatbot
    chatbot = OpenAIChatbot(api_key)
    return chatbot
