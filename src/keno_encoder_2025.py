#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Encodeur Keno 2025 - Nouvelle génération
Convertit les tirages et leurs caractéristiques en vecteurs numériques (embeddings)
pour l'exploitation par l'IA

Spécifications FDJ 2025:
- 56 numéros possibles (1-56)
- 16 numéros tirés par tirage
- 1 tirage par jour
"""

import numpy as np
import pandas as pd
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, date
import logging

from keno_config import KenoConfig

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KenoEncoder2025:
    """
    Encodeur Keno nouvelle génération (FDJ 2025)
    Produit des embeddings exploitables par l'IA pour prédictions et analyses
    """
    
    def __init__(self, config: Optional[dict] = None):
        """
        Initialise l'encodeur Keno 2025
        
        Args:
            config: Configuration Keno (None = config par défaut 2025)
        """
        self.config = config or KenoConfig.get_current_config()
        self.embedding_dim = self.config.get('embedding_dim', 512)
        self.frequency_windows = self.config.get('frequency_windows', [20, 50, 100])
        self.max_number = self.config['max_number']
        self.numbers_per_draw = self.config['numbers_per_draw']
        
        logger.info(f"Encodeur Keno 2025 initialisé: {self.max_number} numéros, "
                   f"{self.numbers_per_draw} tirés, embedding {self.embedding_dim}D")
    
    def encode_tirage(self, numbers: List[int]) -> np.ndarray:
        """
        Encodage binaire d'un tirage
        
        Args:
            numbers: Liste des numéros tirés (doit contenir exactement numbers_per_draw numéros)
            
        Returns:
            Vecteur binaire de dimension max_number (1 = numéro tiré, 0 = absent)
        """
        if len(numbers) != self.numbers_per_draw:
            logger.warning(f"Nombre de numéros incorrect: {len(numbers)} au lieu de {self.numbers_per_draw}")
        
        # Vérifier que tous les numéros sont valides
        valid_numbers = [n for n in numbers if 1 <= n <= self.max_number]
        if len(valid_numbers) != self.numbers_per_draw:
            logger.warning(f"Numéros invalides détectés, ajustement nécessaire")
        
        # Créer le vecteur binaire
        binary_vector = np.zeros(self.max_number, dtype=np.float32)
        for num in valid_numbers:
            if 1 <= num <= self.max_number:
                binary_vector[num - 1] = 1.0
        
        return binary_vector
    
    def calculate_sliding_frequencies(self, df: pd.DataFrame, 
                                      tirage_index: int) -> Dict[str, np.ndarray]:
        """
        Calcule les fréquences glissantes pour différentes fenêtres
        
        Args:
            df: DataFrame contenant l'historique des tirages
            tirage_index: Index du tirage actuel dans le DataFrame
            
        Returns:
            Dict avec les fréquences pour chaque fenêtre (window_20, window_50, window_100, total)
        """
        frequencies = {}
        
        # Tous les tirages jusqu'à l'index actuel
        all_draws = df.iloc[:tirage_index]
        
        # Fréquence totale
        total_freq = np.zeros(self.max_number, dtype=np.float32)
        total_count = 0
        
        for window_size in self.frequency_windows:
            if tirage_index < window_size:
                # Pas assez de données pour cette fenêtre
                window_freq = np.zeros(self.max_number, dtype=np.float32)
            else:
                # Prendre les window_size derniers tirages
                window_draws = df.iloc[tirage_index - window_size:tirage_index]
                window_freq = np.zeros(self.max_number, dtype=np.float32)
                
                for _, row in window_draws.iterrows():
                    numbers = self._extract_numbers_from_row(row)
                    for num in numbers:
                        if 1 <= num <= self.max_number:
                            window_freq[num - 1] += 1.0
                            total_freq[num - 1] += 1.0
                            total_count += 1
                
                # Normaliser par le nombre de tirages dans la fenêtre
                if len(window_draws) > 0:
                    window_freq = window_freq / (len(window_draws) * self.numbers_per_draw)
            
            frequencies[f'window_{window_size}'] = window_freq
        
        # Fréquence totale (normalisée)
        if total_count > 0:
            total_freq = total_freq / total_count
        frequencies['total'] = total_freq
        
        return frequencies
    
    def calculate_gaps(self, df: pd.DataFrame, 
                       tirage_index: int) -> Dict[int, Dict[str, Any]]:
        """
        Calcule les écarts pour chaque numéro
        
        Args:
            df: DataFrame contenant l'historique des tirages
            tirage_index: Index du tirage actuel
            
        Returns:
            Dict par numéro contenant: current_gap, mean_gap, max_gap, last_appearance_date
        """
        gaps_data = {}
        
        # Initialiser tous les numéros
        for num in range(1, self.max_number + 1):
            gaps_data[num] = {
                'current_gap': tirage_index,  # Maximum possible
                'mean_gap': 0.0,
                'max_gap': 0,
                'last_appearance_date': None,
                'appearances': []
            }
        
        # Parcourir l'historique en ordre inverse (du plus récent au plus ancien)
        for idx in range(tirage_index - 1, -1, -1):
            row = df.iloc[idx]
            numbers = self._extract_numbers_from_row(row)
            tirage_date = self._extract_date_from_row(row)
            
            for num in numbers:
                if 1 <= num <= self.max_number:
                    data = gaps_data[num]
                    
                    # Si c'est la première apparition trouvée (plus récente)
                    if data['current_gap'] == tirage_index:
                        data['current_gap'] = tirage_index - idx - 1
                        data['last_appearance_date'] = tirage_date
                    
                    # Enregistrer toutes les apparitions
                    data['appearances'].append(idx)
        
        # Calculer les statistiques des écarts pour chaque numéro
        for num, data in gaps_data.items():
            appearances = data['appearances']
            
            if len(appearances) >= 2:
                # Calculer les écarts entre apparitions
                gaps_list = []
                for i in range(1, len(appearances)):
                    gap = appearances[i-1] - appearances[i]
                    gaps_list.append(gap)
                
                if gaps_list:
                    data['mean_gap'] = float(np.mean(gaps_list))
                    data['max_gap'] = int(max(gaps_list))
            elif len(appearances) == 1:
                # Un seul tirage trouvé, écart = position actuelle - position
                data['mean_gap'] = float(tirage_index - appearances[0])
                data['max_gap'] = int(tirage_index - appearances[0])
            else:
                # Jamais apparu
                data['current_gap'] = tirage_index
                data['mean_gap'] = float(tirage_index)
                data['max_gap'] = tirage_index
        
        return gaps_data
    
    def detect_historical_patterns(self, df: pd.DataFrame, 
                                   tirage_index: int) -> Dict[str, Any]:
        """
        Détecte les patterns historiques dans les tirages
        
        Args:
            df: DataFrame contenant l'historique
            tirage_index: Index du tirage actuel
            
        Returns:
            Dict contenant différents patterns détectés
        """
        patterns = {
            'grouped_numbers': [],  # Numéros sortis ensemble fréquemment
            'repetitions': [],  # Répétitions de combinaisons
            'short_cycles': [],  # Cycles courts détectés
            'long_cycles': [],  # Cycles longs détectés
            'zone_distribution': np.zeros(len(self.config.get('zones', [])), dtype=np.float32),
            'similarity_scores': []  # Similarités avec anciens tirages
        }
        
        if tirage_index < 5:
            return patterns
        
        # Analyser les derniers tirages pour détecter les patterns
        window_size = min(100, tirage_index)
        recent_draws = df.iloc[tirage_index - window_size:tirage_index]
        
        # Pattern 1: Numéros groupés (sortis ensemble)
        number_cooccurrence = defaultdict(int)
        for _, row in recent_draws.iterrows():
            numbers = sorted(self._extract_numbers_from_row(row))
            for i, num1 in enumerate(numbers):
                for num2 in numbers[i+1:]:
                    if abs(num1 - num2) <= 5:  # Numéros proches (à 5 unités)
                        pair = tuple(sorted([num1, num2]))
                        number_cooccurrence[pair] += 1
        
        # Top 10 paires les plus fréquentes
        top_pairs = sorted(number_cooccurrence.items(), key=lambda x: x[1], reverse=True)[:10]
        patterns['grouped_numbers'] = [{'pair': pair, 'count': count} 
                                       for pair, count in top_pairs]
        
        # Pattern 2: Répétitions de numéros consécutifs
        repetition_count = Counter()
        prev_numbers = None
        for _, row in recent_draws.iterrows():
            current_numbers = set(self._extract_numbers_from_row(row))
            if prev_numbers:
                repeated = current_numbers & prev_numbers
                for num in repeated:
                    repetition_count[num] += 1
            prev_numbers = current_numbers
        
        patterns['repetitions'] = [{'number': num, 'count': count} 
                                  for num, count in repetition_count.most_common(10)]
        
        # Pattern 3: Distribution par zones
        zones = self.config.get('zones', [])
        if zones:
            zone_counts = np.zeros(len(zones))
            for _, row in recent_draws.iterrows():
                numbers = self._extract_numbers_from_row(row)
                for num in numbers:
                    for i, (zone_min, zone_max) in enumerate(zones):
                        if zone_min <= num <= zone_max:
                            zone_counts[i] += 1
                            break
            
            # Normaliser
            total_in_zones = np.sum(zone_counts)
            if total_in_zones > 0:
                patterns['zone_distribution'] = zone_counts / total_in_zones
        
        # Pattern 4: Similarité avec anciens tirages
        if tirage_index > 0:
            current_numbers = set(self._extract_numbers_from_row(df.iloc[tirage_index - 1]))
            
            similarities = []
            for idx in range(max(0, tirage_index - 100), tirage_index - 1):
                past_numbers = set(self._extract_numbers_from_row(df.iloc[idx]))
                # Jaccard similarity
                intersection = len(current_numbers & past_numbers)
                union = len(current_numbers | past_numbers)
                similarity = intersection / union if union > 0 else 0
                similarities.append({'index': idx, 'similarity': similarity})
            
            # Top 5 tirages les plus similaires
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            patterns['similarity_scores'] = similarities[:5]
        
        return patterns
    
    def create_embedding(self, df: pd.DataFrame, tirage_index: int) -> np.ndarray:
        """
        Crée l'embedding complet pour un tirage
        
        Args:
            df: DataFrame contenant l'historique
            tirage_index: Index du tirage à encoder
            
        Returns:
            Vecteur d'embedding de dimension embedding_dim
        """
        if tirage_index >= len(df):
            raise ValueError(f"Index {tirage_index} hors limites (taille: {len(df)})")
        
        embedding_parts = []
        
        # 1. Encodage binaire du dernier tirage (56D)
        if tirage_index > 0:
            last_tirage = df.iloc[tirage_index - 1]
            last_numbers = self._extract_numbers_from_row(last_tirage)
            binary_encoding = self.encode_tirage(last_numbers)
            embedding_parts.append(binary_encoding)
        else:
            embedding_parts.append(np.zeros(self.max_number, dtype=np.float32))
        
        # 2. Fréquences glissantes (20, 50, 100, total) = 56 * 4 = 224D
        frequencies = self.calculate_sliding_frequencies(df, tirage_index)
        for window_name in ['window_20', 'window_50', 'window_100', 'total']:
            if window_name in frequencies:
                embedding_parts.append(frequencies[window_name])
            else:
                embedding_parts.append(np.zeros(self.max_number, dtype=np.float32))
        
        # 3. Écarts normalisés (4 métriques * 56 numéros = 224D)
        gaps = self.calculate_gaps(df, tirage_index)
        
        # Normaliser les écarts (diviser par max possible pour avoir des valeurs 0-1)
        max_possible_gap = max(tirage_index, 100)
        
        current_gaps = np.array([gaps[num]['current_gap'] / max_possible_gap 
                                for num in range(1, self.max_number + 1)], dtype=np.float32)
        mean_gaps = np.array([min(gaps[num]['mean_gap'] / max_possible_gap, 1.0) 
                             for num in range(1, self.max_number + 1)], dtype=np.float32)
        max_gaps = np.array([min(gaps[num]['max_gap'] / max_possible_gap, 1.0) 
                            for num in range(1, self.max_number + 1)], dtype=np.float32)
        
        # Score d'écart (current / mean, normalisé)
        gap_scores = np.array([min(gaps[num]['current_gap'] / (gaps[num]['mean_gap'] + 1), 2.0) / 2.0
                              for num in range(1, self.max_number + 1)], dtype=np.float32)
        
        embedding_parts.extend([current_gaps, mean_gaps, max_gaps, gap_scores])
        
        # 4. Patterns historiques
        patterns = self.detect_historical_patterns(df, tirage_index)
        
        # Distribution par zones (6 zones = 6D)
        embedding_parts.append(patterns['zone_distribution'])
        
        # Top répétitions (encodage binaire des top 10) = 56D
        top_repeats = np.zeros(self.max_number, dtype=np.float32)
        for rep_info in patterns['repetitions'][:10]:
            num = rep_info['number']
            if 1 <= num <= self.max_number:
                top_repeats[num - 1] = min(rep_info['count'] / 10.0, 1.0)
        embedding_parts.append(top_repeats)
        
        # Similarité moyenne avec top 5 = 1D
        if patterns['similarity_scores']:
            avg_similarity = np.mean([s['similarity'] for s in patterns['similarity_scores']])
        else:
            avg_similarity = 0.0
        embedding_parts.append(np.array([avg_similarity], dtype=np.float32))
        
        # 5. Statistiques temporelles (jour semaine, jour mois, etc.) = 5D
        if tirage_index > 0:
            tirage_date = self._extract_date_from_row(df.iloc[tirage_index - 1])
            if tirage_date:
                day_of_week = tirage_date.weekday() / 6.0  # 0-1
                day_of_month = tirage_date.day / 31.0  # 0-1
                month = tirage_date.month / 12.0  # 0-1
            else:
                day_of_week = day_of_month = month = 0.5
        else:
            day_of_week = day_of_month = month = 0.5
        
        # Position dans l'historique
        position = tirage_index / max(len(df), 1000)  # 0-1
        diversity = len(set([n for row_idx in range(max(0, tirage_index - 20), tirage_index)
                            for n in self._extract_numbers_from_row(df.iloc[row_idx])])) / self.max_number
        
        temporal_features = np.array([day_of_week, day_of_month, month, position, diversity], 
                                    dtype=np.float32)
        embedding_parts.append(temporal_features)
        
        # Assembler tous les composants
        full_embedding = np.concatenate(embedding_parts)
        
        # Si la dimension dépasse embedding_dim, réduire avec PCA ou tronquer
        # Si la dimension est inférieure, compléter avec des zéros
        if len(full_embedding) > self.embedding_dim:
            # Utiliser les premières dimensions les plus importantes
            full_embedding = full_embedding[:self.embedding_dim]
        elif len(full_embedding) < self.embedding_dim:
            # Compléter avec des zéros
            padding = np.zeros(self.embedding_dim - len(full_embedding), dtype=np.float32)
            full_embedding = np.concatenate([full_embedding, padding])
        
        return full_embedding
    
    def _extract_numbers_from_row(self, row: pd.Series) -> List[int]:
        """Extrait les numéros d'une ligne de DataFrame"""
        numbers = []
        
        # Essayer différents formats de colonnes
        if 'numeros' in row and pd.notna(row['numeros']):
            # Format liste ou array
            numeros = row['numeros']
            if isinstance(numeros, (list, np.ndarray)):
                numbers = [int(n) for n in numeros if pd.notna(n)]
            elif isinstance(numeros, str):
                # Format string séparé par virgules
                numbers = [int(n.strip()) for n in numeros.split(',') if n.strip().isdigit()]
        else:
            # Format colonnes numero_1, numero_2, ...
            for i in range(1, self.numbers_per_draw + 1):
                col_name = f'numero_{i}'
                if col_name in row and pd.notna(row[col_name]):
                    numbers.append(int(row[col_name]))
        
        return numbers
    
    def _extract_date_from_row(self, row: pd.Series) -> Optional[date]:
        """Extrait la date d'une ligne de DataFrame"""
        if 'date_tirage' in row and pd.notna(row['date_tirage']):
            date_val = row['date_tirage']
            if isinstance(date_val, date):
                return date_val
            elif isinstance(date_val, datetime):
                return date_val.date()
            elif isinstance(date_val, str):
                try:
                    return datetime.strptime(date_val, '%Y-%m-%d').date()
                except:
                    pass
        return None
    
    def encode_batch(self, df: pd.DataFrame, start_index: int = 0, 
                     end_index: Optional[int] = None) -> np.ndarray:
        """
        Encode un batch de tirages pour l'entraînement
        
        Args:
            df: DataFrame contenant l'historique
            start_index: Index de début (inclus)
            end_index: Index de fin (exclus, None = fin du DataFrame)
            
        Returns:
            Matrice d'embeddings (n_samples, embedding_dim)
        """
        if end_index is None:
            end_index = len(df)
        
        embeddings = []
        for idx in range(start_index, end_index):
            embedding = self.create_embedding(df, idx)
            embeddings.append(embedding)
        
        return np.array(embeddings, dtype=np.float32)


