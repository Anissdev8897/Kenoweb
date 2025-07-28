#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Application GUI Keno - Interface graphique moderne
Intègre toutes les méthodes avancées du système Loto adaptées au Keno
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import os
import sys
import json
import webbrowser
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import numpy as np
from collections import Counter
import seaborn as sns

# Import des modules Keno
try:
    from keno_web_scraper import KenoWebScraper
    from keno_analyzer import KenoAnalyzer
    from keno_optimizer import KenoOptimizer
    from keno_frequency_analysis import KenoFrequencyAnalyzer
    from keno_cycle_analysis import KenoCycleAnalyzer
    from keno_fibonacci_weighting import KenoFibonacciWeighting
    from keno_backtesting import KenoBacktester
except ImportError as e:
    print(f"Erreur d'import des modules Keno: {e}")
    messagebox.showerror("Erreur", f"Modules manquants: {e}")

class KenoAdvancedGUI:
    """Interface graphique avancée pour l'analyse Keno"""
    
    def __init__(self, root):
        self.root = root
        self.setup_main_window()
        self.setup_variables()
        self.create_widgets()
        self.setup_styles()
        
        # Modules d'analyse
        self.scraper = KenoWebScraper()
        self.analyzer = None
        self.optimizer = KenoOptimizer()
        self.frequency_analyzer = KenoFrequencyAnalyzer()
        self.cycle_analyzer = KenoCycleAnalyzer()
        self.fibonacci_weighting = KenoFibonacciWeighting()
        self.backtester = KenoBacktester()
        
        # Données
        self.tirages_data = None
        self.analysis_results = None
        
    def setup_main_window(self):
        """Configuration de la fenêtre principale"""
        self.root.title("🎰 KENO ANALYZER PRO - Analyse Prédictive Avancée")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        
        # Configuration du style
        self.root.configure(bg='#1a1a2e')
        
        # Icône de l'application (optionnel)
        try:
            self.root.iconbitmap('keno_icon.ico')
        except:
            pass
    
    def setup_variables(self):
        """Initialisation des variables"""
        self.nb_numeros_var = tk.IntVar(value=5)
        self.nb_combinaisons_var = tk.IntVar(value=10)
        self.objectif_gain_var = tk.IntVar(value=50)
        self.mise_var = tk.IntVar(value=1)
        self.fenetre_analyse_var = tk.IntVar(value=50)
        self.utiliser_ml_var = tk.BooleanVar(value=True)
        self.auto_update_var = tk.BooleanVar(value=True)
        
        # Variables d'état
        self.analysis_running = tk.BooleanVar(value=False)
        self.progress_var = tk.DoubleVar(value=0)
        self.status_var = tk.StringVar(value="Prêt")
        
    def setup_styles(self):
        """Configuration des styles ttk"""
        style = ttk.Style()
        
        # Thème sombre
        style.theme_use('clam')
        
        # Couleurs personnalisées
        style.configure('Dark.TFrame', background='#16213e')
        style.configure('Dark.TLabel', background='#16213e', foreground='white')
        style.configure('Dark.TButton', background='#ffd700', foreground='black')
        style.configure('Gold.TButton', background='#ffd700', foreground='black')
        style.configure('Blue.TButton', background='#4a90e2', foreground='white')
        
    def create_widgets(self):
        """Création de tous les widgets"""
        self.create_menu_bar()
        self.create_main_layout()
        self.create_toolbar()
        self.create_keno_grid()
        self.create_analysis_panel()
        self.create_statistics_panel()
        self.create_results_panel()
        self.create_status_bar()
        
    def create_menu_bar(self):
        """Création de la barre de menu"""
        menubar = tk.Menu(self.root, bg='#1a1a2e', fg='white')
        self.root.config(menu=menubar)
        
        # Menu Fichier
        file_menu = tk.Menu(menubar, tearoff=0, bg='#16213e', fg='white')
        menubar.add_cascade(label="Fichier", menu=file_menu)
        file_menu.add_command(label="Nouveau", command=self.nouveau_projet)
        file_menu.add_command(label="Ouvrir", command=self.ouvrir_projet)
        file_menu.add_command(label="Sauvegarder", command=self.sauvegarder_projet)
        file_menu.add_separator()
        file_menu.add_command(label="Exporter CSV", command=self.exporter_csv)
        file_menu.add_command(label="Exporter PDF", command=self.exporter_pdf)
        file_menu.add_separator()
        file_menu.add_command(label="Quitter", command=self.root.quit)
        
        # Menu Analyse
        analyse_menu = tk.Menu(menubar, tearoff=0, bg='#16213e', fg='white')
        menubar.add_cascade(label="Analyse", menu=analyse_menu)
        analyse_menu.add_command(label="Lancer Analyse Complète", command=self.lancer_analyse_complete)
        analyse_menu.add_command(label="Analyse Rapide", command=self.lancer_analyse_rapide)
        analyse_menu.add_separator()
        analyse_menu.add_command(label="Analyse de Fréquence", command=self.lancer_analyse_frequence)
        analyse_menu.add_command(label="Analyse de Cycles", command=self.lancer_analyse_cycles)
        analyse_menu.add_command(label="Pondération Fibonacci", command=self.lancer_fibonacci)
        analyse_menu.add_separator()
        analyse_menu.add_command(label="Mettre à jour Données", command=self.mettre_a_jour_donnees)
        analyse_menu.add_command(label="Backtesting", command=self.lancer_backtesting)
        
        # Menu Outils
        outils_menu = tk.Menu(menubar, tearoff=0, bg='#16213e', fg='white')
        menubar.add_cascade(label="Outils", menu=outils_menu)
        outils_menu.add_command(label="Générateur de Grilles", command=self.ouvrir_generateur)
        outils_menu.add_command(label="Calculateur de Gains", command=self.ouvrir_calculateur)
        outils_menu.add_command(label="Statistiques Avancées", command=self.ouvrir_stats_avancees)
        
        # Menu Aide
        aide_menu = tk.Menu(menubar, tearoff=0, bg='#16213e', fg='white')
        menubar.add_cascade(label="Aide", menu=aide_menu)
        aide_menu.add_command(label="Guide d'utilisation", command=self.ouvrir_guide)
        aide_menu.add_command(label="À propos", command=self.afficher_apropos)
        
    def create_main_layout(self):
        """Création de la disposition principale"""
        # Frame principal
        self.main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Notebook pour les onglets
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Onglets
        self.tab_analyse = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.tab_predictions = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.tab_statistiques = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.tab_graphiques = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.tab_historique = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.tab_parametres = ttk.Frame(self.notebook, style='Dark.TFrame')
        
        self.notebook.add(self.tab_analyse, text="🔍 ANALYSE")
        self.notebook.add(self.tab_predictions, text="🎯 PRÉDICTIONS")
        self.notebook.add(self.tab_statistiques, text="📊 STATISTIQUES")
        self.notebook.add(self.tab_graphiques, text="📈 GRAPHIQUES")
        self.notebook.add(self.tab_historique, text="📋 HISTORIQUE")
        self.notebook.add(self.tab_parametres, text="⚙️ PARAMÈTRES")
        
    def create_toolbar(self):
        """Création de la barre d'outils"""
        toolbar = ttk.Frame(self.tab_analyse, style='Dark.TFrame')
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        # Boutons principaux
        ttk.Button(toolbar, text="🚀 LANCER ANALYSE", 
                  command=self.lancer_analyse_complete,
                  style='Gold.TButton').pack(side=tk.LEFT, padx=5)
        
        ttk.Button(toolbar, text="🎲 GÉNÉRER GRILLES", 
                  command=self.generer_grilles,
                  style='Blue.TButton').pack(side=tk.LEFT, padx=5)
        
        ttk.Button(toolbar, text="📊 STATISTIQUES", 
                  command=self.afficher_statistiques,
                  style='Blue.TButton').pack(side=tk.LEFT, padx=5)
        
        ttk.Button(toolbar, text="💾 EXPORTER", 
                  command=self.exporter_resultats,
                  style='Blue.TButton').pack(side=tk.LEFT, padx=5)
        
        # Barre de progression
        self.progress_bar = ttk.Progressbar(toolbar, variable=self.progress_var, 
                                          maximum=100, length=200)
        self.progress_bar.pack(side=tk.RIGHT, padx=5)
        
        # Label de statut
        self.status_label = ttk.Label(toolbar, textvariable=self.status_var, 
                                     style='Dark.TLabel')
        self.status_label.pack(side=tk.RIGHT, padx=5)
        
    def create_keno_grid(self):
        """Création de la grille Keno (70 numéros)"""
        grid_frame = ttk.LabelFrame(self.tab_analyse, text="🎰 GRILLE KENO", 
                                   style='Dark.TFrame')
        grid_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)
        
        # Frame pour la grille
        self.grid_container = ttk.Frame(grid_frame, style='Dark.TFrame')
        self.grid_container.pack(padx=10, pady=10)
        
        # Création des boutons numéros
        self.numero_buttons = {}
        self.selected_numbers = set()
        
        for i in range(1, 71):
            row = (i - 1) // 10
            col = (i - 1) % 10
            
            btn = tk.Button(self.grid_container, text=str(i), 
                           width=4, height=2,
                           bg='#16213e', fg='white',
                           font=('Arial', 10, 'bold'),
                           command=lambda num=i: self.toggle_number(num))
            btn.grid(row=row, column=col, padx=1, pady=1)
            self.numero_buttons[i] = btn
        
        # Boutons de contrôle
        control_frame = ttk.Frame(grid_frame, style='Dark.TFrame')
        control_frame.pack(pady=5)
        
        ttk.Button(control_frame, text="Tout sélectionner", 
                  command=self.select_all_numbers).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Tout désélectionner", 
                  command=self.clear_selection).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Sélection aléatoire", 
                  command=self.random_selection).pack(side=tk.LEFT, padx=5)
        
    def create_analysis_panel(self):
        """Création du panneau d'analyse"""
        analysis_frame = ttk.LabelFrame(self.tab_analyse, text="📊 ANALYSE", 
                                       style='Dark.TFrame')
        analysis_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configuration de l'analyse
        config_frame = ttk.Frame(analysis_frame, style='Dark.TFrame')
        config_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Nombre de numéros par grille
        ttk.Label(config_frame, text="Numéros par grille:", 
                 style='Dark.TLabel').grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Spinbox(config_frame, from_=4, to=10, textvariable=self.nb_numeros_var,
                   width=10).grid(row=0, column=1, padx=5)
        
        # Nombre de combinaisons
        ttk.Label(config_frame, text="Combinaisons:", 
                 style='Dark.TLabel').grid(row=1, column=0, sticky=tk.W, padx=5)
        ttk.Spinbox(config_frame, from_=1, to=50, textvariable=self.nb_combinaisons_var,
                   width=10).grid(row=1, column=1, padx=5)
        
        # Objectif de gain
        ttk.Label(config_frame, text="Objectif gain (€):", 
                 style='Dark.TLabel').grid(row=2, column=0, sticky=tk.W, padx=5)
        ttk.Spinbox(config_frame, from_=10, to=1000, textvariable=self.objectif_gain_var,
                   width=10).grid(row=2, column=1, padx=5)
        
        # Options avancées
        options_frame = ttk.LabelFrame(analysis_frame, text="Options Avancées", 
                                      style='Dark.TFrame')
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Checkbutton(options_frame, text="Utiliser Machine Learning", 
                       variable=self.utiliser_ml_var,
                       style='Dark.TLabel').pack(anchor=tk.W, padx=5)
        
        ttk.Checkbutton(options_frame, text="Mise à jour automatique", 
                       variable=self.auto_update_var,
                       style='Dark.TLabel').pack(anchor=tk.W, padx=5)
        
        # Zone de résultats
        self.results_text = scrolledtext.ScrolledText(analysis_frame, 
                                                     height=15, width=50,
                                                     bg='#0f0f23', fg='white',
                                                     font=('Consolas', 10))
        self.results_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def create_statistics_panel(self):
        """Création du panneau de statistiques"""
        # Frame principal pour les statistiques
        stats_main = ttk.Frame(self.tab_statistiques, style='Dark.TFrame')
        stats_main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Statistiques générales
        general_frame = ttk.LabelFrame(stats_main, text="📈 Statistiques Générales", 
                                      style='Dark.TFrame')
        general_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.stats_labels = {}
        stats_info = [
            ("Tirages analysés:", "total_tirages"),
            ("Période couverte:", "periode"),
            ("Numéros chauds:", "numeros_chauds"),
            ("Numéros froids:", "numeros_froids"),
            ("Dernière mise à jour:", "derniere_maj")
        ]
        
        for i, (label, key) in enumerate(stats_info):
            ttk.Label(general_frame, text=label, style='Dark.TLabel').grid(
                row=i, column=0, sticky=tk.W, padx=5, pady=2)
            self.stats_labels[key] = ttk.Label(general_frame, text="N/A", 
                                              style='Dark.TLabel')
            self.stats_labels[key].grid(row=i, column=1, sticky=tk.W, padx=20, pady=2)
        
        # Graphiques intégrés
        self.create_embedded_charts()
        
    def create_embedded_charts(self):
        """Création des graphiques intégrés"""
        charts_frame = ttk.LabelFrame(self.tab_graphiques, text="📊 Visualisations", 
                                     style='Dark.TFrame')
        charts_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configuration matplotlib pour le thème sombre
        plt.style.use('dark_background')
        
        # Figure pour les graphiques
        self.fig, ((self.ax1, self.ax2), (self.ax3, self.ax4)) = plt.subplots(2, 2, 
                                                                              figsize=(12, 8),
                                                                              facecolor='#1a1a2e')
        
        # Canvas pour intégrer matplotlib dans tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, charts_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Initialisation des graphiques vides
        self.init_empty_charts()
        
    def init_empty_charts(self):
        """Initialisation des graphiques vides"""
        titles = ["Fréquences des Numéros", "Écarts Actuels", 
                 "Évolution des Sommes", "Répartition Pair/Impair"]
        axes = [self.ax1, self.ax2, self.ax3, self.ax4]
        
        for ax, title in zip(axes, titles):
            ax.set_title(title, color='white', fontsize=12)
            ax.set_facecolor('#16213e')
            ax.tick_params(colors='white')
            
        self.canvas.draw()
        
    def create_results_panel(self):
        """Création du panneau de résultats"""
        results_frame = ttk.LabelFrame(self.tab_predictions, text="🎯 Combinaisons Prédites", 
                                      style='Dark.TFrame')
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Treeview pour afficher les combinaisons
        columns = ("Rang", "Combinaison", "Stratégie", "Score", "Gain Estimé")
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show='headings',
                                        height=15)
        
        # Configuration des colonnes
        for col in columns:
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=120, anchor=tk.CENTER)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, 
                                   command=self.results_tree.yview)
        h_scrollbar = ttk.Scrollbar(results_frame, orient=tk.HORIZONTAL, 
                                   command=self.results_tree.xview)
        
        self.results_tree.configure(yscrollcommand=v_scrollbar.set,
                                   xscrollcommand=h_scrollbar.set)
        
        # Placement
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def create_status_bar(self):
        """Création de la barre de statut"""
        status_frame = ttk.Frame(self.root, style='Dark.TFrame')
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Informations de statut
        self.status_info = ttk.Label(status_frame, text="Prêt", style='Dark.TLabel')
        self.status_info.pack(side=tk.LEFT, padx=5)
        
        # Horloge
        self.clock_label = ttk.Label(status_frame, text="", style='Dark.TLabel')
        self.clock_label.pack(side=tk.RIGHT, padx=5)
        self.update_clock()
        
    def update_clock(self):
        """Mise à jour de l'horloge"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.clock_label.config(text=current_time)
        self.root.after(1000, self.update_clock)
        
    def toggle_number(self, numero):
        """Basculer la sélection d'un numéro"""
        if numero in self.selected_numbers:
            self.selected_numbers.remove(numero)
            self.numero_buttons[numero].config(bg='#16213e', fg='white')
        else:
            self.selected_numbers.add(numero)
            self.numero_buttons[numero].config(bg='#ffd700', fg='black')
            
    def select_all_numbers(self):
        """Sélectionner tous les numéros"""
        for i in range(1, 71):
            if i not in self.selected_numbers:
                self.toggle_number(i)
                
    def clear_selection(self):
        """Désélectionner tous les numéros"""
        for numero in list(self.selected_numbers):
            self.toggle_number(numero)
            
    def random_selection(self):
        """Sélection aléatoire de numéros"""
        self.clear_selection()
        import random
        numbers = random.sample(range(1, 71), self.nb_numeros_var.get())
        for num in numbers:
            self.toggle_number(num)
            
    def lancer_analyse_complete(self):
        """Lancer l'analyse complète"""
        if self.analysis_running.get():
            messagebox.showwarning("Analyse en cours", 
                                 "Une analyse est déjà en cours d'exécution.")
            return
            
        # Lancer l'analyse dans un thread séparé
        thread = threading.Thread(target=self._run_analysis_thread)
        thread.daemon = True
        thread.start()
        
    def _run_analysis_thread(self):
        """Thread d'exécution de l'analyse"""
        try:
            self.analysis_running.set(True)
            self.status_var.set("Analyse en cours...")
            self.progress_var.set(0)
            
            # Étape 1: Scraping des données
            self.update_status("Collecte des données...", 10)
            tirages = self.scraper.scraper_tirages()
            
            if not tirages:
                raise Exception("Aucune donnée collectée")
                
            # Étape 2: Sauvegarde CSV
            self.update_status("Sauvegarde des données...", 20)
            self.scraper.sauvegarder_csv(tirages)
            
            # Étape 3: Initialisation de l'analyseur
            self.update_status("Initialisation de l'analyseur...", 30)
            self.analyzer = KenoAnalyzer()
            self.analyzer.config.update({
                'nb_numeros_par_grille': self.nb_numeros_var.get(),
                'nb_combinaisons': self.nb_combinaisons_var.get(),
                'objectif_gain': self.objectif_gain_var.get(),
                'utiliser_ml': self.utiliser_ml_var.get()
            })
            
            # Étape 4: Analyse complète
            self.update_status("Analyse statistique...", 50)
            success = self.analyzer.run_analyse_complete()
            
            if success:
                self.update_status("Génération des visualisations...", 80)
                self.update_gui_with_results()
                self.update_status("Analyse terminée", 100)
                
                # Afficher les résultats
                self.root.after(0, self.show_analysis_results)
            else:
                raise Exception("Échec de l'analyse")
                
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Erreur", str(e)))
            self.update_status("Erreur d'analyse", 0)
        finally:
            self.analysis_running.set(False)
            
    def update_status(self, message, progress):
        """Mise à jour du statut et de la progression"""
        self.status_var.set(message)
        self.progress_var.set(progress)
        
    def update_gui_with_results(self):
        """Mise à jour de l'interface avec les résultats"""
        if not self.analyzer:
            return
            
        try:
            # Charger les résultats JSON
            with open('resultats_keno/resultats_keno.json', 'r', encoding='utf-8') as f:
                self.analysis_results = json.load(f)
                
            # Mettre à jour les statistiques
            self.root.after(0, self.update_statistics_display)
            
            # Mettre à jour les graphiques
            self.root.after(0, self.update_charts)
            
            # Mettre à jour les résultats
            self.root.after(0, self.update_results_display)
            
        except Exception as e:
            print(f"Erreur lors de la mise à jour GUI: {e}")
            
    def update_statistics_display(self):
        """Mise à jour de l'affichage des statistiques"""
        if not self.analysis_results:
            return
            
        config = self.analysis_results.get('config', {})
        stats = self.analysis_results.get('statistiques', {})
        
        # Mise à jour des labels
        self.stats_labels['total_tirages'].config(text=str(len(self.tirages_data) if self.tirages_data else "N/A"))
        self.stats_labels['periode'].config(text="Nov 2018 - Juin 2025")
        self.stats_labels['numeros_chauds'].config(text=str(stats.get('numeros_chauds', [])[:5]))
        self.stats_labels['numeros_froids'].config(text=str(stats.get('numeros_froids', [])[:5]))
        self.stats_labels['derniere_maj'].config(text=datetime.now().strftime("%d/%m/%Y %H:%M"))
        
    def update_charts(self):
        """Mise à jour des graphiques"""
        if not self.analysis_results:
            return
            
        try:
            # Nettoyer les axes
            for ax in [self.ax1, self.ax2, self.ax3, self.ax4]:
                ax.clear()
                ax.set_facecolor('#16213e')
                
            # Graphique 1: Fréquences des numéros prédits
            numeros_predits = self.analysis_results.get('numeros_predits', [])[:20]
            if numeros_predits:
                nums = [item[0] for item in numeros_predits]
                scores = [item[1] for item in numeros_predits]
                
                bars = self.ax1.bar(nums, scores, color='#ffd700', alpha=0.8)
                self.ax1.set_title('Top 20 Numéros Prédits', color='white')
                self.ax1.set_xlabel('Numéros', color='white')
                self.ax1.set_ylabel('Score', color='white')
                self.ax1.tick_params(colors='white')
                
            # Graphique 2: Écarts actuels
            ecarts = self.analysis_results.get('statistiques', {}).get('ecarts_globaux', {})
            if ecarts:
                # Prendre les 20 plus grands écarts
                sorted_ecarts = sorted(ecarts.items(), key=lambda x: x[1], reverse=True)[:20]
                nums = [item[0] for item in sorted_ecarts]
                gaps = [item[1] for item in sorted_ecarts]
                
                bars = self.ax2.bar(nums, gaps, color='#ff6b6b', alpha=0.8)
                self.ax2.set_title('Écarts Actuels (Top 20)', color='white')
                self.ax2.set_xlabel('Numéros', color='white')
                self.ax2.set_ylabel('Écart', color='white')
                self.ax2.tick_params(colors='white')
                
            # Graphique 3: Simulation d'évolution
            x = np.arange(1, 21)
            y = np.random.normal(700, 50, 20)  # Simulation des sommes
            self.ax3.plot(x, y, color='#4ecdc4', linewidth=2)
            self.ax3.set_title('Évolution des Sommes (Simulation)', color='white')
            self.ax3.set_xlabel('Tirages', color='white')
            self.ax3.set_ylabel('Somme', color='white')
            self.ax3.tick_params(colors='white')
            
            # Graphique 4: Répartition des stratégies
            combinaisons = self.analysis_results.get('combinaisons', [])
            if combinaisons:
                strategies = [combo.get('strategie', 'Inconnue') for combo in combinaisons]
                strategy_counts = Counter(strategies)
                
                labels = list(strategy_counts.keys())
                sizes = list(strategy_counts.values())
                colors = ['#ffd700', '#ff6b6b', '#4ecdc4', '#45b7d1']
                
                self.ax4.pie(sizes, labels=labels, colors=colors[:len(labels)], 
                           autopct='%1.1f%%', textprops={'color': 'white'})
                self.ax4.set_title('Répartition des Stratégies', color='white')
                
            # Mise à jour du canvas
            self.fig.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            print(f"Erreur lors de la mise à jour des graphiques: {e}")
            
    def update_results_display(self):
        """Mise à jour de l'affichage des résultats"""
        # Nettoyer le treeview
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
            
        if not self.analysis_results:
            return
            
        # Ajouter les combinaisons
        combinaisons = self.analysis_results.get('combinaisons', [])
        for i, combo in enumerate(combinaisons, 1):
            numeros = combo.get('numeros', [])
            strategie = combo.get('strategie', 'Inconnue')
            score = combo.get('score_moyen', 0)
            gain = combo.get('gain_moyen_estime', 0)
            
            self.results_tree.insert('', 'end', values=(
                i, 
                ' - '.join(map(str, numeros)),
                strategie,
                f"{score:.3f}",
                f"{gain:.2f}€"
            ))
            
    def show_analysis_results(self):
        """Afficher les résultats dans la zone de texte"""
        if not self.analysis_results:
            return
            
        self.results_text.delete(1.0, tk.END)
        
        # Formatage des résultats
        text = "🎯 RÉSULTATS DE L'ANALYSE KENO\n"
        text += "=" * 50 + "\n\n"
        
        # Configuration
        config = self.analysis_results.get('config', {})
        text += f"📊 Configuration:\n"
        text += f"   • Numéros par grille: {config.get('nb_numeros_par_grille', 'N/A')}\n"
        text += f"   • Combinaisons générées: {config.get('nb_combinaisons', 'N/A')}\n"
        text += f"   • Objectif de gain: {config.get('objectif_gain', 'N/A')}€\n\n"
        
        # Top numéros
        numeros_predits = self.analysis_results.get('numeros_predits', [])[:10]
        text += f"🎲 Top 10 Numéros Prédits:\n"
        for i, (numero, score) in enumerate(numeros_predits, 1):
            text += f"   {i:2d}. Numéro {numero:2d} (score: {score:.3f})\n"
        text += "\n"
        
        # Meilleures combinaisons
        combinaisons = self.analysis_results.get('combinaisons', [])[:5]
        text += f"🏆 Top 5 Combinaisons:\n"
        for i, combo in enumerate(combinaisons, 1):
            numeros = combo.get('numeros', [])
            strategie = combo.get('strategie', 'Inconnue')
            gain = combo.get('gain_moyen_estime', 0)
            text += f"   {i}. {numeros} - {strategie}\n"
            text += f"      Gain estimé: {gain:.2f}€\n"
        
        # Statistiques
        stats = self.analysis_results.get('statistiques', {})
        text += f"\n📈 Statistiques:\n"
        text += f"   • Numéros chauds: {stats.get('numeros_chauds', [])[:10]}\n"
        text += f"   • Numéros froids: {stats.get('numeros_froids', [])[:10]}\n"
        
        self.results_text.insert(1.0, text)
        
    # Méthodes pour les autres fonctionnalités
    def lancer_analyse_rapide(self):
        """Analyse rapide sans ML"""
        messagebox.showinfo("Analyse Rapide", "Fonctionnalité en développement")
        
    def generer_grilles(self):
        """Générer des grilles de jeu"""
        if not self.analysis_results:
            messagebox.showwarning("Pas de données", "Veuillez d'abord lancer une analyse")
            return
            
        # Ouvrir une fenêtre de génération de grilles
        self.open_grille_generator()
        
    def open_grille_generator(self):
        """Ouvrir le générateur de grilles"""
        grille_window = tk.Toplevel(self.root)
        grille_window.title("🎲 Générateur de Grilles")
        grille_window.geometry("600x400")
        grille_window.configure(bg='#1a1a2e')
        
        # Contenu du générateur
        ttk.Label(grille_window, text="Générateur de Grilles Keno", 
                 style='Dark.TLabel', font=('Arial', 16, 'bold')).pack(pady=20)
        
        # Options de génération
        options_frame = ttk.Frame(grille_window, style='Dark.TFrame')
        options_frame.pack(pady=20)
        
        ttk.Label(options_frame, text="Nombre de grilles:", 
                 style='Dark.TLabel').grid(row=0, column=0, padx=10)
        nb_grilles_var = tk.IntVar(value=5)
        ttk.Spinbox(options_frame, from_=1, to=20, textvariable=nb_grilles_var,
                   width=10).grid(row=0, column=1, padx=10)
        
        # Bouton de génération
        ttk.Button(grille_window, text="Générer Grilles", 
                  command=lambda: self.generate_grilles_display(grille_window, nb_grilles_var.get()),
                  style='Gold.TButton').pack(pady=20)
        
    def generate_grilles_display(self, window, nb_grilles):
        """Afficher les grilles générées"""
        if not self.analysis_results:
            return
            
        # Zone d'affichage des grilles
        grilles_text = scrolledtext.ScrolledText(window, height=15, width=70,
                                               bg='#0f0f23', fg='white',
                                               font=('Consolas', 10))
        grilles_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Générer les grilles
        combinaisons = self.analysis_results.get('combinaisons', [])[:nb_grilles]
        
        text = "🎲 GRILLES KENO GÉNÉRÉES\n"
        text += "=" * 50 + "\n\n"
        
        for i, combo in enumerate(combinaisons, 1):
            numeros = combo.get('numeros', [])
            strategie = combo.get('strategie', 'Inconnue')
            score = combo.get('score_moyen', 0)
            gain = combo.get('gain_moyen_estime', 0)
            
            text += f"GRILLE {i} - {strategie}\n"
            text += f"Numéros: {' - '.join(map(str, numeros))}\n"
            text += f"Score: {score:.3f} | Gain estimé: {gain:.2f}€\n"
            text += "-" * 40 + "\n"
            
        grilles_text.insert(1.0, text)
        
    def afficher_statistiques(self):
        """Afficher les statistiques détaillées"""
        self.notebook.select(self.tab_statistiques)
        
    def exporter_resultats(self):
        """Exporter les résultats"""
        if not self.analysis_results:
            messagebox.showwarning("Pas de données", "Aucun résultat à exporter")
            return
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.analysis_results, f, indent=2, ensure_ascii=False)
                messagebox.showinfo("Export réussi", f"Résultats exportés vers {filename}")
            except Exception as e:
                messagebox.showerror("Erreur d'export", str(e))
                
    def mettre_a_jour_donnees(self):
        """Mettre à jour les données"""
        thread = threading.Thread(target=self._update_data_thread)
        thread.daemon = True
        thread.start()
        
    def _update_data_thread(self):
        """Thread de mise à jour des données"""
        try:
            self.update_status("Mise à jour des données...", 0)
            tirages = self.scraper.scraper_tirages()
            if tirages:
                self.scraper.sauvegarder_csv(tirages)
                self.update_status("Données mises à jour", 100)
                self.root.after(0, lambda: messagebox.showinfo("Succès", "Données mises à jour"))
            else:
                raise Exception("Échec de la mise à jour")
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Erreur", str(e)))
            
    # Méthodes pour les menus
    def nouveau_projet(self):
        """Nouveau projet"""
        self.clear_all_data()
        messagebox.showinfo("Nouveau projet", "Nouveau projet créé")
        
    def ouvrir_projet(self):
        """Ouvrir un projet"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    self.analysis_results = json.load(f)
                self.update_gui_with_results()
                messagebox.showinfo("Succès", "Projet ouvert avec succès")
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible d'ouvrir le projet: {e}")
                
    def sauvegarder_projet(self):
        """Sauvegarder le projet"""
        if not self.analysis_results:
            messagebox.showwarning("Pas de données", "Aucun projet à sauvegarder")
            return
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.analysis_results, f, indent=2, ensure_ascii=False)
                messagebox.showinfo("Succès", "Projet sauvegardé")
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible de sauvegarder: {e}")
                
    def exporter_csv(self):
        """Exporter en CSV"""
        messagebox.showinfo("Export CSV", "Fonctionnalité en développement")
        
    def exporter_pdf(self):
        """Exporter en PDF"""
        messagebox.showinfo("Export PDF", "Fonctionnalité en développement")
        
    def lancer_backtesting(self):
        """Lancer le backtesting"""
        messagebox.showinfo("Backtesting", "Fonctionnalité en développement")
        
    def ouvrir_generateur(self):
        """Ouvrir le générateur de grilles"""
        self.open_grille_generator()
        
    def ouvrir_calculateur(self):
        """Ouvrir le calculateur de gains"""
        messagebox.showinfo("Calculateur", "Fonctionnalité en développement")
        
    def ouvrir_stats_avancees(self):
        """Ouvrir les statistiques avancées"""
        self.notebook.select(self.tab_statistiques)
        
    def ouvrir_guide(self):
        """Ouvrir le guide d'utilisation"""
        try:
            webbrowser.open("README_KENO.md")
        except:
            messagebox.showinfo("Guide", "Consultez le fichier README_KENO.md")
            
    def afficher_apropos(self):
        """Afficher les informations à propos"""
        about_text = """
🎰 KENO ANALYZER PRO
Version 1.0

Application d'analyse prédictive avancée pour le Keno
Intègre toutes les méthodes sophistiquées du système Loto

Fonctionnalités:
• Scraping automatique des données
• Analyse statistique avancée
• Machine Learning intégré
• Visualisations interactives
• Génération de grilles optimisées
• Backtesting et validation

Développé avec Python, Tkinter, Matplotlib
© 2025 - Keno Analyzer Pro
        """
        messagebox.showinfo("À propos", about_text)
        
    def clear_all_data(self):
        """Nettoyer toutes les données"""
        self.analysis_results = None
        self.tirages_data = None
        self.clear_selection()
        self.results_text.delete(1.0, tk.END)
        
        # Nettoyer les graphiques
        for ax in [self.ax1, self.ax2, self.ax3, self.ax4]:
            ax.clear()
        self.init_empty_charts()
        
        # Nettoyer le treeview
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

