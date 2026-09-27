from pathlib import Path
import re
import pandas as pd
import unicodedata
import numpy as np


COMMON_COLS = [
    "id_source",        # 'A' ou 'B' -> traçabilité (data lineage)
    "id_patient_src",   # identifiant tel qu'il existe dans la source
    "nom_norm",         # nom normalisé, clé de rapprochement
    "prenom_norm",
    "deuxieme_prenom",
    "date_naissance",   # datetime
    "sexe",             # 'M' / 'F' / NA
    "date_traitement",  # datetime
    "type_traitement",  # texte
    "compte_rendu",     # texte libre (exploité à l'étape 3)
]

SOURCE_A = Path("data/raw/source_hopital_A.csv")
SOURCE_B = Path("data/raw/source_hopital_B.csv")

STADE_RE = re.compile(r"stade\s*(IV|III|II|I)\b", re.IGNORECASE)


def load_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    return pd.read_csv(path)


def inspect_dataframe(df: pd.DataFrame, source_name: str, categorical_cols: list[str] | None = None) -> None:
    """Inspection exploratoire d'une source brute avant nettoyage :
    aperçu, dimensions, types, valeurs manquantes, doublons, et
    distribution des colonnes catégorielles passées en paramètre
    (leurs noms diffèrent selon la source, donc on ne les code pas en dur ici)."""
    print(f"\n{'=' * 100}")
    print(f"                                           {source_name}")
    print(f"{'=' * 100}")

    print("\nAperçu :")
    print(df.head())

    print(f"\nDimensions : {df.shape[0]} lignes × {df.shape[1]} colonnes")

    print("\nColonnes :")
    for column in df.columns:
        print(f"  - {column}")

    print("\nTypes :")
    print(df.dtypes)

    print("\n===== VALEURS MANQUANTES =====")
    print(df.isna().sum())

    print("\nTaux de valeurs manquantes (%) :")
    print(df.isna().mean() * 100)

    print("\n===== DOUBLONS =====")
    print(df.duplicated().sum())

    if categorical_cols:
        for col in categorical_cols:
            print(f"\n===== {col.upper()} =====")
            print(df[col].value_counts(dropna=False))

def normalize_name(raw: str) -> str:
    if pd.isna(raw):
        return ""
    txt = unicodedata.normalize("NFKD", str(raw)).encode("ascii", "ignore").decode("ascii")
    return " ".join(txt.strip().lower().split())


def clean_optional(raw):
    """Deuxième prénom : nettoyé léger, vide -> NA (on garde l'info si elle existe)."""
    if pd.isna(raw):
        return pd.NA
    v = str(raw).strip()
    return v.title() if v else pd.NA

