#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script principal pour l'analyse et la prédiction Keno
Pipeline complet: Scraping -> Analyse -> Prédiction -> Optimisation
Objectif: Générer des combinaisons de 4-5 numéros pour gains ~50€
"""

import os
import sys
import argparse
from datetime import datetime
import json

# Import des modules locaux
from keno_web_scraper import KenoWebScraper
from keno_analyzer import KenoAnalyzer

class KenoPipeline:
    def __init__(self):
        self.scraper = KenoWebScraper()
        self.analyzer = None
        self.config = {
            'forcer_scraping': False,
            'nb_numeros_par_grille': 5,  # 4 ou 5
            'nb_combinaisons': 10,
            'objectif_gain': 50,
            'mise_par_grille': 1,
            'utiliser_ml': True,
            'generer_visualisations': True,
            'fichier_csv': 'tirages_keno.csv',
            'repertoire_sortie': 'resultats_keno'
        }
    
    def verifier_donnees_existantes(self):
        """Vérifie si des données existent déjà"""
        if os.path.exists(self.config['fichier_csv']):
            try:
                import pandas as pd
                df = pd.read_csv(self.config['fichier_csv'])
                print(f"Données existantes trouvées: {len(df)} tirages")
                
                # Vérifier la fraîcheur des données
                if len(df) > 0:
                    derniere_date = df['date'].iloc[0]  # Première ligne = plus récent
                    print(f"Dernier tirage: {derniere_date}")
                    return True
            except Exception as e:
                print(f"Erreur lors de la lecture des données existantes: {e}")
        
        return False
    
    def executer_scraping(self):
        """Exécute le scraping des données"""
        print("=== PHASE 1: COLLECTE DES DONNÉES ===")
        
        # Vérifier si on doit scraper
        if not self.config['forcer_scraping'] and self.verifier_donnees_existantes():
            reponse = input("Données existantes trouvées. Scraper à nouveau? (o/N): ").lower()
            if reponse not in ['o', 'oui', 'y', 'yes']:
                print("Utilisation des données existantes.")
                return True
        
        print("Début du scraping...")
        tirages = self.scraper.scraper_tirages()
        
        if tirages:
            success = self.scraper.sauvegarder_csv(tirages, self.config['fichier_csv'])
            if success:
                print(f"✓ Scraping réussi: {len(tirages)} tirages collectés")
                return True
            else:
                print("✗ Erreur lors de la sauvegarde")
                return False
        else:
            print("✗ Aucun tirage collecté")
            return False
    
    def executer_analyse(self):
        """Exécute l'analyse et la prédiction"""
        print("\n=== PHASE 2: ANALYSE ET PRÉDICTION ===")
        
        # Initialiser l'analyseur avec la configuration
        self.analyzer = KenoAnalyzer(self.config['fichier_csv'])
        
        # Appliquer la configuration
        self.analyzer.config.update({
            'nb_numeros_par_grille': self.config['nb_numeros_par_grille'],
            'nb_combinaisons': self.config['nb_combinaisons'],
            'objectif_gain': self.config['objectif_gain'],
            'mise_par_grille': self.config['mise_par_grille'],
            'utiliser_ml': self.config['utiliser_ml'],
            'repertoire_sortie': self.config['repertoire_sortie']
        })
        
        # Lancer l'analyse complète
        success = self.analyzer.run_analyse_complete()
        
        if success:
            print("✓ Analyse terminée avec succès")
            return True
        else:
            print("✗ Erreur lors de l'analyse")
            return False
    
    def afficher_resume_resultats(self):
        """Affiche un résumé des résultats"""
        print("\n=== PHASE 3: RÉSUMÉ DES RÉSULTATS ===")
        
        try:
            # Charger les résultats JSON
            with open(f"{self.config['repertoire_sortie']}/resultats_keno.json", 'r', encoding='utf-8') as f:
                resultats = json.load(f)
            
            print(f"Date d'analyse: {resultats['date_analyse']}")
            print(f"Configuration utilisée:")
            print(f"  - Numéros par grille: {resultats['config']['nb_numeros_par_grille']}")
            print(f"  - Nombre de combinaisons: {resultats['config']['nb_combinaisons']}")
            print(f"  - Objectif de gain: {resultats['config']['objectif_gain']}€")
            
            print(f"\n🎯 TOP 10 NUMÉROS PRÉDITS:")
            for i, (numero, score) in enumerate(resultats['numeros_predits'][:10], 1):
                print(f"  {i:2d}. Numéro {numero:2d} (score: {score:.3f})")
            
            print(f"\n🎲 MEILLEURES COMBINAISONS:")
            for i, combo in enumerate(resultats['combinaisons'][:5], 1):
                numeros = combo['numeros']
                strategie = combo['strategie']
                gain_est = combo.get('gain_moyen_estime', 0)
                print(f"  {i}. {numeros} - {strategie}")
                print(f"     Gain moyen estimé: {gain_est:.2f}€")
            
            print(f"\n📊 STATISTIQUES:")
            stats = resultats['statistiques']
            print(f"  Numéros chauds: {stats['numeros_chauds'][:10]}")
            print(f"  Numéros froids: {stats['numeros_froids'][:10]}")
            
            # Calculer le coût total
            cout_total = len(resultats['combinaisons']) * resultats['config']['mise_par_grille']
            print(f"\n💰 INVESTISSEMENT:")
            print(f"  Coût total: {cout_total}€ ({len(resultats['combinaisons'])} grilles × {resultats['config']['mise_par_grille']}€)")
            print(f"  Objectif de gain: {resultats['config']['objectif_gain']}€")
            print(f"  Ratio objectif/coût: {resultats['config']['objectif_gain']/cout_total:.1f}x")
            
            print(f"\n📁 Fichiers générés:")
            print(f"  - Rapport détaillé: {self.config['repertoire_sortie']}/rapport_keno.txt")
            print(f"  - Données JSON: {self.config['repertoire_sortie']}/resultats_keno.json")
            print(f"  - Graphiques: {self.config['repertoire_sortie']}/analyse_keno.png")
            
            return True
            
        except Exception as e:
            print(f"Erreur lors de l'affichage des résultats: {e}")
            return False
    
    def generer_grilles_jeu(self):
        """Génère des grilles prêtes à jouer"""
        print("\n=== GÉNÉRATION DES GRILLES DE JEU ===")
        
        try:
            with open(f"{self.config['repertoire_sortie']}/resultats_keno.json", 'r', encoding='utf-8') as f:
                resultats = json.load(f)
            
            # Créer un fichier de grilles prêtes à jouer
            with open(f"{self.config['repertoire_sortie']}/grilles_keno.txt", 'w', encoding='utf-8') as f:
                f.write("=== GRILLES KENO OPTIMISÉES ===\n")
                f.write(f"Générées le: {datetime.now().strftime('%d/%m/%Y à %H:%M')}\n")
                f.write(f"Objectif de gain: {self.config['objectif_gain']}€\n")
                f.write(f"Mise par grille: {self.config['mise_par_grille']}€\n\n")
                
                cout_total = 0
                for i, combo in enumerate(resultats['combinaisons'], 1):
                    f.write(f"GRILLE {i} - {combo['strategie']}\n")
                    f.write(f"Numéros: {' - '.join(map(str, combo['numeros']))}\n")
                    f.write(f"Score: {combo['score_moyen']:.3f}\n")
                    if 'gain_moyen_estime' in combo:
                        f.write(f"Gain estimé: {combo['gain_moyen_estime']:.2f}€\n")
                    f.write("-" * 40 + "\n")
                    cout_total += self.config['mise_par_grille']
                
                f.write(f"\nCOÛT TOTAL: {cout_total}€\n")
                f.write(f"OBJECTIF: {self.config['objectif_gain']}€\n")
                f.write(f"RATIO: {self.config['objectif_gain']/cout_total:.1f}x\n")
            
            print(f"✓ Grilles de jeu sauvegardées: {self.config['repertoire_sortie']}/grilles_keno.txt")
            return True
            
        except Exception as e:
            print(f"✗ Erreur lors de la génération des grilles: {e}")
            return False
    
    def executer_pipeline_complet(self):
        """Exécute le pipeline complet"""
        print("🎰 PIPELINE KENO - ANALYSE PRÉDICTIVE")
        print("=" * 50)
        print(f"Objectif: {self.config['objectif_gain']}€ avec {self.config['nb_numeros_par_grille']} numéros par grille")
        print("=" * 50)
        
        # Phase 1: Scraping
        if not self.executer_scraping():
            print("❌ Échec du pipeline: erreur de scraping")
            return False
        
        # Phase 2: Analyse
        if not self.executer_analyse():
            print("❌ Échec du pipeline: erreur d'analyse")
            return False
        
        # Phase 3: Résumé
        if not self.afficher_resume_resultats():
            print("❌ Échec de l'affichage des résultats")
            return False
        
        # Phase 4: Grilles de jeu
        if not self.generer_grilles_jeu():
            print("❌ Échec de la génération des grilles")
            return False
        
        print("\n🎉 PIPELINE TERMINÉ AVEC SUCCÈS!")
        print(f"📂 Consultez le dossier '{self.config['repertoire_sortie']}' pour tous les résultats")
        
        return True

