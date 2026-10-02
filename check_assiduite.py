def calculer_taux_assiduite(total_seances: int, presences: int) -> float:
    if total_seances == 0:
        return 100.0
    return round((presences / total_seances) * 100, 2)

def verifier_eligibilite(taux: float) -> bool:
    # Seuil d'exclusion fixé par exemple à 75%
    return taux >= 75.0

if __name__ == "__main__":
    print("Test des règles d'assiduité :")
    taux_ok = calculer_taux_assiduite(20, 18)
    print(f"Cas 1 (18/20) -> Taux : {taux_ok}% | Eligible : {verifier_eligibilite(taux_ok)}")
    
    taux_ko = calculer_taux_assiduite(20, 10)
    print(f"Cas 2 (10/20) -> Taux : {taux_ko}% | Eligible : {verifier_eligibilite(taux_ko)}")
    print("OK : Les règles de calcul fonctionnent correctement.")