def main():
    """Test du module d'encodage"""
    print("Test de l'encodeur Keno 2025...")
    
    # Créer des données de test
    test_data = []
    for i in range(150):
        # Simuler des tirages avec 16 numéros parmi 56
        import random
        numbers = sorted(random.sample(range(1, 57), 16))
        test_date = datetime(2025, 1, 1).date() + pd.Timedelta(days=i)
        test_data.append({
            'date_tirage': test_date,
            'numero_1': numbers[0],
            'numero_2': numbers[1],
            'numero_3': numbers[2],
            'numero_4': numbers[3],
            'numero_5': numbers[4],
            'numero_6': numbers[5],
            'numero_7': numbers[6],
            'numero_8': numbers[7],
            'numero_9': numbers[8],
            'numero_10': numbers[9],
            'numero_11': numbers[10],
            'numero_12': numbers[11],
            'numero_13': numbers[12],
            'numero_14': numbers[13],
            'numero_15': numbers[14],
            'numero_16': numbers[15]
        })
    
    df = pd.DataFrame(test_data)
    
    # Créer l'encodeur
    encoder = KenoEncoder2025()
    
    # Tester l'encodage
    test_index = 100
    embedding = encoder.create_embedding(df, test_index)
    
    print(f"✅ Embedding créé avec succès")
    print(f"   Dimension: {len(embedding)}D")
    print(f"   Forme: {embedding.shape}")
    print(f"   Valeurs min/max: {embedding.min():.4f} / {embedding.max():.4f}")
    print(f"   Moyenne: {embedding.mean():.4f}")
    
    # Tester le batch encoding
    batch_embeddings = encoder.encode_batch(df, start_index=50, end_index=100)
    print(f"\n✅ Batch encoding réussi")
    print(f"   Forme: {batch_embeddings.shape}")
    print(f"   {len(batch_embeddings)} embeddings générés")
    
    print("\n✅ Tests terminés avec succès!")


if __name__ == "__main__":
    main()

