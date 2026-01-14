# 🎯 Keno Analyzer Pro - Intelligence Artificielle & Analyse de Données

![Version](https://img.shields.io/badge/Version-2.1.0-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-green)
![Framework](https://img.shields.io/badge/Flask-3.x-orange)

Keno Analyzer Pro est une plateforme web avancée dédiée à l'analyse algorithmique des tirages Keno. Combinant Machine Learning, simulations Monte Carlo et analyses statistiques classiques, elle offre un outil complet pour les passionnés et analystes.

---

## 📋 Table des Matières
1. [Fonctionnalités Clés](#-fonctionnalités-clés)
2. [Spécifications Techniques](#-spécifications-techniques)
3. [Installation Rapide](#-installation-rapide)
4. [Gestion des Bases de Données](#-gestion-des-bases-de-données)
5. [Intelligence Artificielle](#-intelligence-artificielle)
6. [Administration & Sécurité](#-administration--sécurité)
7. [Avertissement](#️-avertissement)

---

## ✨ Fonctionnalités Clés

- **8 Méthodes d'Analyse** : Fréquences, Écarts, Cycles, Mixte, Machine Learning, Fibonacci, Sommes et Monte Carlo.
- **Analyse des Finales & Écarts** : Détection fine des motifs et tendances.
- **Support Keno 2025** : Entièrement compatible avec le nouveau format FDJ (16/56).
- **Interface Progressive** : Tableau de bord interactif avec mode sombre/clair.
- **Authentification Sécurisée** : Système 2FA (SendGrid) et gestion poussée des accès.

---

## 🛠 Spécifications Techniques

- **Backend** : Flask 2.3.3 (compatible 3.x)
- **IA** : Scikit-Learn (Random Forest, GB), NumPy, Pandas
- **Base de Données** : PostgreSQL (Défaut) ou MySQL (Supporté) via SQLAlchemy
- **Communication** : SendGrid pour les emails de récupération et 2FA
- **Système** : Adapté pour Python 3.10 (recommandé 3.13)

---

## 🚀 Installation Rapide (Windows)

### Méthode Automatique
Double-cliquez sur `start.bat`. Le script s'occupe de tout :
- Création de l'environnement virtuel (`venv`).
- Installation des dépendances.
- Configuration initiale et lancement.

### Méthode Manuelle
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Configurez votre DATABASE_URL dans .env
cd src
python app.py
```

---

## 🗄️ Gestion des Bases de Données

Le système supporte nativement **PostgreSQL** et **MySQL**.

### Configuration MySQL
Si vous préférez MySQL, installez le driver et modifiez votre `.env` :
```bash
pip install pymysql
```
```env
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/keno_analyzer
```
*Le système détecte automatiquement le type de base de données à l'initialisation.*

---

## 🤖 Intelligence Artificielle

L'IA intégrée utilise des modèles **Random Forest** et **Gradient Boosting** pour prédire les probabilités de sortie.
- **Apprentissage** : Se base sur les 50 à 100 derniers tirages.
- **Optimisation** : Recherche automatique des hyperparamètres pour chaque nouvel entraînement.
- **Multi-Modèles** : Possibilité de comparer plusieurs modèles depuis l'interface admin.

---

## 🔒 Administration & Sécurité

- **Dashboard Admin** : Gestion des utilisateurs, monitoring des performances et lancement manuel des entraînements.
- **Secrets & API** : Toutes les données sensibles (clés SendGrid, DB URL) sont gérées exclusivement via le fichier `.env`.
- **2FA** : Sécurisation des comptes via code de vérification par email.

---

## ⚠️ Avertissement

Ce logiciel est un outil d'analyse statistique et de divertissement. Le Keno est un jeu de pur hasard. Aucune méthode, aussi avancée soit-elle, ne peut garantir de gain régulier ou certain. **Jouez de manière responsable.**

---
**Développeur** : Aniss  
**Statut** : Version 2.1.0 - Janvier 2026
