from pathlib import Path

import pandas as pd
import unicodedata
import numpy as np


COMMON_COLS = [
    "id_source",        # 'A' ou 'B' -> traçabilité (data lineage)
    "id_patient_src",   # identifiant tel qu'il existe dans la source
    "nom_norm",         # nom normalisé, clé de rapprochement
    "date_naissance",   # datetime
    "sexe",             # 'M' / 'F' / NA
    "date_traitement",  # datetime
    "type_traitement",  # texte
    "compte_rendu",     # texte libre (exploité à l'étape 3)
]

SOURCE_A = Path("data/raw/source_hopital_A.csv")
SOURCE_B = Path("data/raw/source_hopital_B.csv")


def inspect_dataframe(df: pd.DataFrame, source_name: str) -> None:
    print(f"\n{'=' * 50}")
    print(f"{source_name}")
    print(f"{'=' * 50}")

    print("\nAperçu :")
    print(df.head())

    print(f"\nDimensions : {df.shape[0]} lignes × {df.shape[1]} colonnes")

    print("\nColonnes :")
    for column in df.columns:
        print(f"  - {column}")


def load_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    return pd.read_csv(path)

def normalize_name(raw: str) -> str:
    if pd.isna(raw):
        return ""
    # é -> e : on décompose puis on jette les accents
    txt = unicodedata.normalize("NFKD", str(raw))
    txt = txt.encode("ascii", "ignore").decode("ascii")
    tokens = txt.strip().lower().split()
    return " ".join(sorted(tokens))

def prepare_a(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    out["id_source"] = np.repeat("A", len(df))
    out["id_patient_src"] = df["id_patient"]
    out["nom_norm"] = df["nom_pat"].apply(normalize_name)
    out["date_naissance"] = pd.to_datetime(df["date_naissance"], dayfirst=True, errors="coerce")
    out["sexe"] = df["sexe"].str.upper().str.strip().replace({"": pd.NA})
    out["date_traitement"] = pd.to_datetime(df["date_traitement"], dayfirst=True, errors="coerce")
    out["type_traitement"] = df["type_traitement"].str.strip().str.lower()
    out["compte_rendu"] = df["compte_rendu"]
    return out[COMMON_COLS]


def prepare_b(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    out["id_source"] = np.repeat("B", len(df))
    out["id_patient_src"] = df["patient_id"]
    out["nom_norm"] = df["patient_name"].apply(normalize_name)
    out["date_naissance"] = pd.to_datetime(df["birth_date"], errors="coerce")
    out["sexe"] = df["sexe_code"].astype("string").map({"1": "M", "2": "F"})
    out["date_traitement"] = pd.to_datetime(df["treatment_date"], errors="coerce")
    out["type_traitement"] = df["treatment_type"].str.strip().str.lower()
    out["compte_rendu"] = df["report"]
    return out[COMMON_COLS]

def assign_patient_uid(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    dob_key = df["date_naissance"].dt.strftime("%Y-%m-%d")
    key_complete = df["nom_norm"].ne("") & dob_key.notna()

    match_key = df["nom_norm"] + "|" + dob_key
    match_key = match_key.where(key_complete, other="ORPHAN_" + df.index.astype(str))

    df["patient_uid"] = match_key.groupby(match_key).ngroup()
    return df

def build_patient_table(df: pd.DataFrame) -> pd.DataFrame:
    def first_non_null(s):
        s = s.dropna()
        return s.iloc[0] if len(s) else pd.NA

    def sexe_conflict(s):
        return s.dropna().nunique() > 1   # 2 sexes différents = incohérence

    patients = (
        df.groupby("patient_uid")
        .agg(
            nom_norm=("nom_norm", "first"),
            date_naissance=("date_naissance", first_non_null),
            sexe=("sexe", first_non_null),
            sexe_conflit=("sexe", sexe_conflict),
            ids_sources=("id_patient_src", lambda s: ",".join(sorted(set(s.astype(str))))),
            nb_sources=("id_source", lambda s: s.nunique()),
        )
        .reset_index()
    )
    naissance = pd.to_datetime(patients["date_naissance"], errors="coerce")
    today = np.datetime64("today", "D")
    jours = (today - naissance.values.astype("datetime64[D]")) / np.timedelta64(1, "D")
    patients["date_naissance"] = naissance
    patients["age"] = np.floor(jours / 365.25)
    return patients

def quality_report(traitements, patients):
    print("\nPatients fusionnés (2 sources) :", (patients["nb_sources"] > 1).sum())
    print("Conflits de sexe               :", patients["sexe_conflit"].sum())

    m = traitements.merge(patients[["patient_uid", "date_naissance"]], on="patient_uid", how="left")
    mauvaises = m[m["date_traitement"] < m["date_naissance"]]
    if not mauvaises.empty:
        print("\n===== DÉTAIL TRAITEMENTS AVANT NAISSANCE =====")
        print(mauvaises[["id_source", "id_patient_src", "date_traitement", "date_naissance"]])

    print("Traitement avant naissance     :", (m["date_traitement"] < m["date_naissance"]).sum())
    print("Traitement dans le futur       :", (traitements["date_traitement"] > pd.Timestamp("today")).sum())
    print("Dates illisibles (NaT)         :", traitements["date_traitement"].isna().sum())
    print("Comptes-rendus vides           :", traitements["compte_rendu"].fillna("").eq("").sum())

def main() -> None:
    df_a = load_data(SOURCE_A)
    df_b = load_data(SOURCE_B)

    inspect_dataframe(df_a, "HÔPITAL A")
    inspect_dataframe(df_b, "HÔPITAL B")
    print(df_a.dtypes)
    print(df_b.dtypes)
    print("\n===== VALEURS MANQUANTES A =====")
    print(df_a.isna().sum(), "\n")

    print("\n===== VALEURS MANQUANTES B =====")
    print(df_b.isna().sum(), "\n")

    missing_rate_a = df_a.isna().mean() * 100
    print("\n", missing_rate_a)

    missing_rate_b = df_b.isna().mean() * 100
    print("\n", missing_rate_b)

    print("\n===== DOUBLONS A =====")
    print(df_a.duplicated().sum())

    print("\n===== DOUBLONS B =====")
    print(df_b.duplicated().sum())

    # Count the occurrences of each value in the columns
    # to check the categories and identify unexpected values or missing data.
    print("\n===== SEXE A =====")
    print(df_a["sexe"].value_counts(dropna=False))

    print("\n===== SEXE B =====")
    print(df_b["sexe_code"].value_counts(dropna=False))

    print("\n===== TRAITEMENTS A =====")
    print(df_a["type_traitement"].value_counts(dropna=False))

    print("\n===== TRAITEMENTS B =====")
    print(df_b["treatment_type"].value_counts(dropna=False))

    df_all = pd.concat([prepare_a(df_a), prepare_b(df_b)], ignore_index=True)
    df_all = assign_patient_uid(df_all)

    patients = build_patient_table(df_all)
    traitements = df_all[[
        "patient_uid", "id_source", "id_patient_src",
        "date_traitement", "type_traitement", "compte_rendu",
    ]].copy()
    traitements.insert(0, "id_traitement", range(1, len(traitements) + 1))
        
    quality_report(traitements, patients)

    Path("data/processed").mkdir(parents=True, exist_ok=True)
    patients.to_csv("data/processed/patients_clean.csv", index=False)
    traitements.to_csv("data/processed/traitements_clean.csv", index=False)

if __name__ == "__main__":
    main()