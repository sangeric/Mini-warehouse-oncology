import pandas as pd

def test_pas_de_patient_uid_null():
    df = pd.read_csv("data/processed/traitements_clean.csv")
    assert df["patient_uid"].notna().all(), "Des patient_uid sont nuls après nettoyage !"
    print("OK : aucun patient_uid nul")

if __name__ == "__main__":
    test_pas_de_patient_uid_null()