-- =====================================================================
-- schema_salaires.sql - Addendum à schema_maitre.sql (à exécuter ensuite)
-- Impact salarial des cours non dispensés, avec contestation encadrée.
-- Une retenue n'est JAMAIS appliquée immédiatement : fenêtre de contestation
-- (delai_contestation_j), puis validation automatique si personne ne conteste.
-- =====================================================================
BEGIN;

ALTER TABLE professeurs
  ADD COLUMN taux_horaire_fcfa NUMERIC(12,2)
  CHECK (taux_horaire_fcfa IS NULL OR taux_horaire_fcfa >= 0);

INSERT INTO parametres_systeme (cle, valeur, description) VALUES
  ('delai_contestation_j', 5, 'Jours laissés au professeur pour contester une retenue avant validation automatique');

CREATE TYPE statut_retenue AS ENUM ('EN_CONTESTATION','CONTESTEE','VALIDEE','ANNULEE');

CREATE TABLE retenues_salaire (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  professeur_id      UUID NOT NULL REFERENCES professeurs(id),
  seance_id          UUID NOT NULL UNIQUE REFERENCES seances_cours(id),   -- une seule retenue par séance
  duree_minutes      INT  NOT NULL CHECK (duree_minutes > 0),
  taux_horaire_fcfa  NUMERIC(12,2) NOT NULL CHECK (taux_horaire_fcfa >= 0),
  montant_fcfa       NUMERIC(12,2) NOT NULL CHECK (montant_fcfa >= 0),
  secteur            secteur_etablissement NOT NULL,                      -- public : Etat / privé : employeur
  statut             statut_retenue NOT NULL DEFAULT 'EN_CONTESTATION',
  cree_le            TIMESTAMPTZ NOT NULL DEFAULT now(),
  contestable_jusqua TIMESTAMPTZ NOT NULL,
  motif_contestation TEXT,
  motif_decision     TEXT,
  decide_par         UUID REFERENCES utilisateurs(id),
  decide_le          TIMESTAMPTZ
);
CREATE INDEX idx_retenue_prof   ON retenues_salaire(professeur_id, statut);
CREATE INDEX idx_retenue_statut ON retenues_salaire(statut, contestable_jusqua);

-- VALIDEE et ANNULEE sont définitives ; jamais de suppression
CREATE OR REPLACE FUNCTION retenue_verrou() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'Une retenue ne peut pas être supprimée';
  END IF;
  IF OLD.statut IN ('VALIDEE','ANNULEE') THEN
    RAISE EXCEPTION 'Retenue finalisée (%) : modification interdite', OLD.statut;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER t_retenue_verrou BEFORE UPDATE OR DELETE ON retenues_salaire
  FOR EACH ROW EXECUTE FUNCTION retenue_verrou();
CREATE TRIGGER t_audit_retenue AFTER INSERT OR UPDATE OR DELETE ON retenues_salaire
  FOR EACH ROW EXECUTE FUNCTION audit_generique();

COMMIT;
