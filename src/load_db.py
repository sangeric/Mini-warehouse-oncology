import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text

DB_URL = os.environ.get(
    "DB_URL",
    "postgresql+psycopg2://app:app@localhost:5432/entrepot",
)

RAW_A = "data/raw/source_hopital_A.csv"
RAW_B = "data/raw/source_hopital_B.csv"
CLEAN_PATIENTS = "data/processed/patients_clean.csv"
CLEAN_TRAITEMENTS = "data/processed/traitements_clean.csv"


def main():
    engine = create_engine(DB_URL)

    # ===== COUCHE STAGING : sources brutes telles quelles (rien n'est perdu) =====
    # Les colonnes nom/prenom/deuxieme_prenom (et middle_name côté B) sont
    # copiées à l'identique : la source est intégralement conservée.
    raw_a = pd.read_csv(RAW_A)
    raw_b = pd.read_csv(RAW_B)
    raw_a.to_sql("staging_hopital_a", engine, if_exists="replace", index=False)
    raw_b.to_sql("staging_hopital_b", engine, if_exists="replace", index=False)

    # ===== COUCHE PROPRE : dimension + faits =====
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS Traitement"))
        conn.execute(text("DROP TABLE IF EXISTS Patient"))
        conn.execute(text("""
            CREATE TABLE Patient (
                patient_uid     INTEGER PRIMARY KEY,
                nom_norm        TEXT,
                prenom_norm     TEXT,
                deuxieme_prenom TEXT,          -- conservé, souvent NULL (légitime)
                date_naissance  DATE,
                sexe            TEXT,
                age             INTEGER,
                est_complet     BOOLEAN
            )"""))
        conn.execute(text("""
            CREATE TABLE Traitement (
                id_traitement   INTEGER PRIMARY KEY,
                patient_uid     INTEGER NOT NULL REFERENCES Patient(patient_uid),
                date_traitement DATE,
                type_traitement TEXT,
                stade           TEXT
            )"""))

    patients = pd.read_csv(CLEAN_PATIENTS)
    traitements = pd.read_csv(CLEAN_TRAITEMENTS)

    patients_sql = patients[["patient_uid", "nom_norm", "prenom_norm", "deuxieme_prenom",
                             "date_naissance", "sexe", "age", "est_complet"]]
    traitements_sql = traitements[["id_traitement", "patient_uid",
                                   "date_traitement", "type_traitement", "stade"]]

    patients_sql.to_sql("patient", engine, if_exists="append", index=False)
    traitements_sql.to_sql("traitement", engine, if_exists="append", index=False)

    # ===== VERIFICATION =====
    with engine.connect() as conn:
        print("=== Comptages par table ===")
        for tbl in ["staging_hopital_a", "staging_hopital_b", "patient", "traitement"]:
            n = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            print(f"  {tbl:20s}: {n}")
        na = conn.execute(text("SELECT COUNT(*) FROM staging_hopital_a")).scalar()
        nb = conn.execute(text("SELECT COUNT(*) FROM staging_hopital_b")).scalar()
        print(f"\n  Total lignes sources en base : {na + nb}")
        print("\n=== Complétude patients ===")
        print(pd.read_sql("SELECT est_complet, COUNT(*) AS n FROM patient GROUP BY est_complet ORDER BY est_complet", conn).to_string(index=False))
        print("\n=== Exemple : un patient fusionné avec 2e prénom ===")
        print(pd.read_sql("SELECT patient_uid, nom_norm, prenom_norm, deuxieme_prenom, date_naissance, sexe, age FROM patient WHERE deuxieme_prenom IS NOT NULL ORDER BY patient_uid LIMIT 5", conn).to_string(index=False))

    try:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO Traitement (id_traitement, patient_uid) VALUES (99999, 123456)"))
        print("\nFK NON appliquee (probleme)")
        sys.exit(1)
    except Exception as e:
        print("\nFK appliquee : insertion orpheline refusee ->", type(e).__name__)


if __name__ == "__main__":
    main()
