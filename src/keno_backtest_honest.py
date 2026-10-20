#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backtest HONNÊTE des stratégies de « prédiction » Keno.

Question posée : une stratégie (numéros chauds, froids, en retard...) permet-elle
réellement de trouver PLUS de bons numéros que le pur hasard ?

Méthode (walk-forward, sans tricher sur le futur) :
    - On parcourt l'historique tirage par tirage, dans l'ordre chronologique.
    - À chaque tirage t, on construit une grille de `pick` numéros en n'utilisant
      QUE les tirages 0..t-1 (jamais le tirage t lui-même).
    - On compte combien de ces numéros sortent effectivement au tirage t.
    - On moyenne sur des milliers de tirages, pour chaque stratégie.

Référence mathématique : si les tirages sont aléatoires (ils le sont), le nombre
moyen de bons numéros d'une grille de `pick` numéros vaut exactement

        E = pick × (numéros_tirés / numéros_total)

quelle que soit la façon de choisir la grille. Une stratégie « qui marche »
devrait battre cette valeur de référence de façon statistiquement significative.
Spoiler mathématique : aucune ne le peut, car les tirages sont sans mémoire.
Ce script le MESURE au lieu de l'affirmer.

Usage :
    python3 keno_backtest_honest.py [chemin_csv] [--pick 10] [--window 100] [--warmup 200]
