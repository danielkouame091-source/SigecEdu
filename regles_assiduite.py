"""regles_assiduite.py - Règles PURES de l'assiduité et des QR Codes (aucune base de données, aucune
bibliothèque tierce) : testables seules avec `python check_assiduite.py`.

  * taux = présences / séances comptées x 100, arrondi à 2 décimales, demi supérieur ;
  * bloque = (taux < seuil), STRICTEMENT inférieur : 85.00 % pile n'est pas bloqué, 84.99 % l'est ;
  * hash = HMAC-SHA256 d'un message canonique ; ce message DOIT rester identique, caractère pour
    caractère, à la concaténation du trigger SQL `convocation_calculer()`.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

PREFIXE_QR = "CIEDU1"          # format du QR : CIEDU1:<uuid de la convocation>:<hash hex 64>
DEUX_DECIMALES = Decimal("0.01")
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class ErreurAssiduite(ValueError):
    pass


class IncoherenceConvocation(RuntimeError):
    """La convocation stockée ne correspond pas à l'algorithme : incident de sécurité à investiguer."""


def calculer_taux(presences: int, seances_comptees: int) -> Decimal:
    """Sans séance comptée, l'élève n'a aucune absence à son passif : 100 %."""
    if seances_comptees < 0 or presences < 0 or presences > seances_comptees:
        raise ErreurAssiduite("Compteurs d'assiduité incohérents")
    if seances_comptees == 0:
        return Decimal("100.00")
    return (Decimal(100) * presences / seances_comptees).quantize(DEUX_DECIMALES, rounding=ROUND_HALF_UP)


def est_bloque(taux: Decimal, seuil: Decimal) -> bool:
    """Règle unique du blocage : strictement sous le seuil. Aucune exception, aucune dérogation."""
    return taux < seuil


@dataclass(frozen=True)
class ResultatAssiduite:
    seances_comptees: int
    presences: int
    taux: Decimal
    seuil: Decimal

    @property
    def bloque(self) -> bool:
        return est_bloque(self.taux, self.seuil)


def message_hash(conv_id, roll_number: str, session_id, taux: Decimal, bloque: bool, genere_le: datetime) -> str:
    """Message canonique signé. Miroir exact du trigger SQL : id | roll | session | taux | bloque | horodatage UTC."""
    horodatage = genere_le.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")
    return "|".join([
        str(conv_id), roll_number, str(session_id),
        f"{Decimal(taux).quantize(DEUX_DECIMALES):.2f}",
        "true" if bloque else "false",
        horodatage,
    ])


def calculer_hash_qr(secret: str, conv_id, roll_number, session_id, taux, bloque, genere_le) -> str:
    message = message_hash(conv_id, roll_number, session_id, taux, bloque, genere_le)
    return hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


def hash_identiques(a: str, b: str) -> bool:
    """Comparaison en temps constant."""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def payload_depuis(conv_id, hash_hex: str) -> str:
    return f"{PREFIXE_QR}:{conv_id}:{hash_hex}"


def analyser_payload(payload: str) -> tuple[uuid.UUID, str] | None:
    """Décompose un QR. Retourne None pour tout format invalide (jamais d'exception : entrée non fiable)."""
    parties = payload.strip().split(":")
    if len(parties) != 3 or parties[0] != PREFIXE_QR:
        return None
    try:
        conv_id = uuid.UUID(parties[1])
    except ValueError:
        return None
    hash_hex = parties[2].lower()
    return (conv_id, hash_hex) if _HASH_RE.match(hash_hex) else None