def main():
    """Fonction principale"""
    root = tk.Tk()
    app = KenoAdvancedGUI(root)
    
    # Gestionnaire de fermeture
    def on_closing():
        if messagebox.askokcancel("Quitter", "Voulez-vous vraiment quitter l'application?"):
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Lancement de l'application
    root.mainloop()

if __name__ == "__main__":
    main()


    
    # Nouvelles méthodes d'analyse avancées
    def lancer_analyse_frequence(self):
        """Lancer l'analyse de fréquence avancée"""
        if not self.tirages_data:
            messagebox.showwarning("Pas de données", "Veuillez d'abord charger les données")
            return
        
        def run_frequency_analysis():
            try:
                self.update_status("Analyse de fréquence en cours...", 20)
                
                # Analyse de fréquence
                freq_results = self.frequency_analyzer.calculate_number_frequencies(self.tirages_data)
                
                # Analyse des écarts
                self.update_status("Calcul des écarts...", 40)
                gaps = self.frequency_analyzer.calculate_gaps(self.tirages_data)
                
                # Analyse des patterns
                self.update_status("Analyse des patterns...", 60)
                patterns = self.frequency_analyzer.analyze_patterns(self.tirages_data)
                
                # Analyse par fenêtres
                self.update_status("Analyse par fenêtres...", 80)
                window_analysis = self.frequency_analyzer.analyze_frequency_windows(self.tirages_data)
                
                # Génération du rapport
                report = self.frequency_analyzer.generate_frequency_report(freq_results, gaps, patterns)
                
                self.update_status("Analyse de fréquence terminée", 100)
                
                # Afficher les résultats
                self.root.after(0, lambda: self.show_frequency_results(report, freq_results))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Erreur", f"Erreur d'analyse: {e}"))
                self.update_status("Erreur d'analyse", 0)
        
        thread = threading.Thread(target=run_frequency_analysis)
        thread.daemon = True
        thread.start()
    
    def show_frequency_results(self, report: str, freq_results: dict):
        """Afficher les résultats d'analyse de fréquence"""
        # Créer une nouvelle fenêtre
        freq_window = tk.Toplevel(self.root)
        freq_window.title("📊 Analyse de Fréquence")
        freq_window.geometry("800x600")
        freq_window.configure(bg='#1a1a2e')
        
        # Zone de texte pour le rapport
        text_frame = ttk.Frame(freq_window, style='Dark.TFrame')
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = scrolledtext.ScrolledText(text_frame, 
                                              bg='#0f0f23', fg='white',
                                              font=('Consolas', 10))
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(1.0, report)
        
        # Boutons d'action
        button_frame = ttk.Frame(freq_window, style='Dark.TFrame')
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(button_frame, text="Exporter Rapport", 
                  command=lambda: self.export_text_report(report, "rapport_frequence.txt"),
                  style='Blue.TButton').pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Fermer", 
                  command=freq_window.destroy,
                  style='Blue.TButton').pack(side=tk.RIGHT, padx=5)
    
    def lancer_analyse_cycles(self):
        """Lancer l'analyse de cycles avancée"""
        if not self.tirages_data:
            messagebox.showwarning("Pas de données", "Veuillez d'abord charger les données")
            return
        
        def run_cycle_analysis():
            try:
                self.update_status("Analyse de cycles en cours...", 20)
                
                # Analyse des cycles sur plusieurs fenêtres
                cycle_results = self.cycle_analyzer.analyze_multiple_windows(
                    self.tirages_data, [20, 50, 100, 200]
                )
                
                self.update_status("Génération du rapport de cycles...", 80)
                
                # Génération du rapport
                report = self.cycle_analyzer.generate_cycle_report(cycle_results)
                
                self.update_status("Analyse de cycles terminée", 100)
                
                # Afficher les résultats
                self.root.after(0, lambda: self.show_cycle_results(report, cycle_results))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Erreur", f"Erreur d'analyse: {e}"))
                self.update_status("Erreur d'analyse", 0)
        
        thread = threading.Thread(target=run_cycle_analysis)
        thread.daemon = True
        thread.start()
    
    def show_cycle_results(self, report: str, cycle_results: dict):
        """Afficher les résultats d'analyse de cycles"""
        cycle_window = tk.Toplevel(self.root)
        cycle_window.title("🔄 Analyse de Cycles")
        cycle_window.geometry("900x700")
        cycle_window.configure(bg='#1a1a2e')
        
        # Notebook pour organiser les résultats
        notebook = ttk.Notebook(cycle_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Onglet rapport
        report_frame = ttk.Frame(notebook, style='Dark.TFrame')
        notebook.add(report_frame, text="Rapport")
        
        report_text = scrolledtext.ScrolledText(report_frame, 
                                              bg='#0f0f23', fg='white',
                                              font=('Consolas', 10))
        report_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        report_text.insert(1.0, report)
        
        # Onglet détails par fenêtre
        for window_key, analysis in cycle_results.items():
            if window_key.startswith('window_') and isinstance(analysis, dict):
                window_size = analysis.get('window_size', 0)
                detail_frame = ttk.Frame(notebook, style='Dark.TFrame')
                notebook.add(detail_frame, text=f"Fenêtre {window_size}")
                
                detail_text = scrolledtext.ScrolledText(detail_frame, 
                                                      bg='#0f0f23', fg='white',
                                                      font=('Consolas', 9))
                detail_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
                
                # Formater les détails
                detail_content = f"ANALYSE FENÊTRE {window_size} TIRAGES\n"
                detail_content += "=" * 40 + "\n\n"
                
                over_rep = analysis.get('over_represented', {})
                if over_rep:
                    detail_content += "Numéros sur-représentés:\n"
                    for num, data in sorted(over_rep.items(), 
                                          key=lambda x: x[1]['deviation'], reverse=True)[:15]:
                        detail_content += f"  {num:2d}: {data['deviation_percentage']:+.1f}%\n"
                    detail_content += "\n"
                
                under_rep = analysis.get('under_represented', {})
                if under_rep:
                    detail_content += "Numéros sous-représentés:\n"
                    for num, data in sorted(under_rep.items(), 
                                          key=lambda x: x[1]['deviation'])[:15]:
                        detail_content += f"  {num:2d}: {data['deviation_percentage']:+.1f}%\n"
                
                detail_text.insert(1.0, detail_content)
        
        # Boutons d'action
        button_frame = ttk.Frame(cycle_window, style='Dark.TFrame')
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(button_frame, text="Exporter Rapport", 
                  command=lambda: self.export_text_report(report, "rapport_cycles.txt"),
                  style='Blue.TButton').pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Fermer", 
                  command=cycle_window.destroy,
                  style='Blue.TButton').pack(side=tk.RIGHT, padx=5)
    
    def lancer_fibonacci(self):
        """Lancer l'analyse de pondération Fibonacci"""
        if not self.tirages_data:
            messagebox.showwarning("Pas de données", "Veuillez d'abord charger les données")
            return
        
        def run_fibonacci_analysis():
            try:
                self.update_status("Analyse Fibonacci en cours...", 20)
                
                # Calculer les fréquences pour différentes fenêtres
                frequency_data = {}
                
                # Fréquences récentes (50 derniers tirages)
                if len(self.tirages_data) >= 50:
                    recent_data = self.tirages_data.tail(50)
                    recent_freq = self.frequency_analyzer.calculate_number_frequencies(recent_data)
                    frequency_data['recent'] = Counter(recent_freq['frequency_absolute'])
                
                # Fréquences moyennes (100 derniers tirages)
                if len(self.tirages_data) >= 100:
                    medium_data = self.tirages_data.tail(100)
                    medium_freq = self.frequency_analyzer.calculate_number_frequencies(medium_data)
                    frequency_data['medium'] = Counter(medium_freq['frequency_absolute'])
                
                # Fréquences globales
                global_freq = self.frequency_analyzer.calculate_number_frequencies(self.tirages_data)
                frequency_data['long'] = Counter(global_freq['frequency_absolute'])
                
                self.update_status("Calcul des poids Fibonacci...", 50)
                
                # Appliquer la pondération Fibonacci adaptative
                adaptive_weights = self.fibonacci_weighting.apply_adaptive_fibonacci_weights(frequency_data)
                
                # Calculer les scores pour les combinaisons
                self.update_status("Calcul des scores de combinaisons...", 70)
                top_numbers = sorted(adaptive_weights.items(), key=lambda x: x[1], reverse=True)[:20]
                numbers_list = [num for num, _ in top_numbers]
                
                combination_scores = self.fibonacci_weighting.calculate_fibonacci_scores(
                    numbers_list, adaptive_weights
                )
                
                self.update_status("Génération du rapport Fibonacci...", 90)
                
                # Génération du rapport
                report = self.fibonacci_weighting.generate_fibonacci_report(adaptive_weights, combination_scores)
                
                self.update_status("Analyse Fibonacci terminée", 100)
                
                # Afficher les résultats
                self.root.after(0, lambda: self.show_fibonacci_results(report, adaptive_weights, combination_scores))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Erreur", f"Erreur d'analyse: {e}"))
                self.update_status("Erreur d'analyse", 0)
        
        thread = threading.Thread(target=run_fibonacci_analysis)
        thread.daemon = True
        thread.start()
    
    def show_fibonacci_results(self, report: str, weights: dict, scores: dict):
        """Afficher les résultats d'analyse Fibonacci"""
        fib_window = tk.Toplevel(self.root)
        fib_window.title("🌀 Pondération Fibonacci")
        fib_window.geometry("1000x700")
        fib_window.configure(bg='#1a1a2e')
        
        # Notebook pour organiser les résultats
        notebook = ttk.Notebook(fib_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Onglet rapport
        report_frame = ttk.Frame(notebook, style='Dark.TFrame')
        notebook.add(report_frame, text="Rapport")
        
        report_text = scrolledtext.ScrolledText(report_frame, 
                                              bg='#0f0f23', fg='white',
                                              font=('Consolas', 10))
        report_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        report_text.insert(1.0, report)
        
        # Onglet poids détaillés
        weights_frame = ttk.Frame(notebook, style='Dark.TFrame')
        notebook.add(weights_frame, text="Poids Détaillés")
        
        # Treeview pour les poids
        columns = ("Rang", "Numéro", "Poids", "Pourcentage")
        weights_tree = ttk.Treeview(weights_frame, columns=columns, show='headings', height=20)
        
        for col in columns:
            weights_tree.heading(col, text=col)
            weights_tree.column(col, width=100, anchor=tk.CENTER)
        
        # Remplir avec les poids
        sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        for i, (number, weight) in enumerate(sorted_weights, 1):
            percentage = weight * 100
            weights_tree.insert('', 'end', values=(i, number, f"{weight:.4f}", f"{percentage:.2f}%"))
        
        weights_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Onglet combinaisons
        if scores:
            combo_frame = ttk.Frame(notebook, style='Dark.TFrame')
            notebook.add(combo_frame, text="Meilleures Combinaisons")
            
            combo_text = scrolledtext.ScrolledText(combo_frame, 
                                                 bg='#0f0f23', fg='white',
                                                 font=('Consolas', 10))
            combo_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            combo_content = "MEILLEURES COMBINAISONS FIBONACCI\n"
            combo_content += "=" * 40 + "\n\n"
            
            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            for i, (combo, score) in enumerate(sorted_scores[:20], 1):
                combo_str = " - ".join(map(str, sorted(combo)))
                combo_content += f"{i:2d}. [{combo_str}] - Score: {score:.4f}\n"
            
            combo_text.insert(1.0, combo_content)
        
        # Boutons d'action
        button_frame = ttk.Frame(fib_window, style='Dark.TFrame')
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(button_frame, text="Exporter Rapport", 
                  command=lambda: self.export_text_report(report, "rapport_fibonacci.txt"),
                  style='Blue.TButton').pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Utiliser pour Prédictions", 
                  command=lambda: self.use_fibonacci_weights(weights),
                  style='Gold.TButton').pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Fermer", 
                  command=fib_window.destroy,
                  style='Blue.TButton').pack(side=tk.RIGHT, padx=5)
    
    def use_fibonacci_weights(self, weights: dict):
        """Utiliser les poids Fibonacci pour les prédictions"""
        try:
            # Mettre à jour les numéros sélectionnés avec les meilleurs poids
            self.clear_selection()
            
            sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
            top_numbers = [num for num, _ in sorted_weights[:self.nb_numeros_var.get()]]
            
            for num in top_numbers:
                if 1 <= num <= 70:
                    self.toggle_number(num)
            
            messagebox.showinfo("Succès", f"Sélection mise à jour avec les {len(top_numbers)} meilleurs numéros Fibonacci")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'application des poids: {e}")
    
    def export_text_report(self, text: str, filename: str):
        """Exporter un rapport texte"""
        try:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialvalue=filename
            )
            
            if filepath:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(text)
                messagebox.showinfo("Export réussi", f"Rapport exporté vers {filepath}")
                
        except Exception as e:
            messagebox.showerror("Erreur d'export", str(e))
    
    def lancer_backtesting(self):
        """Lancer le backtesting des stratégies"""
        if not self.tirages_data:
            messagebox.showwarning("Pas de données", "Veuillez d'abord charger les données")
            return
        
        # Ouvrir la fenêtre de configuration du backtesting
        self.open_backtesting_window()
    
    def open_backtesting_window(self):
        """Ouvrir la fenêtre de configuration du backtesting"""
        bt_window = tk.Toplevel(self.root)
        bt_window.title("🧪 Backtesting des Stratégies")
        bt_window.geometry("600x500")
        bt_window.configure(bg='#1a1a2e')
        
        # Configuration du backtesting
        config_frame = ttk.LabelFrame(bt_window, text="Configuration", style='Dark.TFrame')
        config_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Paramètres
        ttk.Label(config_frame, text="Fenêtre d'analyse:", style='Dark.TLabel').grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        lookback_var = tk.IntVar(value=50)
        ttk.Spinbox(config_frame, from_=20, to=200, textvariable=lookback_var, width=10).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(config_frame, text="Mise par jeu (€):", style='Dark.TLabel').grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        bet_var = tk.DoubleVar(value=1.0)
        ttk.Spinbox(config_frame, from_=0.5, to=10.0, increment=0.5, textvariable=bet_var, width=10).grid(row=1, column=1, padx=5, pady=2)
        
        ttk.Label(config_frame, text="Nombre de numéros:", style='Dark.TLabel').grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        num_numbers_var = tk.IntVar(value=5)
        ttk.Spinbox(config_frame, from_=4, to=10, textvariable=num_numbers_var, width=10).grid(row=2, column=1, padx=5, pady=2)
        
        # Sélection des stratégies
        strategies_frame = ttk.LabelFrame(bt_window, text="Stratégies à Tester", style='Dark.TFrame')
        strategies_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Variables pour les stratégies
        strategy_vars = {
            'Fréquence': tk.BooleanVar(value=True),
            'Écarts': tk.BooleanVar(value=True),
            'Aléatoire': tk.BooleanVar(value=True)
        }
        
        for i, (strategy, var) in enumerate(strategy_vars.items()):
            ttk.Checkbutton(strategies_frame, text=strategy, variable=var, 
                           style='Dark.TLabel').grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
        
        # Zone de résultats
        results_frame = ttk.LabelFrame(bt_window, text="Résultats", style='Dark.TFrame')
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        results_text = scrolledtext.ScrolledText(results_frame, height=10,
                                               bg='#0f0f23', fg='white',
                                               font=('Consolas', 9))
        results_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Boutons
        button_frame = ttk.Frame(bt_window, style='Dark.TFrame')
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        def run_backtest():
            try:
                results_text.delete(1.0, tk.END)
                results_text.insert(tk.END, "Démarrage du backtesting...\n")
                bt_window.update()
                
                # Importer les stratégies de test
                from keno_backtesting import random_strategy, frequency_strategy, gap_strategy
                
                # Préparer les stratégies sélectionnées
                strategies = {}
                if strategy_vars['Fréquence'].get():
                    strategies['Fréquence'] = {
                        'function': frequency_strategy,
                        'params': {'num_numbers': num_numbers_var.get()}
                    }
                if strategy_vars['Écarts'].get():
                    strategies['Écarts'] = {
                        'function': gap_strategy,
                        'params': {'num_numbers': num_numbers_var.get()}
                    }
                if strategy_vars['Aléatoire'].get():
                    strategies['Aléatoire'] = {
                        'function': random_strategy,
                        'params': {'num_numbers': num_numbers_var.get()}
                    }
                
                if not strategies:
                    messagebox.showwarning("Aucune stratégie", "Veuillez sélectionner au moins une stratégie")
                    return
                
                # Paramètres communs
                common_params = {
                    'lookback_window': lookback_var.get(),
                    'bet_amount': bet_var.get()
                }
                
                results_text.insert(tk.END, f"Test de {len(strategies)} stratégies...\n")
                bt_window.update()
                
                # Lancer la comparaison
                comparison = self.backtester.compare_strategies(
                    self.tirages_data, strategies, common_params
                )
                
                if comparison and 'comparison' in comparison:
                    results_text.insert(tk.END, "\nRÉSULTATS DU BACKTESTING\n")
                    results_text.insert(tk.END, "=" * 30 + "\n")
                    
                    # Classement par ROI
                    roi_ranking = comparison['comparison']['metrics_comparison'].get('final_roi', {}).get('ranking', [])
                    if roi_ranking:
                        results_text.insert(tk.END, "\nClassement par ROI:\n")
                        for i, (strategy, roi) in enumerate(roi_ranking, 1):
                            results_text.insert(tk.END, f"  {i}. {strategy}: {roi:.2f}%\n")
                    
                    # Classement par taux de réussite
                    win_rate_ranking = comparison['comparison']['metrics_comparison'].get('win_rate', {}).get('ranking', [])
                    if win_rate_ranking:
                        results_text.insert(tk.END, "\nClassement par taux de réussite:\n")
                        for i, (strategy, rate) in enumerate(win_rate_ranking, 1):
                            results_text.insert(tk.END, f"  {i}. {strategy}: {rate:.2f}%\n")
                    
                    # Détails par stratégie
                    results_text.insert(tk.END, "\nDétails par stratégie:\n")
                    for strategy_name, result in comparison['individual_results'].items():
                        if result and 'financial_metrics' in result:
                            fm = result['financial_metrics']
                            pm = result['performance_metrics']
                            results_text.insert(tk.END, f"\n{strategy_name}:\n")
                            results_text.insert(tk.END, f"  ROI: {fm.get('final_roi', 0):.2f}%\n")
                            results_text.insert(tk.END, f"  Taux réussite: {pm.get('win_rate', 0):.2f}%\n")
                            results_text.insert(tk.END, f"  Jeux testés: {result['test_period'].get('total_games', 0)}\n")
                
                results_text.insert(tk.END, "\nBacktesting terminé!\n")
                
            except Exception as e:
                results_text.insert(tk.END, f"\nErreur: {e}\n")
        
        ttk.Button(button_frame, text="Lancer Backtesting", 
                  command=run_backtest,
                  style='Gold.TButton').pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Fermer", 
                  command=bt_window.destroy,
                  style='Blue.TButton').pack(side=tk.RIGHT, padx=5)

if __name__ == "__main__":
    main()