def prepare_a(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    out["id_source"] = np.repeat("A", len(df))
    out["id_patient_src"] = df["id_patient"]
    out["nom_norm"] = df["nom"].apply(normalize_name)
    out["prenom_norm"] = df["prenom"].apply(normalize_name)
    out["deuxieme_prenom"] = df["deuxieme_prenom"].apply(clean_optional)
    out["date_naissance"] = pd.to_datetime(df["date_naissance"], dayfirst=True, format="mixed", errors="coerce")
    out["sexe"] = df["sexe"].str.upper().str.strip().replace({"": pd.NA})
    out["date_traitement"] = pd.to_datetime(df["date_traitement"], dayfirst=True, format="mixed", errors="coerce")
    out["type_traitement"] = df["type_traitement"].str.strip().str.lower()
    out["compte_rendu"] = df["compte_rendu"]
    return out[COMMON_COLS]


def prepare_b(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    out["id_source"] = np.repeat("B", len(df))
    out["id_patient_src"] = df["patient_id"]
    out["nom_norm"] = df["last_name"].apply(normalize_name)
    out["prenom_norm"] = df["first_name"].apply(normalize_name)
    out["deuxieme_prenom"] = df["middle_name"].apply(clean_optional)
    out["date_naissance"] = pd.to_datetime(df["birth_date"], format="ISO8601", errors="coerce")
    out["sexe"] = df["sexe_code"].astype("string").map({"1": "M", "2": "F"})
    out["date_traitement"] = pd.to_datetime(df["treatment_date"], format="ISO8601", errors="coerce")
    out["type_traitement"] = df["treatment_type"].str.strip().str.lower()
    out["compte_rendu"] = df["report"]
    return out[COMMON_COLS]

def assign_patient_uid(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    dob_key = df["date_naissance"].dt.strftime("%Y-%m-%d")
    key_complete = df["nom_norm"].ne("") & df["prenom_norm"].ne("") & dob_key.notna()
    match_key = df["nom_norm"] + "|" + df["prenom_norm"] + "|" + dob_key
    match_key = match_key.where(key_complete, other="ORPHAN_" + df.index.astype(str))

    df["patient_uid"] = match_key.groupby(match_key).ngroup()
    return df

def build_patient_table(df: pd.DataFrame) -> pd.DataFrame:
    def first_non_null(s):
        s = s.dropna()
        return s.iloc[0] if len(s) else pd.NA

    def sexe_conflict(s):
        return s.dropna().nunique() > 1 

    patients = (
        df.groupby("patient_uid")
        .agg(
            nom_norm=("nom_norm", "first"),
            prenom_norm=("prenom_norm", "first"),
            deuxieme_prenom=("deuxieme_prenom", first_non_null), 
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
    patients["est_complet"] = (
        patients["nom_norm"].ne("") & patients["prenom_norm"].ne("") & patients["date_naissance"].notna()
    )
    return patients

def quality_report(traitements, patients):
    print("Patients                       :", len(patients))
    print("  dont complets                :", patients["est_complet"].sum())
    print("Patients fusionnés (2 sources) :", (patients["nb_sources"] > 1).sum())
    print("Conflits de sexe               :", patients["sexe_conflit"].sum())
    print("Deuxième prénom renseigné      :", patients["deuxieme_prenom"].notna().sum())
    m = traitements.merge(patients[["patient_uid", "date_naissance"]], on="patient_uid", how="left")
    print("Traitement avant naissance     :", (m["date_traitement"] < m["date_naissance"]).sum())
    print("Traitement dans le futur       :", (traitements["date_traitement"] > pd.Timestamp("today")).sum())
    ext = traitements["stade"].notna().sum()
    print(f"Stade extrait                  : {ext}/{len(traitements)}")





def extract_stade(text: str):
    if pd.isna(text):
        return pd.NA
    match = STADE_RE.search(str(text))
    return match.group(1).upper() if match else pd.NA


def main() -> None:
    df_a = load_data(SOURCE_A)
    df_b = load_data(SOURCE_B)
    
    inspect_dataframe(df_a, "HÔPITAL A OLD", categorical_cols=["sexe", "type_traitement"])
    inspect_dataframe(df_b, "HÔPITAL B OLD", categorical_cols=["sexe_code", "treatment_type"])

    df_all = pd.concat([prepare_a(df_a), prepare_b(df_b)], ignore_index=True)
    df_all = assign_patient_uid(df_all)

    patients = build_patient_table(df_all)
    traitements = df_all[[
        "patient_uid", "id_source", "id_patient_src",
        "date_traitement", "type_traitement", "compte_rendu",
    ]].copy()
    traitements.insert(0, "id_traitement", range(1, len(traitements) + 1))

    traitements["stade"] = traitements["compte_rendu"].apply(extract_stade)

    inspect_dataframe(patients, "PATIENTS (table finale)", categorical_cols=["sexe", "sexe_conflit", "nb_sources", "est_complet"])
    inspect_dataframe(traitements, "TRAITEMENTS (table finale)", categorical_cols=["type_traitement", "stade"])
    
    print(f"Lignes brutes : {len(df_all)} | Patients : {len(patients)} | Traitements : {len(traitements)}")
    quality_report(traitements, patients)

    Path("data/processed").mkdir(parents=True, exist_ok=True)
    patients.to_csv("data/processed/patients_clean.csv", index=False)
    traitements.to_csv("data/processed/traitements_clean.csv", index=False)

if __name__ == "__main__":
    main()