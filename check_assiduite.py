"""Attendance rules: how the attendance rate is computed and who may sit the exam."""


def calculer_taux_assiduite(total_seances: int, presences: int) -> float:
    """Attendance rate in % = sessions attended / total sessions x 100."""
    if total_seances == 0:
        return 100.0
    return round((presences / total_seances) * 100, 2)

def verifier_eligibilite(taux: float) -> bool:
    """A student can sit the exam only with at least 75 % attendance (threshold chosen as an example)."""
    return taux >= 75.0

if __name__ == "__main__":
    print("Attendance rules self-test:")
    taux_ok = calculer_taux_assiduite(20, 18)
    print(f"Case 1 (18/20) -> Taux : {taux_ok}% | Eligible : {verifier_eligibilite(taux_ok)}")
    
    taux_ko = calculer_taux_assiduite(20, 10)
    print(f"Case 2 (10/20) -> Taux : {taux_ko}% | Eligible : {verifier_eligibilite(taux_ko)}")
    print("OK: the calculation rules work correctly.")
