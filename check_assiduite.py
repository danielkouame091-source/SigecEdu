"""check_assiduite.py - Test automatique des règles pures (seuil 85 %, arrondi, hash, QR).
Aucune base de données, aucune bibliothèque tierce. Lancement :  python check_assiduite.py
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import regles_assiduite as r

D = Decimal
SEUIL = D("85.00")


def attend_erreur(exc, fonction, *args):
    try:
        fonction(*args)
    except exc:
        return
    raise AssertionError(f"{exc.__name__} attendue pour {args}")


# --- Taux : arrondi demi supérieur, cas limites --------------------------------------------------
assert r.calculer_taux(17, 20) == D("85.00")
assert r.calculer_taux(16, 20) == D("80.00")
assert r.calculer_taux(20, 20) == D("100.00")
assert r.calculer_taux(0, 0) == D("100.00")             # aucune séance comptée : pas d'absence au passif
assert r.calculer_taux(0, 10) == D("0.00")
assert r.calculer_taux(1, 3) == D("33.33") and r.calculer_taux(2, 3) == D("66.67")
assert r.calculer_taux(201, 800) == D("25.13")          # 25.125 -> 25.13 (demi supérieur, pas l'arrondi bancaire)
assert r.calculer_taux(8499, 10000) == D("84.99")
attend_erreur(r.ErreurAssiduite, r.calculer_taux, 5, 4)
attend_erreur(r.ErreurAssiduite, r.calculer_taux, -1, 4)
attend_erreur(r.ErreurAssiduite, r.calculer_taux, 1, -4)

# --- Blocage : STRICTEMENT sous le seuil -----------------------------------------------------------
assert r.est_bloque(D("84.99"), SEUIL) is True
assert r.est_bloque(D("85.00"), SEUIL) is False         # pile 85 % : convoqué
assert r.est_bloque(D("85.01"), SEUIL) is False
assert r.est_bloque(D("0.00"), SEUIL) is True
assert r.est_bloque(D("100.00"), SEUIL) is False
assert r.est_bloque(D("80.00"), D("80.00")) is False    # le seuil est un paramètre, pas une constante
res = r.ResultatAssiduite(seances_comptees=20, presences=16, taux=r.calculer_taux(16, 20), seuil=SEUIL)
assert res.bloque is True
assert r.ResultatAssiduite(20, 17, r.calculer_taux(17, 20), SEUIL).bloque is False

# --- Message canonique (doit rester identique au trigger SQL) -------------------------------------
CONV = uuid.UUID("11111111-1111-1111-1111-111111111111")
SESS = uuid.UUID("22222222-2222-2222-2222-222222222222")
ROLL = "CI-26-00000001-01"
QUAND = datetime(2026, 10, 1, 8, 30, 15, 123456, tzinfo=timezone.utc)
SECRET = "0123456789abcdef0123456789abcdef"

assert r.message_hash(CONV, ROLL, SESS, D("85"), False, QUAND) == (
    "11111111-1111-1111-1111-111111111111|CI-26-00000001-01|22222222-2222-2222-2222-222222222222"
    "|85.00|false|2026-10-01T08:30:15.123456")
assert r.message_hash(CONV, ROLL, SESS, D("80.5"), True, QUAND).endswith("|80.50|true|2026-10-01T08:30:15.123456")
# L'heure locale est ramenée en UTC ; microsecondes toujours sur 6 chiffres
abidjan_plus2 = QUAND.astimezone(timezone(timedelta(hours=2)))
assert r.message_hash(CONV, ROLL, SESS, D("85"), False, abidjan_plus2) == r.message_hash(CONV, ROLL, SESS, D("85"), False, QUAND)
assert r.message_hash(CONV, ROLL, SESS, D("85"), False, QUAND.replace(microsecond=5)).endswith(".000005")

# --- HMAC : vecteur de référence (toute modification du format le casse volontairement) ---------------
VECTEUR = "56de8b12dd37a2129453eb8fbfb1a6069a35684de20d5717c7f1c3d1ce44247c"
h = r.calculer_hash_qr(SECRET, CONV, ROLL, SESS, D("85.00"), False, QUAND)
assert h == VECTEUR, f"Le format du hash a changé : {h}"
assert r.calculer_hash_qr(SECRET, CONV, ROLL, SESS, D("85.00"), False, QUAND) == h               # déterministe
variantes = [
    r.calculer_hash_qr(SECRET + "x", CONV, ROLL, SESS, D("85.00"), False, QUAND),                # autre clé
    r.calculer_hash_qr(SECRET, uuid.uuid4(), ROLL, SESS, D("85.00"), False, QUAND),              # autre convocation
    r.calculer_hash_qr(SECRET, CONV, "CI-26-00000002-02", SESS, D("85.00"), False, QUAND),       # autre élève
    r.calculer_hash_qr(SECRET, CONV, ROLL, uuid.uuid4(), D("85.00"), False, QUAND),              # autre session
    r.calculer_hash_qr(SECRET, CONV, ROLL, SESS, D("85.01"), False, QUAND),                      # autre taux
    r.calculer_hash_qr(SECRET, CONV, ROLL, SESS, D("85.00"), True, QUAND),                       # blocage inversé
    r.calculer_hash_qr(SECRET, CONV, ROLL, SESS, D("85.00"), False, QUAND + timedelta(microseconds=1)),
]
assert len({h, *variantes}) == 8, "chaque champ doit modifier le hash"
assert len(h) == 64 and r.hash_identiques(h, h) and not r.hash_identiques(h, variantes[0])

# --- Contenu du QR ---------------------------------------------------------------------------------------
payload = r.payload_depuis(CONV, h)
assert payload == f"CIEDU1:{CONV}:{h}"
assert r.analyser_payload(payload) == (CONV, h)
assert r.analyser_payload("  " + payload + "\n") == (CONV, h)                      # espaces tolérés
assert r.analyser_payload(f"CIEDU1:{CONV}:{h.upper()}") == (CONV, h)             # hash normalisé en minuscules
for faux in ("", "CIEDU1", f"CIEDU2:{CONV}:{h}", f"CIEDU1:pas-un-uuid:{h}", f"CIEDU1:{CONV}:{h[:-1]}",
             f"CIEDU1:{CONV}:{h}:extra", f"CIEDU1:{CONV}:{'z' * 64}", f"{CONV}:{h}"):
    assert r.analyser_payload(faux) is None, f"payload accepté à tort : {faux!r}"

print("OK : règles d'assiduité validées (seuil strict à 85 %, arrondi, hash HMAC, format du QR).")
