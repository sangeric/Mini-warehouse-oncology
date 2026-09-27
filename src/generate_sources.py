# -*- coding: utf-8 -*-
"""
Génère 2 CSV sources hétérogènes et volontairement "sales".
Nouveauté : nom / prénom / deuxième prénom en colonnes SÉPARÉES.
Le deuxième prénom est souvent vide (NaN) et sera conservé en base.
- source_hopital_A.csv : colonnes FR, dates JJ/MM/AAAA, sexe M/F
- source_hopital_B.csv : colonnes EN, dates AAAA-MM-JJ, sexe 1/2
Doublons volontaires : mêmes patients dans les 2 sources, IDs différents.
"""
import csv
import random
import unicodedata
from datetime import date, timedelta

random.seed(42)

def strip_accents(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")

# (prenom, deuxieme_prenom|None, nom, annee, mois, jour, sexe, presence)
# noms avec accents volontaires (Lefèvre, Génin...) pour justifier le déaccentuage
patients = [
    ("Martin",   "Louis",  "Dupont",    1958, 3, 12, "M", "both"),
    ("Sophie",   None,     "Bernard",   1965, 7, 22, "F", "both"),
    ("Jean",     "Pierre", "Petit",     1949, 11, 5, "M", "both"),
    ("Nathalie", None,     "Moreau",    1972, 1, 30, "F", "both"),
    ("Ahmed",    None,     "Benali",    1960, 9, 14, "M", "both"),
    ("Isabelle", "Marie",  "Girard",    1955, 5, 3,  "F", "both"),
    ("Philippe", None,     "Roux",      1948, 12, 19,"M", "both"),
    ("Fatima",   None,     "Haddad",    1968, 4, 8,  "F", "both"),
    ("Laurent",  "Andre",  "Fontaine",  1961, 2, 27, "M", "both"),
    ("Christine",None,     "Lefevre",   1953, 8, 16, "F", "both"),   # accent ajouté à l'écriture
    ("Michel",   None,     "Garnier",   1946, 6, 11, "M", "both"),
    ("Sylvie",   "Anne",   "Faure",     1970, 10, 2, "F", "both"),

    ("Pierre",   None,     "Durand",    1959, 3, 25, "M", "A"),
    ("Marie",    "Jose",   "Leroy",     1963, 7, 9,  "F", "A"),
    ("Antoine",  None,     "Muller",    1951, 11, 30,"M", "A"),
    ("Camille",  None,     "Blanc",     1975, 1, 18, "F", "A"),
    ("Kevin",    None,     "Guerin",    1980, 5, 21, "M", "A"),
    ("Djamila",  None,     "Meziane",   1966, 9, 7,  "F", "A"),
    ("Robert",   "Henri",  "Chevalier", 1943, 12, 13,"M", "A"),
    ("Aurelie",  None,     "Robin",     1978, 4, 4,  "F", "A"),
    ("Thierry",  None,     "Masson",    1957, 6, 28, "M", "A"),
    ("Nadia",    None,     "Bouchard",  1969, 8, 1,  "F", "A"),
    ("Gerard",   "Paul",   "Lemoine",   1944, 2, 15, "M", "A"),
    ("Valerie",  None,     "Dumas",     1971, 10, 24,"F", "A"),
    ("Olivier",  None,     "Perrin",    1962, 3, 6,  "M", "A"),
    ("Sandrine", None,     "Morel",     1974, 7, 17, "F", "A"),

    ("Bernard",  None,     "Gauthier",  1947, 11, 11,"M", "B"),
    ("Celine",   "Marie",  "Roussel",   1967, 1, 23, "F", "B"),
    ("Vincent",  None,     "Barbier",   1954, 5, 29, "M", "B"),
    ("Emilie",   None,     "Renard",    1979, 9, 10, "F", "B"),
    ("Karim",    None,     "Cherif",    1964, 4, 2,  "M", "B"),
    ("Patricia", "Anne",   "Noel",      1952, 12, 8, "F", "B"),
    ("Alain",    None,     "Aubert",    1945, 6, 20, "M", "B"),
    ("Julie",    None,     "Lopez",     1982, 2, 14, "F", "B"),
    ("Denis",    "Marc",   "Colin",     1956, 8, 26, "M", "B"),
    ("Sabrina",  None,     "Vidal",     1976, 10, 5, "F", "B"),
    ("Francois", None,     "Brun",      1950, 3, 31, "M", "B"),
    ("Monique",  None,     "Gaillard",  1942, 7, 13, "F", "B"),
    ("Hakim",    None,     "Slimani",   1973, 11, 19,"M", "B"),
    ("Chantal",  "Rose",   "Rey",       1959, 5, 7,  "F", "B"),
]

# patients dont le nom porte un accent (écrit accentué en A, sans accent en B -> montre le déaccentuage)
NOMS_ACCENTUES = {"Lefevre": "Lefèvre", "Benali": "Bénali", "Guerin": "Guérin"}

TRAIT = ["chimiotherapie", "radiotherapie", "chirurgie", "immunotherapie", "hormonotherapie"]
STADES = ["I", "II", "III", "IV"]
CANCERS = ["du sein", "pulmonaire", "colorectal", "de la prostate",
           "de l'ovaire", "gastrique", "du pancreas", "ORL"]
CR_TEMPLATES = [
    "Patient stade {stade}, traitement {trait}.",
    "Cancer {cancer} de stade {stade}. Prise en charge par {trait}.",
    "Diagnostic : tumeur {cancer}, Stade {stade}. {trait} en cours.",
    "RCP du {d} : stade {stade}, decision {trait}.",
    "stade {stade} - {trait}. Bonne tolerance.",
    "Bilan : {cancer}, classe stade {stade}. Debut {trait}.",
    "Compte rendu : stade{stade} confirme, {trait} programmee.",
    "Patiente presentant une lesion {cancer} de stade {stade}.",
]

def rd(y0, y1):
    start = date(y0, 1, 1)
    return start + timedelta(days=random.randint(0, (date(y1, 12, 31) - start).days))

def make_cr(stade, trait, cancer, d):
    return random.choice(CR_TEMPLATES).format(
        stade=stade, trait=trait, cancer=cancer, d=d.strftime("%d/%m/%Y"))

def casse(txt, source):
    r = random.random()
    if source == "A":
        if r < 0.55: return txt                      # Title
        elif r < 0.85: return txt.upper()            # UPPER
        else: return f" {txt} "                      # espaces parasites
    else:  # B : systemes hospitaliers souvent en MAJUSCULES
        if r < 0.6: return txt.upper()
        elif r < 0.85: return txt
        else: return txt.lower()

# ---------------- HOPITAL A ----------------
rows_A = []
aid = 1
for (prenom, deux, nom, y, m, d, sexe, presence) in patients:
    if presence not in ("A", "both"):
        continue
    dob = date(y, m, d)
    nom_ecrit = NOMS_ACCENTUES.get(nom, nom)   # accent conservé côté A
    for _ in range(random.choices([1, 2, 3], weights=[3, 4, 2])[0]):
        stade = random.choice(STADES); trait = random.choice(TRAIT); cancer = random.choice(CANCERS)
        dt = rd(2021, 2024)
        sx = sexe
        if random.random() < 0.10: sx = sexe.lower()
        if random.random() < 0.06: sx = ""
        if random.random() < 0.25:
            dob_str = f"{dob.day}/{dob.month}/{dob.year}"
        else:
            dob_str = dob.strftime("%d/%m/%Y")
        if random.random() < 0.05: dob_str = ""
        rows_A.append({
            "id_patient": f"A{aid:03d}",
            "nom": casse(nom_ecrit, "A"),
            "prenom": casse(prenom, "A"),
            "deuxieme_prenom": (deux if (deux and random.random() < 0.85) else ""),
            "date_naissance": dob_str,
            "sexe": sx,
            "date_traitement": dt.strftime("%d/%m/%Y"),
            "type_traitement": trait,
            "compte_rendu": make_cr(stade, trait, cancer, dt),
        })
        aid += 1

# anomalies A
rows_A.append({"id_patient": f"A{aid:03d}", "nom": "Girard", "prenom": "Luc", "deuxieme_prenom": "",
               "date_naissance": "15/06/1990", "sexe": "M", "date_traitement": "10/03/1985",
               "type_traitement": "chirurgie", "compte_rendu": "Patient stade I, traitement chirurgie."}); aid += 1
rows_A.append({"id_patient": f"A{aid:03d}", "nom": "Lambert", "prenom": "Eva", "deuxieme_prenom": "",
               "date_naissance": "03/09/1961", "sexe": "F", "date_traitement": "22/11/2023",
               "type_traitement": "radiotherapie", "compte_rendu": ""}); aid += 1

# ---------------- HOPITAL B ----------------
rows_B = []
bid = 1001
for (prenom, deux, nom, y, m, d, sexe, presence) in patients:
    if presence not in ("B", "both"):
        continue
    dob = date(y, m, d)
    nom_ecrit = strip_accents(NOMS_ACCENTUES.get(nom, nom))  # accent RETIRÉ côté B
    for _ in range(random.choices([1, 2, 3], weights=[3, 4, 2])[0]):
        stade = random.choice(STADES); trait = random.choice(TRAIT); cancer = random.choice(CANCERS)
        dt = rd(2021, 2024)
        sx = "1" if sexe == "M" else "2"
        if random.random() < 0.06: sx = ""
        if random.random() < 0.2:
            dob_str = dob.strftime("%Y-%m-%d 00:00:00")
        else:
            dob_str = dob.strftime("%Y-%m-%d")
        if random.random() < 0.05: dob_str = ""
        rows_B.append({
            "patient_id": f"B{bid}",
            "last_name": casse(nom_ecrit, "B"),
            "first_name": casse(prenom, "B"),
            "middle_name": (deux if (deux and random.random() < 0.5) else ""),  # souvent vide en B
            "birth_date": dob_str,
            "sexe_code": sx,
            "treatment_date": dt.strftime("%Y-%m-%d"),
            "treatment_type": trait,
            "report": make_cr(stade, trait, cancer, dt),
        })
        bid += 1

# anomalies B
rows_B.append({"patient_id": f"B{bid}", "last_name": "MARCHAND", "first_name": "PAUL", "middle_name": "",
               "birth_date": "1955-04-18", "sexe_code": "1", "treatment_date": "2027-08-01",
               "treatment_type": "immunotherapie",
               "report": "Cancer pulmonaire de stade III. Prise en charge par immunotherapie."}); bid += 1
rows_B.append({"patient_id": f"B{bid}", "last_name": "", "first_name": "INCONNU", "middle_name": "",
               "birth_date": "1960-02-02", "sexe_code": "2", "treatment_date": "2023-07-19",
               "treatment_type": "chimiotherapie",
               "report": "stade IV - chimiotherapie. Surveillance rapprochee."}); bid += 1

# ---------------- écriture ----------------
with open("source_hopital_A.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["id_patient", "nom", "prenom", "deuxieme_prenom",
                                      "date_naissance", "sexe", "date_traitement",
                                      "type_traitement", "compte_rendu"])
    w.writeheader(); w.writerows(rows_A)
with open("source_hopital_B.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["patient_id", "last_name", "first_name", "middle_name",
                                      "birth_date", "sexe_code", "treatment_date",
                                      "treatment_type", "report"])
    w.writeheader(); w.writerows(rows_B)

print(f"A : {len(rows_A)} lignes | B : {len(rows_B)} lignes")
print(f"Patients dans les 2 sources : {sum(1 for p in patients if p[7]=='both')}")