def main():
    """Fonction principale avec arguments en ligne de commande"""
    parser = argparse.ArgumentParser(description="Pipeline d'analyse prédictive Keno")
    
    parser.add_argument('--numeros', type=int, choices=[4, 5], default=5,
                       help='Nombre de numéros par grille (4 ou 5)')
    parser.add_argument('--combinaisons', type=int, default=10,
                       help='Nombre de combinaisons à générer')
    parser.add_argument('--objectif', type=int, default=50,
                       help='Objectif de gain en euros')
    parser.add_argument('--mise', type=int, default=1,
                       help='Mise par grille en euros')
    parser.add_argument('--force-scraping', action='store_true',
                       help='Forcer le scraping même si des données existent')
    parser.add_argument('--no-ml', action='store_true',
                       help='Désactiver le machine learning')
    
    args = parser.parse_args()
    
    # Créer le pipeline
    pipeline = KenoPipeline()
    
    # Appliquer la configuration
    pipeline.config.update({
        'nb_numeros_par_grille': args.numeros,
        'nb_combinaisons': args.combinaisons,
        'objectif_gain': args.objectif,
        'mise_par_grille': args.mise,
        'forcer_scraping': args.force_scraping,
        'utiliser_ml': not args.no_ml
    })
    
    # Exécuter le pipeline
    success = pipeline.executer_pipeline_complet()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()

