#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests de validation du moteur de probabilités (keno_probabilities.py).

Objectif : PROUVER que les probabilités calculées sont exactes. Chaque test
s'appuie sur une propriété mathématique vérifiable (somme = 1, valeurs
calculées à la main, symétrie de la loi hypergéométrique).

Exécution sans dépendance :  python3 test_keno_probabilities.py
Ou avec pytest        :      pytest test_keno_probabilities.py
"""

from fractions import Fraction
from math import comb, isclose

from keno_probabilities import (
    KENO_FDJ_2025,
    KENO_FDJ_LEGACY,
    at_least_probability,
    hypergeometric,
    match_probability,
    probability_table,
)


def test_hypergeometric_valeur_calculee_a_la_main():
    # Population de 4, 2 succès, on tire 2 : P(exactement 1 succès) = C(2,1)C(2,1)/C(4,2) = 4/6 = 2/3
    assert hypergeometric(4, 2, 2, 1) == Fraction(2, 3)
    assert hypergeometric(4, 2, 2, 2) == Fraction(1, 6)
    assert hypergeometric(4, 2, 2, 0) == Fraction(1, 6)
    # La somme sur tous les cas possibles vaut 1
    assert hypergeometric(4, 2, 2, 0) + hypergeometric(4, 2, 2, 1) + hypergeometric(4, 2, 2, 2) == 1


def test_hypergeometric_cas_impossibles_nuls():
    # Plus de succès que de tirages, ou que de succès disponibles -> probabilité nulle
    assert hypergeometric(56, 16, 10, 11) == Fraction(0)
    assert hypergeometric(56, 16, 10, -1) == Fraction(0)


def test_somme_des_probabilites_vaut_1_nouveau_format():
    for picked in range(KENO_FDJ_2025.min_pick, KENO_FDJ_2025.max_pick + 1):
        total = sum((p for _, p in probability_table(KENO_FDJ_2025, picked)), Fraction(0))
        assert total == Fraction(1), f"Somme != 1 pour {picked} numéros joués (56/16)"


def test_somme_des_probabilites_vaut_1_ancien_format():
    for picked in range(KENO_FDJ_LEGACY.min_pick, KENO_FDJ_LEGACY.max_pick + 1):
        total = sum((p for _, p in probability_table(KENO_FDJ_LEGACY, picked)), Fraction(0))
        assert total == Fraction(1), f"Somme != 1 pour {picked} numéros joués (70/20)"


def test_match_probability_est_exacte():
    # 4 bons sur 4 joués, format 56/16 : C(16,4)*C(40,0)/C(56,4)
    attendu = Fraction(comb(16, 4) * comb(40, 0), comb(56, 4))
    assert match_probability(KENO_FDJ_2025, 4, 4) == attendu


def test_symetrie_hypergeometrique():
    # P(k | on considère les picks comme marqués) == P(k | on considère le tirage comme marqué)
    for k in range(0, 8):
        a = hypergeometric(56, 7, 16, k)   # 7 picks marqués, 16 tirés
        b = hypergeometric(56, 16, 7, k)   # 16 tirés marqués, 7 picks
        assert a == b


def test_at_least_coherent_avec_table():
    picked = 7
    table = dict(probability_table(KENO_FDJ_2025, picked))
    attendu = sum((p for k, p in table.items() if k >= 5), Fraction(0))
    assert at_least_probability(KENO_FDJ_2025, picked, 5) == attendu


def test_esperance_de_bons_numeros():
    # L'espérance du nombre de bons numéros doit valoir picked * (drawn / total).
    # C'est une propriété de la loi hypergéométrique, et elle illustre que CHAQUE
    # numéro a la même probabilité drawn/total de sortir, indépendamment de l'historique.
    fmt = KENO_FDJ_2025
    for picked in (4, 7, 10):
        esperance = sum(float(p) * k for k, p in probability_table(fmt, picked))
        attendu = picked * fmt.numbers_drawn / fmt.total_numbers
        assert isclose(esperance, attendu, rel_tol=1e-12), (
            f"E[bons]={esperance} != {attendu} pour {picked} joués")


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"[OK]   {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"[FAIL] {t.__name__} : {e}")
    print("-" * 50)
    print(f"{len(tests) - failures}/{len(tests)} tests réussis.")
    return failures


if __name__ == "__main__":
    import sys
    sys.exit(1 if _run_all() else 0)
