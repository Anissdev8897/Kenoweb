#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de configuration pour la gestion des versions Keno
Séparation entre ancien Keno (archive) et nouveau Keno 2025 (production)
"""

from datetime import datetime
from enum import Enum
from typing import Optional

class KenoVersion(Enum):
    """Versions du Keno supportées"""
    OLD = "old"  # Ancien format : 20 numéros sur 70, 2 tirages/jour
    NEW_2025 = "new_2025"  # Nouveau format FDJ 2025 : 16 numéros sur 56, 1 tirage/jour


class KenoConfig:
    """
    Configuration centralisée pour les paramètres Keno
    Permet de gérer facilement la transition et la compatibilité
    """
    
    # Date de transition au nouveau format.
    # Le changement officiel FDJ (grille 56/16, un seul tirage par jour à 20h) est
    # entré en vigueur le 3 novembre 2025. Les tirages antérieurs à cette date
    # relèvent de l'ancien format 70/20 (deux tirages par jour).
    TRANSITION_DATE = datetime(2025, 11, 3).date()
    
    # Configuration ancien Keno (archive)
    OLD_CONFIG = {
        'min_number': 1,
        'max_number': 70,
        'numbers_per_draw': 20,
        'draws_per_day': 2,  # midi et soir
        'min_pick': 2,
        'max_pick': 10,
        'version': KenoVersion.OLD
    }
    
    # Configuration nouveau Keno 2025 (production) — en vigueur depuis le 03/11/2025
    NEW_CONFIG = {
        'min_number': 1,
        'max_number': 56,
        'numbers_per_draw': 16,
        'draws_per_day': 1,          # un seul tirage par jour
        'draw_time': '20:00',        # tirage à 20h
        'min_pick': 4,               # minimum de numéros cochables par le joueur
        'max_pick': 10,              # maximum de numéros cochables
        'stakes': [1, 2, 3, 5, 10],  # mises possibles (€)
        'multiplier_values': [2, 3, 5],  # coefficient Multiplicateur tiré au sort
        'version': KenoVersion.NEW_2025,
        'embedding_dim': 512,  # Dimension recommandée pour l'embedding
        'frequency_windows': [20, 50, 100],  # Fenêtres de fréquences glissantes
        'zones': [
            (1, 10), (11, 20), (21, 30), (31, 40), (41, 50), (51, 56)
        ]  # Zones pour l'analyse
    }
    
    @staticmethod
    def get_config_for_date(date: Optional[datetime.date] = None) -> dict:
        """
        Retourne la configuration appropriée selon la date
        
        Args:
            date: Date du tirage (None = date actuelle)
            
        Returns:
            Configuration dict pour cette date
        """
        if date is None:
            date = datetime.now().date()
        
        if date >= KenoConfig.TRANSITION_DATE:
            return KenoConfig.NEW_CONFIG.copy()
        else:
            return KenoConfig.OLD_CONFIG.copy()
    
    @staticmethod
    def get_current_config() -> dict:
        """Retourne la configuration actuelle (nouveau format)"""
        return KenoConfig.NEW_CONFIG.copy()
    
    @staticmethod
    def is_new_format(date: Optional[datetime.date] = None) -> bool:
        """Vérifie si la date correspond au nouveau format"""
        if date is None:
            date = datetime.now().date()
        return date >= KenoConfig.TRANSITION_DATE
    
    @staticmethod
    def get_zone_for_number(number: int, config: Optional[dict] = None) -> Optional[tuple]:
        """
        Retourne la zone d'un numéro selon la configuration
        
        Args:
            number: Numéro à analyser
            config: Configuration à utiliser (None = config actuelle)
            
        Returns:
            Tuple (min_zone, max_zone) ou None si pas de zones définies
        """
        if config is None:
            config = KenoConfig.get_current_config()
        
        if 'zones' not in config:
            return None
        
        for zone_min, zone_max in config['zones']:
            if zone_min <= number <= zone_max:
                return (zone_min, zone_max)
        
        return None

