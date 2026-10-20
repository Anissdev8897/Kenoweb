#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Moteur de probabilités EXACT pour le Keno FDJ — nouveau format (depuis le 3 novembre 2025).

Format officiel en vigueur :
    - Grille de 56 numéros (1 à 56)
    - 16 numéros tirés au sort par tirage
    - Le joueur coche de 4 à 10 numéros
    - 1 tirage par jour à 20h
    - Mises : 1, 2, 3, 5 ou 10 €
    - Option Multiplicateur : coefficient tiré parmi x2, x3, x5

------------------------------------------------------------------------------
POURQUOI CE MODULE EXISTE
------------------------------------------------------------------------------
Un tirage de Keno est un processus ALÉATOIRE et SANS MÉMOIRE : chaque numéro a
exactement la même probabilité de sortir à chaque tirage, indépendamment de
l'historique. Aucune analyse de fréquences, d'écarts, de « numéros chauds/froids »
ni aucun modèle de machine learning ne peut prédire le prochain tirage ni créer
un avantage sur le hasard. C'est une conséquence mathématique, pas une opinion.

Ce que l'on PEUT calculer, en revanche, est 100 % exact et vérifiable : la
probabilité d'obtenir exactement k bons numéros suit la LOI HYPERGÉOMÉTRIQUE.
Ce module fournit ces probabilités exactes (arithmétique entière, sans arrondi),
les cotes correspondantes (« 1 chance sur N ») et, lorsqu'un barème officiel
complet est fourni, l'espérance de gain et le taux de retour au joueur.

C'est l'outil honnête : il dit la vérité sur les chances réelles au lieu de
promettre des prédictions impossibles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from math import comb
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Configuration du format
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KenoFormat:
    """Paramètres d'une matrice de Keno (population, boules tirées, bornes de jeu)."""

    total_numbers: int          # Taille de la grille (population)
    numbers_drawn: int          # Numéros tirés par tirage
    min_pick: int               # Minimum de numéros cochables par le joueur
    max_pick: int               # Maximum de numéros cochables par le joueur
    label: str = ""

    def validate_pick(self, picked: int) -> None:
        if not (self.min_pick <= picked <= self.max_pick):
            raise ValueError(
                f"Nombre de numéros joués invalide : {picked}. "
                f"Autorisé pour « {self.label or 'ce format'} » : "
                f"{self.min_pick} à {self.max_pick}."
            )


# Nouveau Keno FDJ, en vigueur depuis le 3 novembre 2025.
KENO_FDJ_2025 = KenoFormat(
    total_numbers=56,
    numbers_drawn=16,
    min_pick=4,
    max_pick=10,
    label="Keno FDJ 56/16 (depuis le 03/11/2025)",
)

# Ancien Keno FDJ (archive, jusqu'au 02/11/2025) : utile pour analyser les
# données historiques antérieures au changement de format.
KENO_FDJ_LEGACY = KenoFormat(
    total_numbers=70,
    numbers_drawn=20,
    min_pick=2,
    max_pick=10,
    label="Keno FDJ 70/20 (ancien format, jusqu'au 02/11/2025)",
)


# ---------------------------------------------------------------------------
# Probabilités exactes (loi hypergéométrique)
# ---------------------------------------------------------------------------

def hypergeometric(total: int, successes: int, draws: int, hits: int) -> Fraction:
    """
    Probabilité exacte d'obtenir `hits` succès en tirant `draws` éléments sans
    remise dans une population de `total` éléments dont `successes` sont des succès.

        P = C(successes, hits) * C(total - successes, draws - hits) / C(total, draws)

    Retourne une Fraction (valeur rationnelle exacte, aucun arrondi).
    """
    if hits < 0 or hits > draws or hits > successes:
        return Fraction(0)
    if draws - hits > total - successes:
        return Fraction(0)
    numerator = comb(successes, hits) * comb(total - successes, draws - hits)
    denominator = comb(total, draws)
    return Fraction(numerator, denominator)


def match_probability(fmt: KenoFormat, picked: int, matches: int) -> Fraction:
    """
    Probabilité EXACTE d'obtenir exactement `matches` bons numéros quand on joue
    `picked` numéros sur ce format.

    On considère les `picked` numéros du joueur comme la « population marquée » et
    les `numbers_drawn` boules du tirage comme l'échantillon (la symétrie de la loi
    hypergéométrique garantit un résultat identique dans les deux sens).
    """
    fmt.validate_pick(picked)
    return hypergeometric(
        total=fmt.total_numbers,
        successes=picked,
        draws=fmt.numbers_drawn,
        hits=matches,
    )


def probability_table(fmt: KenoFormat, picked: int) -> List[Tuple[int, Fraction]]:
    """
    Table complète (matches, probabilité exacte) pour toutes les valeurs possibles
    de bons numéros, de 0 à `picked`.
    """
    fmt.validate_pick(picked)
    max_matches = min(picked, fmt.numbers_drawn)
    return [(k, match_probability(fmt, picked, k)) for k in range(0, max_matches + 1)]


def odds_one_in(prob: Fraction) -> Optional[float]:
    """Convertit une probabilité en cote « 1 chance sur N ». None si probabilité nulle."""
    if prob <= 0:
        return None
    return float(1 / prob)


def at_least_probability(fmt: KenoFormat, picked: int, min_matches: int) -> Fraction:
    """Probabilité exacte d'obtenir AU MOINS `min_matches` bons numéros."""
    return sum(
        (p for k, p in probability_table(fmt, picked) if k >= min_matches),
        Fraction(0),
    )


