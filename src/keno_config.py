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
    
    # Date de transition au nouveau format
    TRANSITION_DATE = datetime(2025, 1, 1).date()
    
    # Configuration ancien Keno (archive)
    OLD_CONFIG = {
        'min_number': 1,
        'max_number': 70,
        'numbers_per_draw': 20,
        'draws_per_day': 2,  # midi et soir
        'version': KenoVersion.OLD
    }
    
    # Configuration nouveau Keno 2025 (production)
    NEW_CONFIG = {
        'min_number': 1,
        'max_number': 56,
        'numbers_per_draw': 16,
        'draws_per_day': 1,  # un seul tirage par jour
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

