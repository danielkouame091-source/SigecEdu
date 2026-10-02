import enum

class StatutPresence(str, enum.Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"

class StatutAssiduite(str, enum.Enum):
    REGULIER = "REGULIER"
    A_RISQUE = "A_RISQUE"
    INSUFFISANT = "INSUFFISANT"

class StatutSeance(str, enum.Enum):
    DISPENSE = "DISPENSE"
    REMPLACE = "REMPLACE"
    ANNULE = "ANNULE"