# ---------------------------------------------------------------------------
# Barème (grille des gains)
# ---------------------------------------------------------------------------
# Rapports pour une mise de 1 € (hors option Multiplicateur), nouveau format FDJ.
#
# ATTENTION — DONNÉES PARTIELLES :
# Seules les valeurs ci-dessous ont pu être confirmées via des sources publiques
# au moment de l'écriture. Les cases laissées à None doivent être complétées
# depuis la grille officielle FDJ (fdj.fr → Keno → « Comment jouer ») AVANT tout
# calcul d'espérance de gain. Aucune valeur n'est inventée : une case None
# signifie « inconnue », pas « gain nul ».
#
# Clé = nombre de numéros joués ; sous-clé = nombre de bons numéros ; valeur = gain en € pour 1 € misé.
PAYOUTS_1EUR: Dict[int, Dict[int, Optional[float]]] = {
    4: {4: None, 3: None, 2: None},
    5: {5: None, 4: None, 3: None},
    6: {6: None, 5: None, 4: None, 3: None},
    7: {7: 3000.0, 6: 90.0, 5: 5.0, 4: None, 3: None},
    8: {8: None, 7: None, 6: None, 5: None, 4: None},
    9: {9: 30000.0, 8: None, 7: None, 6: None, 5: None, 4: None},
    # Pour 10/10, le lot « Gagnant à vie » peut être pris en cash (200 000 €)
    # ou en rente (10 000 €/an). On retient ici l'équivalent cash pour le calcul.
    10: {10: 200000.0, 9: None, 8: None, 7: None, 6: None, 5: None, 4: None, 0: None},
}

MULTIPLIER_VALUES: Tuple[int, ...] = (2, 3, 5)  # coefficient tiré au sort si option activée
STAKES: Tuple[int, ...] = (1, 2, 3, 5, 10)      # mises possibles en euros


@dataclass
class ExpectedValueResult:
    picked: int
    stake: float
    expected_gain: float          # gain moyen par grille (€)
    return_rate: Optional[float]  # taux de retour au joueur (expected_gain / stake)
    complete: bool                # True si le barème utilisé était complet
    missing_tiers: List[int] = field(default_factory=list)


def expected_value(
    fmt: KenoFormat,
    picked: int,
    stake: float = 1.0,
    payouts_1eur: Optional[Dict[int, Optional[float]]] = None,
) -> ExpectedValueResult:
    """
    Espérance de gain et taux de retour pour une grille de `picked` numéros.

    `payouts_1eur` : dict {bons_numeros: gain_en_euros_pour_1€}. Par défaut, la
    ligne correspondante de PAYOUTS_1EUR est utilisée. Si des cases sont None
    (barème incomplet), le calcul est marqué non fiable (`complete=False`) et les
    paliers manquants sont listés : complétez-les depuis la grille officielle FDJ.
    """
    fmt.validate_pick(picked)
    table = payouts_1eur if payouts_1eur is not None else PAYOUTS_1EUR.get(picked, {})

    missing = sorted([k for k, v in table.items() if v is None], reverse=True)
    expected = 0.0
    for matches, prob in probability_table(fmt, picked):
        gain_1eur = table.get(matches)
        if gain_1eur:  # ignore None et 0
            expected += float(prob) * gain_1eur * stake

    complete = len(missing) == 0 and len(table) > 0
    return_rate = (expected / stake) if stake else None
    return ExpectedValueResult(
        picked=picked,
        stake=stake,
        expected_gain=expected,
        return_rate=return_rate,
        complete=complete,
        missing_tiers=missing,
    )


# ---------------------------------------------------------------------------
# Affichage / démonstration
# ---------------------------------------------------------------------------

def format_probability_report(fmt: KenoFormat, picked: int) -> str:
    """Rapport lisible des probabilités exactes pour une grille de `picked` numéros."""
    lines = []
    lines.append(f"=== Probabilités exactes — {fmt.label} ===")
    lines.append(f"Grille jouée : {picked} numéros | Tirage : {fmt.numbers_drawn} "
                 f"boules sur {fmt.total_numbers}")
    lines.append("")
    lines.append(f"{'Bons n°':>8} | {'Probabilité':>16} | {'1 chance sur':>18}")
    lines.append("-" * 50)
    for k, prob in probability_table(fmt, picked):
        one_in = odds_one_in(prob)
        one_in_str = f"{one_in:,.1f}".replace(",", " ") if one_in else "—"
        lines.append(f"{k:>8} | {float(prob):>16.10f} | {one_in_str:>18}")
    total = sum((p for _, p in probability_table(fmt, picked)), Fraction(0))
    lines.append("-" * 50)
    lines.append(f"Somme des probabilités = {float(total):.10f} (doit valoir 1.0)")
    return "\n".join(lines)


def _demo() -> None:
    fmt = KENO_FDJ_2025
    print(__doc__.split("---")[0].strip())
    print()
    for picked in (5, 7, 10):
        print(format_probability_report(fmt, picked))
        ev = expected_value(fmt, picked, stake=1.0)
        if ev.complete:
            print(f"\nTaux de retour (mise 1 €) : {ev.return_rate * 100:.1f} %")
        else:
            print(f"\nEspérance non calculable : barème incomplet pour {picked} "
                  f"numéros joués (paliers manquants : {ev.missing_tiers}).")
            print("→ Complétez PAYOUTS_1EUR depuis la grille officielle FDJ.")
        print("\n" + "=" * 60 + "\n")

    print("RAPPEL : le Keno est un jeu de pur hasard. Ces probabilités décrivent")
    print("vos chances réelles ; elles ne permettent PAS de prédire un tirage.")


if __name__ == "__main__":
    _demo()
