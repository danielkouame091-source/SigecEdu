"""Fixed lists of values (enumerations) shared by the whole project.

Vocabulary (the code keeps the French domain words, here is what they mean):
  eleve       = student        enseignant = teacher        seance = class session
  assiduite   = attendance     matricule  = student ID     numero_te = teacher ID
"""
import enum


class StatutPresence(str, enum.Enum):
    """Was the student in the class session or not?"""
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"


class StatutAssiduite(str, enum.Enum):
    """Overall attendance level of a student (stored as the NAME, e.g. REGULIER;
    the API shows and accepts the VALUE, e.g. "Regular")."""
    REGULIER = "Regular"        # attends normally
    IRREGULIER = "Irregular"    # misses too many sessions
    ABSENT = "Absent"           # almost never present
    EXCLU = "Excluded"          # below the minimum rate: cannot sit the exam


class StatutSeance(str, enum.Enum):
    """What happened to a class session."""
    DISPENSE = "DISPENSE"   # held normally
    REMPLACE = "REMPLACE"   # held by a replacement teacher
    ANNULE = "ANNULE"       # cancelled
