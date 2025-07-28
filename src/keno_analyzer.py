#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyseur avancé pour le Keno - Prédiction de combinaisons optimisées
Adapté des méthodes développées pour le Loto
Objectif: Générer des combinaisons de 4-5 numéros pour gains ~50€
"""

import pandas as pd
import numpy as np
from collections import Counter, defaultdict
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import json
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
import joblib
import warnings
warnings.filterwarnings('ignore')

class KenoAnalyzer:
    def __init__(self, csv_file="tirages_keno.csv"):
        self.csv_file = csv_file
        self.df = None
        self.config = {
            'fenetre_analyse': 50,  # Nombre de tirages récents à analyser
            'nb_numeros_chauds': 15,
            'nb_numeros_froids': 15,
            'nb_combinaisons': 10,
            'mise_par_grille': 1,  # 1€ par grille
            'objectif_gain': 50,   # Objectif de gain en euros
            'nb_numeros_par_grille': 5,  # 4 ou 5 numéros par grille
            'repertoire_sortie': 'resultats_keno',
            'utiliser_ml': True,
            'sauvegarder_modeles': True
        }
        
        # Statistiques globales
        self.stats_globales = {}
        self.stats_fenetre = {}
        self.numeros_chauds = []
        self.numeros_froids = []
        self.ecarts_globaux = {}
        
        # Modèles ML
        self.rf_model = None
        self.scaler = None
        
        # Créer le répertoire de sortie
        os.makedirs(self.config['repertoire_sortie'], exist_ok=True)
    
    def charger_donnees(self):
    """Charge et prétraite les données des tirages depuis la base PostgreSQL (table tirages_keno)"""
    print("Chargement des données depuis la base PostgreSQL...")
    import sqlalchemy
    from sqlalchemy import create_engine
    from config import DATABASE_CONFIG
    try:
        engine = create_engine(DATABASE_CONFIG['postgresql_url'])
        # On suppose la table 'tirages_keno' avec les colonnes : id, date, date_brute, numero_1 ... numero_20, multiplicateur, joker
        query = "SELECT * FROM tirages_keno ORDER BY date ASC;"
        self.df = pd.read_sql(query, engine)
        print(f"Données chargées: {len(self.df)} tirages")
        # Convertir la date
        self.df['date_parsed'] = pd.to_datetime(self.df['date'], format='%d/%m/%Y')
        # Extraire les numéros dans une liste
        numero_cols = [f'numero_{i}' for i in range(1, 21)]
        self.df['numeros'] = self.df[numero_cols].apply(lambda row: sorted([int(x) for x in row if x is not None]), axis=1)
        # Trier par date (plus ancien en premier pour l'analyse chronologique)
        self.df = self.df.sort_values('date_parsed')
        self.df = self.df.reset_index(drop=True)
        print(f"Période couverte: {self.df['date'].iloc[0]} à {self.df['date'].iloc[-1]}")
        return True
    except Exception as e:
        print(f"Erreur lors du chargement SQL: {e}")
        return False
    
    def calculer_statistiques_globales(self):
        """Calcule les statistiques sur tous les tirages"""
        print("Calcul des statistiques globales...")
        
        # Compter les fréquences de chaque numéro
        tous_numeros = []
        for numeros in self.df['numeros']:
            tous_numeros.extend(numeros)
        
        self.stats_globales['frequences'] = Counter(tous_numeros)
        self.stats_globales['total_tirages'] = len(self.df)
        
        # Calculer les écarts actuels (nombre de tirages depuis dernière apparition)
        self.ecarts_globaux = {}
        for numero in range(1, 71):
            # Trouver le dernier tirage où ce numéro est apparu
            derniere_apparition = -1
            for i in range(len(self.df) - 1, -1, -1):
                if numero in self.df.iloc[i]['numeros']:
                    derniere_apparition = i
                    break
            
            if derniere_apparition >= 0:
                self.ecarts_globaux[numero] = len(self.df) - 1 - derniere_apparition
            else:
                self.ecarts_globaux[numero] = len(self.df)
        
        print(f"Statistiques calculées sur {self.stats_globales['total_tirages']} tirages")
    
    def calculer_statistiques_fenetre(self):
        """Calcule les statistiques sur la fenêtre récente"""
        print(f"Calcul des statistiques sur les {self.config['fenetre_analyse']} derniers tirages...")
        
        # Prendre les derniers tirages
        fenetre_df = self.df.tail(self.config['fenetre_analyse'])
        
        # Compter les fréquences
        numeros_fenetre = []
        for numeros in fenetre_df['numeros']:
            numeros_fenetre.extend(numeros)
        
        self.stats_fenetre['frequences'] = Counter(numeros_fenetre)
        self.stats_fenetre['total_tirages'] = len(fenetre_df)
        
        # Identifier numéros chauds et froids
        freq_sorted = sorted(self.stats_fenetre['frequences'].items(), key=lambda x: x[1], reverse=True)
        
        self.numeros_chauds = [num for num, freq in freq_sorted[:self.config['nb_numeros_chauds']]]
        self.numeros_froids = [num for num, freq in freq_sorted[-self.config['nb_numeros_froids']:]]
        
        print(f"Numéros chauds: {self.numeros_chauds[:10]}")
        print(f"Numéros froids: {self.numeros_froids[:10]}")
    
    def analyser_patterns(self):
        """Analyse les patterns dans les tirages"""
        print("Analyse des patterns...")
        
        patterns = {
            'sommes': [],
            'parite': [],
            'sequences': [],
            'repartition_dizaines': []
        }
        
        for numeros in self.df['numeros']:
            # Somme des numéros
            patterns['sommes'].append(sum(numeros))
            
            # Parité (nombre de pairs/impairs)
            pairs = sum(1 for n in numeros if n % 2 == 0)
            patterns['parite'].append(f"{pairs}P-{20-pairs}I")
            
            # Séquences consécutives
            sequences = 0
            numeros_sorted = sorted(numeros)
            for i in range(len(numeros_sorted) - 1):
                if numeros_sorted[i+1] == numeros_sorted[i] + 1:
                    sequences += 1
            patterns['sequences'].append(sequences)
            
            # Répartition par dizaines
            dizaines = [0] * 7  # 1-10, 11-20, ..., 61-70
            for num in numeros:
                dizaine = min((num - 1) // 10, 6)
                dizaines[dizaine] += 1
            patterns['repartition_dizaines'].append(dizaines)
        
        self.patterns = patterns
        
        # Statistiques des patterns
        print(f"Somme moyenne: {np.mean(patterns['sommes']):.1f}")
        print(f"Parité la plus fréquente: {Counter(patterns['parite']).most_common(1)[0]}")
        print(f"Séquences moyennes: {np.mean(patterns['sequences']):.1f}")
    
    def entrainer_modele_ml(self):
        """Entraîne un modèle de machine learning pour la prédiction"""
        if not self.config['utiliser_ml'] or len(self.df) < 100:
            print("ML désactivé ou pas assez de données")
            return
        
        print("Entraînement du modèle ML...")
        
        # Préparer les features et targets
        X, y = self.preparer_donnees_ml()
        
        if len(X) < 50:
            print("Pas assez de données pour l'entraînement ML")
            return
        
        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Normalisation
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Entraînement
        self.rf_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        
        self.rf_model.fit(X_train_scaled, y_train)
        
        # Évaluation
        y_pred = self.rf_model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"Précision du modèle: {accuracy:.3f}")
        
        # Sauvegarder les modèles
        if self.config['sauvegarder_modeles']:
            joblib.dump(self.rf_model, f"{self.config['repertoire_sortie']}/keno_rf_model.joblib")
            joblib.dump(self.scaler, f"{self.config['repertoire_sortie']}/keno_scaler.joblib")
    
    def preparer_donnees_ml(self, fenetre_features=10):
        """Prépare les données pour l'entraînement ML"""
        X, y = [], []
        
        for i in range(fenetre_features, len(self.df)):
            # Features: statistiques des tirages précédents
            features = []
            
            # Fenêtre des tirages précédents
            fenetre = self.df.iloc[i-fenetre_features:i]
            
            # Fréquences des numéros dans la fenêtre
            freq_fenetre = Counter()
            for numeros in fenetre['numeros']:
                freq_fenetre.update(numeros)
            
            # Features: fréquence de chaque numéro (1-70)
            for num in range(1, 71):
                features.append(freq_fenetre.get(num, 0))
            
            # Features additionnelles
            derniers_numeros = fenetre['numeros'].iloc[-1]
            features.extend([
                sum(derniers_numeros),  # Somme du dernier tirage
                len([n for n in derniers_numeros if n % 2 == 0]),  # Nb pairs
                np.std(derniers_numeros),  # Écart-type
            ])
            
            X.append(features)
            
            # Target: numéros du tirage suivant (multi-label)
            target = [1 if num in self.df.iloc[i]['numeros'] else 0 for num in range(1, 71)]
            y.append(target)
        
        return np.array(X), np.array(y)
    
    def predire_prochains_numeros(self):
        """Prédit les numéros les plus probables pour le prochain tirage"""
        print("Prédiction des prochains numéros...")
        
        scores_finaux = {}
        
        # 1. Scores basés sur les fréquences récentes
        for numero in range(1, 71):
            freq_recente = self.stats_fenetre['frequences'].get(numero, 0)
            score_freq = freq_recente / self.stats_fenetre['total_tirages']
            
            # 2. Score basé sur l'écart (numéros "dus")
            ecart = self.ecarts_globaux.get(numero, 0)
            # Plus l'écart est grand, plus le score est élevé (pondération Fibonacci)
            score_ecart = min(ecart / 10, 1.0)  # Normaliser
            
            # 3. Score ML si disponible
            score_ml = 0
            if self.rf_model and self.scaler:
                try:
                    # Préparer les features pour la prédiction
                    features = self.preparer_features_prediction()
                    if features is not None:
                        features_scaled = self.scaler.transform([features])
                        probas = self.rf_model.predict_proba(features_scaled)
                        if len(probas) > 0 and len(probas[0]) > 1:
                            score_ml = probas[0][1]  # Probabilité de sortie
                except:
                    score_ml = 0
            
            # Score final combiné
            scores_finaux[numero] = (
                0.4 * score_freq +
                0.3 * score_ecart +
                0.3 * score_ml
            )
        
        # Trier par score décroissant
        numeros_predits = sorted(scores_finaux.items(), key=lambda x: x[1], reverse=True)
        
        return numeros_predits
    
    def preparer_features_prediction(self):
        """Prépare les features pour la prédiction du prochain tirage"""
        if len(self.df) < 10:
            return None
        
        # Utiliser les 10 derniers tirages
        fenetre = self.df.tail(10)
        
        features = []
        
        # Fréquences des numéros dans la fenêtre
        freq_fenetre = Counter()
        for numeros in fenetre['numeros']:
            freq_fenetre.update(numeros)
        
        for num in range(1, 71):
            features.append(freq_fenetre.get(num, 0))
        
        # Features additionnelles
        derniers_numeros = fenetre['numeros'].iloc[-1]
        features.extend([
            sum(derniers_numeros),
            len([n for n in derniers_numeros if n % 2 == 0]),
            np.std(derniers_numeros),
        ])
        
        return features
    
    def generer_combinaisons_optimisees(self, numeros_predits):
        """Génère des combinaisons optimisées pour maximiser les gains"""
        print(f"Génération de {self.config['nb_combinaisons']} combinaisons optimisées...")
        
        combinaisons = []
        nb_numeros = self.config['nb_numeros_par_grille']
        
        # Stratégie 1: Top scores
        top_numeros = [num for num, score in numeros_predits[:20]]
        
        # Stratégie 2: Mix chauds/froids
        mix_numeros = self.numeros_chauds[:10] + self.numeros_froids[:10]
        
        # Stratégie 3: Numéros avec grands écarts
        ecarts_sorted = sorted(self.ecarts_globaux.items(), key=lambda x: x[1], reverse=True)
        ecart_numeros = [num for num, ecart in ecarts_sorted[:15]]
        
        strategies = [
            ("Top Scores", top_numeros),
            ("Mix Chaud/Froid", mix_numeros),
            ("Grands Écarts", ecart_numeros),
            ("Équilibré", top_numeros[:7] + self.numeros_chauds[:7] + ecart_numeros[:6])
        ]
        
        for strategie, pool_numeros in strategies:
            # Générer plusieurs combinaisons par stratégie
            for i in range(self.config['nb_combinaisons'] // len(strategies) + 1):
                if len(combinaisons) >= self.config['nb_combinaisons']:
                    break
                
                # Sélectionner les numéros
                if len(pool_numeros) >= nb_numeros:
                    # Prendre les meilleurs + quelques aléatoires pour la diversité
                    base = pool_numeros[:nb_numeros-1]
                    complement = np.random.choice(
                        [n for n in pool_numeros[nb_numeros-1:] if n not in base],
                        size=1,
                        replace=False
                    )
                    combinaison = sorted(base + complement.tolist())
                else:
                    combinaison = sorted(pool_numeros[:nb_numeros])
                
                if combinaison not in combinaisons:
                    combinaisons.append({
                        'numeros': combinaison,
                        'strategie': strategie,
                        'score_moyen': np.mean([dict(numeros_predits)[n] for n in combinaison])
                    })
        
        # Trier par score moyen décroissant
        combinaisons = sorted(combinaisons, key=lambda x: x['score_moyen'], reverse=True)
        
        return combinaisons[:self.config['nb_combinaisons']]
    
    def calculer_gains_potentiels(self, combinaisons):
        """Calcule les gains potentiels selon les règles Keno"""
        # Barème Keno pour 4 et 5 numéros (approximatif)
        bareme = {
            4: {2: 2, 3: 22, 4: 72},  # 4 numéros: 2 bons=2€, 3 bons=22€, 4 bons=72€
            5: {3: 2, 4: 12, 5: 320}  # 5 numéros: 3 bons=2€, 4 bons=12€, 5 bons=320€
        }
        
        for combinaison in combinaisons:
            nb_numeros = len(combinaison['numeros'])
            combinaison['gains_potentiels'] = bareme.get(nb_numeros, {})
            
            # Estimation probabiliste du gain moyen
            if nb_numeros in bareme:
                gain_moyen = 0
                for bons, gain in bareme[nb_numeros].items():
                    # Probabilité approximative (simplifiée)
                    if nb_numeros == 4:
                        prob = 0.1 if bons == 2 else 0.02 if bons == 3 else 0.003
                    else:  # 5 numéros
                        prob = 0.08 if bons == 3 else 0.01 if bons == 4 else 0.001
                    
                    gain_moyen += prob * gain
                
                combinaison['gain_moyen_estime'] = gain_moyen
        
        return combinaisons
    
    def sauvegarder_resultats(self, numeros_predits, combinaisons):
        """Sauvegarde les résultats dans des fichiers"""
        print("Sauvegarde des résultats...")
        
        # Rapport texte
        with open(f"{self.config['repertoire_sortie']}/rapport_keno.txt", 'w', encoding='utf-8') as f:
            f.write("=== RAPPORT D'ANALYSE KENO ===\n\n")
            f.write(f"Date d'analyse: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
            f.write(f"Nombre de tirages analysés: {len(self.df)}\n")
            f.write(f"Période: {self.df['date'].iloc[0]} à {self.df['date'].iloc[-1]}\n\n")
            
            f.write("=== TOP 20 NUMÉROS PRÉDITS ===\n")
            for i, (numero, score) in enumerate(numeros_predits[:20], 1):
                f.write(f"{i:2d}. Numéro {numero:2d} - Score: {score:.3f}\n")
            
            f.write(f"\n=== COMBINAISONS OPTIMISÉES ({self.config['nb_numeros_par_grille']} numéros) ===\n")
            for i, combo in enumerate(combinaisons, 1):
                f.write(f"\nCombinaison {i}: {combo['numeros']}\n")
                f.write(f"Stratégie: {combo['strategie']}\n")
                f.write(f"Score moyen: {combo['score_moyen']:.3f}\n")
                if 'gain_moyen_estime' in combo:
                    f.write(f"Gain moyen estimé: {combo['gain_moyen_estime']:.2f}€\n")
            
            f.write(f"\n=== STATISTIQUES ===\n")
            f.write(f"Numéros chauds (fenêtre {self.config['fenetre_analyse']}): {self.numeros_chauds[:10]}\n")
            f.write(f"Numéros froids: {self.numeros_froids[:10]}\n")
            
            # Top écarts
            top_ecarts = sorted(self.ecarts_globaux.items(), key=lambda x: x[1], reverse=True)[:10]
            f.write(f"Plus grands écarts: {[f'{n}({e})' for n, e in top_ecarts]}\n")
        
        # Données JSON pour traitement ultérieur
        resultats_json = {
            'date_analyse': datetime.now().isoformat(),
            'config': self.config,
            'numeros_predits': numeros_predits[:30],
            'combinaisons': combinaisons,
            'statistiques': {
                'numeros_chauds': self.numeros_chauds,
                'numeros_froids': self.numeros_froids,
                'ecarts_globaux': self.ecarts_globaux
            }
        }
        
        with open(f"{self.config['repertoire_sortie']}/resultats_keno.json", 'w', encoding='utf-8') as f:
            json.dump(resultats_json, f, indent=2, ensure_ascii=False)
        
        print(f"Résultats sauvegardés dans {self.config['repertoire_sortie']}/")
    
    def generer_visualisations(self, numeros_predits):
        """Génère des graphiques d'analyse"""
        print("Génération des visualisations...")
        
        plt.style.use('default')
        
        # 1. Distribution des fréquences
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # Fréquences globales
        numeros = list(range(1, 71))
        frequences = [self.stats_globales['frequences'].get(n, 0) for n in numeros]
        
        axes[0,0].bar(numeros, frequences, alpha=0.7, color='skyblue')
        axes[0,0].set_title('Fréquences globales des numéros')
        axes[0,0].set_xlabel('Numéros')
        axes[0,0].set_ylabel('Fréquence')
        
        # Fréquences récentes
        freq_recentes = [self.stats_fenetre['frequences'].get(n, 0) for n in numeros]
        axes[0,1].bar(numeros, freq_recentes, alpha=0.7, color='lightcoral')
        axes[0,1].set_title(f'Fréquences récentes ({self.config["fenetre_analyse"]} tirages)')
        axes[0,1].set_xlabel('Numéros')
        axes[0,1].set_ylabel('Fréquence')
        
        # Écarts actuels
        ecarts = [self.ecarts_globaux.get(n, 0) for n in numeros]
        axes[1,0].bar(numeros, ecarts, alpha=0.7, color='lightgreen')
        axes[1,0].set_title('Écarts actuels (tirages depuis dernière sortie)')
        axes[1,0].set_xlabel('Numéros')
        axes[1,0].set_ylabel('Écart')
        
        # Scores de prédiction
        scores = [dict(numeros_predits)[n] for n in numeros]
        axes[1,1].bar(numeros, scores, alpha=0.7, color='gold')
        axes[1,1].set_title('Scores de prédiction')
        axes[1,1].set_xlabel('Numéros')
        axes[1,1].set_ylabel('Score')
        
        plt.tight_layout()
        plt.savefig(f"{self.config['repertoire_sortie']}/analyse_keno.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. Évolution des sommes
        fig, ax = plt.subplots(figsize=(12, 6))
        sommes = self.patterns['sommes']
        ax.plot(sommes, alpha=0.7, color='blue')
        ax.axhline(y=np.mean(sommes), color='red', linestyle='--', label=f'Moyenne: {np.mean(sommes):.1f}')
        ax.set_title('Évolution des sommes des tirages')
        ax.set_xlabel('Tirage')
        ax.set_ylabel('Somme')
        ax.legend()
        plt.savefig(f"{self.config['repertoire_sortie']}/evolution_sommes.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Visualisations sauvegardées dans {self.config['repertoire_sortie']}/")
    
    def analyser_semaine_courante(self):
        """Analyse spécifique des tirages de la semaine courante"""
        print("Analyse de la semaine courante...")
        
        # Prendre les 14 derniers tirages (1 semaine = 2 tirages/jour)
        semaine_df = self.df.tail(14)
        
        # Statistiques de la semaine
        numeros_semaine = []
        for numeros in semaine_df['numeros']:
            numeros_semaine.extend(numeros)
        
        freq_semaine = Counter(numeros_semaine)
        
        print(f"Tirages de la semaine: {len(semaine_df)}")
        print(f"Numéros les plus sortis cette semaine: {freq_semaine.most_common(10)}")
        
        return freq_semaine
    
    def run_analyse_complete(self):
        """Exécute l'analyse complète"""
        print("=== DÉBUT DE L'ANALYSE KENO ===\n")
        
        # 1. Charger les données
        if not self.charger_donnees():
            return False
        
        # 2. Calculer les statistiques
        self.calculer_statistiques_globales()
        self.calculer_statistiques_fenetre()
        
        # 3. Analyser les patterns
        self.analyser_patterns()
        
        # 4. Analyse de la semaine
        freq_semaine = self.analyser_semaine_courante()
        
        # 5. Entraîner le modèle ML
        self.entrainer_modele_ml()
        
        # 6. Prédire les numéros
        numeros_predits = self.predire_prochains_numeros()
        
        # 7. Générer les combinaisons
        combinaisons = self.generer_combinaisons_optimisees(numeros_predits)
        combinaisons = self.calculer_gains_potentiels(combinaisons)
        
        # 8. Sauvegarder les résultats
        self.sauvegarder_resultats(numeros_predits, combinaisons)
        
        # 9. Générer les visualisations
        self.generer_visualisations(numeros_predits)
        
        # 10. Afficher le résumé
        print("\n=== RÉSUMÉ DES PRÉDICTIONS ===")
        print(f"Top 10 numéros prédits: {[n for n, s in numeros_predits[:10]]}")
        print(f"\nMeilleures combinaisons ({self.config['nb_numeros_par_grille']} numéros):")
        for i, combo in enumerate(combinaisons[:5], 1):
            gain_est = combo.get('gain_moyen_estime', 0)
            print(f"{i}. {combo['numeros']} - {combo['strategie']} - Gain estimé: {gain_est:.2f}€")
        
        print(f"\n=== ANALYSE TERMINÉE ===")
        print(f"Résultats disponibles dans: {self.config['repertoire_sortie']}/")
        
        return True

def main():
    """Fonction principale"""
    analyzer = KenoAnalyzer()
    
    # Configuration personnalisable
    print("Configuration actuelle:")
    for key, value in analyzer.config.items():
        print(f"  {key}: {value}")
    
    print("\n" + "="*50)
    
    # Lancer l'analyse
    success = analyzer.run_analyse_complete()
    
    if success:
        print("\nAnalyse réussie! Consultez les fichiers de résultats.")
    else:
        print("\nÉchec de l'analyse. Vérifiez les données d'entrée.")

if __name__ == "__main__":
    main()