"""

from __future__ import annotations

import argparse
import csv
import os
import random
import statistics
from collections import Counter
from typing import Callable, Dict, List, Set


def load_draws(csv_path: str) -> List[Set[int]]:
    """Charge les tirages depuis le CSV, renvoyés dans l'ordre CHRONOLOGIQUE ascendant.

    Détecte automatiquement les colonnes numero_*. Le fichier d'origine est en
    ordre décroissant (plus récent en premier) ; on le remet à l'endroit.
    """
    draws: List[Set[int]] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        num_cols = [c for c in reader.fieldnames or []
                    if c.startswith("numero_") and c.split("_")[-1].isdigit()]
        num_cols.sort(key=lambda c: int(c.split("_")[-1]))
        for row in reader:
            nums = set()
            for c in num_cols:
                v = row.get(c)
                if v not in (None, "", "None"):
                    try:
                        nums.add(int(v))
                    except (TypeError, ValueError):
                        pass
            if nums:
                draws.append(nums)
    # Le CSV FDJ est trié du plus récent au plus ancien : on inverse.
    draws.reverse()
    return draws


def infer_format(draws: List[Set[int]]) -> Dict[str, int]:
    """Déduit (total, numéros tirés) à partir des données observées."""
    max_num = max((max(d) for d in draws if d), default=0)
    typical_drawn = Counter(len(d) for d in draws).most_common(1)[0][0]
    return {"total": max_num, "drawn": typical_drawn}


# --- Stratégies : chacune renvoie une grille de `pick` numéros à partir de
#     l'historique (liste de tirages passés) et de la taille de population. -----

def strat_hot(history: List[Set[int]], pick: int, total: int, last_seen: Dict[int, int], t: int) -> Set[int]:
    freq = Counter()
    for d in history:
        freq.update(d)
    return {n for n, _ in freq.most_common(pick)}


def strat_cold(history: List[Set[int]], pick: int, total: int, last_seen: Dict[int, int], t: int) -> Set[int]:
    freq = Counter({n: 0 for n in range(1, total + 1)})
    for d in history:
        freq.update(d)
    least = sorted(freq.items(), key=lambda kv: kv[1])[:pick]
    return {n for n, _ in least}


def strat_overdue(history: List[Set[int]], pick: int, total: int, last_seen: Dict[int, int], t: int) -> Set[int]:
    # Plus grand écart depuis la dernière sortie (numéros « en retard »).
    gaps = {n: t - last_seen.get(n, -1) for n in range(1, total + 1)}
    top = sorted(gaps.items(), key=lambda kv: kv[1], reverse=True)[:pick]
    return {n for n, _ in top}


def strat_random(history: List[Set[int]], pick: int, total: int, last_seen: Dict[int, int], t: int) -> Set[int]:
    return set(random.sample(range(1, total + 1), pick))


STRATEGIES: Dict[str, Callable] = {
    "Numéros chauds (fréquents)": strat_hot,
    "Numéros froids (rares)": strat_cold,
    "Numéros en retard (écart)": strat_overdue,
    "Hasard (référence)": strat_random,
}


def backtest(draws: List[Set[int]], pick: int, window: int, warmup: int, seed: int = 42) -> None:
    random.seed(seed)
    fmt = infer_format(draws)
    total, drawn = fmt["total"], fmt["drawn"]
    expected = pick * drawn / total

    results: Dict[str, List[int]] = {name: [] for name in STRATEGIES}
    last_seen: Dict[int, int] = {}

    for t, actual in enumerate(draws):
        if t >= warmup:
            window_hist = draws[max(0, t - window):t]
            for name, fn in STRATEGIES.items():
                grid = fn(window_hist, pick, total, last_seen, t)
                results[name].append(len(grid & actual))
        # Mettre à jour la dernière apparition APRÈS avoir prédit ce tirage.
        for n in actual:
            last_seen[n] = t

    n_tests = len(draws) - warmup
    print("=" * 70)
    print("BACKTEST HONNÊTE — les stratégies battent-elles le hasard ?")
    print("=" * 70)
    print(f"Fichier       : {n_tests} tirages testés (après {warmup} de rodage)")
    print(f"Format détecté: {drawn} numéros tirés sur {total}")
    print(f"Grille jouée  : {pick} numéros | Fenêtre d'analyse : {window} tirages")
    print()
    print(f"Espérance mathématique (hasard pur) = {pick} × {drawn}/{total} "
          f"= {expected:.4f} bons numéros par grille")
    print()
    print(f"{'Stratégie':<32} | {'Moy. bons':>10} | {'Écart vs hasard':>16} | {'z-score':>8}")
    print("-" * 74)

    for name in STRATEGIES:
        vals = results[name]
        mean = statistics.fmean(vals)
        # z-score de la moyenne par rapport à l'espérance théorique.
        if len(vals) > 1 and statistics.pstdev(vals) > 0:
            se = statistics.pstdev(vals) / (len(vals) ** 0.5)
            z = (mean - expected) / se
        else:
            z = 0.0
        ecart = mean - expected
        print(f"{name:<32} | {mean:>10.4f} | {ecart:>+16.4f} | {z:>8.2f}")

    print("-" * 74)
    print()
    print("LECTURE :")
    print("  • « Moy. bons » ≈ l'espérance théorique pour TOUTES les stratégies.")
    print("  • Un |z-score| au-delà de ~2 à 3 signalerait un écart significatif.")
    print("  • Aucune stratégie ne dépasse durablement le hasard : c'est attendu,")
    print("    les tirages sont indépendants et sans mémoire.")
    print()
    print("CONCLUSION : ce backtest ne sert pas à gagner, il sert à ne pas se mentir.")
    print("Il quantifie honnêtement l'absence d'avantage prédictif.")


def main() -> None:
    default_csv = os.path.join(os.path.dirname(__file__), "tirages_keno_format_db.csv")
    parser = argparse.ArgumentParser(description="Backtest honnête des stratégies Keno")
    parser.add_argument("csv", nargs="?", default=default_csv, help="Chemin du CSV des tirages")
    parser.add_argument("--pick", type=int, default=10, help="Numéros joués par grille")
    parser.add_argument("--window", type=int, default=100, help="Fenêtre d'analyse (tirages)")
    parser.add_argument("--warmup", type=int, default=200, help="Tirages de rodage avant mesure")
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        raise SystemExit(f"Fichier introuvable : {args.csv}")

    draws = load_draws(args.csv)
    if len(draws) <= args.warmup:
        raise SystemExit(f"Pas assez de tirages ({len(draws)}) pour un rodage de {args.warmup}.")
    backtest(draws, pick=args.pick, window=args.window, warmup=args.warmup)


if __name__ == "__main__":
    main()
