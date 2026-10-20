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

- **Probabilités exactes** : Calcul par loi hypergéométrique (arithmétique exacte) des chances réelles par grille — module `src/keno_probabilities.py`.
- **Backtest honnête** : Mesure walk-forward de l'avantage réel de chaque stratégie face au hasard — module `src/keno_backtest_honest.py`.
- **8 Méthodes d'Analyse statistique** : Fréquences, Écarts, Cycles, Mixte, Machine Learning, Fibonacci, Sommes et Monte Carlo.
- **Support du nouveau Keno FDJ** : Format en vigueur depuis le **3 novembre 2025** — grille de **56 numéros, 16 tirés**, un tirage par jour à 20h (voir `src/keno_config.py`).
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

## 🤖 Intelligence Artificielle (ce qu'elle fait vraiment)

L'IA intégrée (**Random Forest**, **Gradient Boosting**) et les analyses statistiques
produisent des indicateurs descriptifs sur l'historique des tirages (fréquences,
écarts, motifs). Elles **ne prédisent pas** le prochain tirage et ne créent aucun
avantage : un tirage de Keno est aléatoire et sans mémoire, chaque numéro gardant la
même probabilité de sortir à chaque fois, indépendamment du passé.

Le module `keno_backtest_honest.py` le démontre sur l'historique réel : testées en
walk-forward sur plusieurs milliers de tirages, les stratégies « numéros chauds /
froids / en retard » obtiennent en moyenne autant (et parfois moins) de bons numéros
que le pur hasard. L'outil sert donc à **comprendre les chances réelles**, pas à les
battre.

- **Apprentissage** : Se base sur les 50 à 100 derniers tirages.
- **Optimisation** : Recherche automatique des hyperparamètres pour chaque nouvel entraînement.
- **Multi-Modèles** : Possibilité de comparer plusieurs modèles depuis l'interface admin.

### Calculer ses chances réelles

```bash
cd src
python3 keno_probabilities.py        # probabilités exactes par grille (56/16)
python3 keno_backtest_honest.py      # mesure l'avantage réel des stratégies
python3 test_keno_probabilities.py   # valide l'exactitude des calculs
```

---

## 🔒 Administration & Sécurité

- **Dashboard Admin** : Gestion des utilisateurs, monitoring des performances et lancement manuel des entraînements.
- **Secrets & API** : Toutes les données sensibles (clés SendGrid, DB URL) sont gérées exclusivement via le fichier `.env`.
- **2FA** : Sécurisation des comptes via code de vérification par email.

---

## ⚠️ Avertissement

Ce logiciel est un outil d'analyse statistique et de divertissement. Le Keno est un
**jeu de pur hasard**. Aucune méthode, aussi avancée soit-elle (statistiques, IA,
machine learning), ne peut prédire un tirage ni garantir un gain : les tirages sont
indépendants et sans mémoire. Le taux de retour au joueur est structurellement
inférieur à 100 %, la maison garde l'avantage sur la durée.

Ne présentez jamais cet outil comme un moyen de « prédire » ou « garantir » des gains :
ce serait trompeur pour les utilisateurs et contraire à la réglementation française sur
les jeux d'argent (ANJ). **Jouez de manière responsable.** En cas de besoin, aide
disponible au **09 74 75 13 13** (Joueurs Info Service, appel non surtaxé).

---
**Développeur** : Aniss  
**Statut** : Version 2.1.0
