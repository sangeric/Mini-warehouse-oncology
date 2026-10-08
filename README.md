# Mini-entrepôt de données oncologiques

## Description

Projet de Data Engineering basé sur deux sources de données hospitalières fictives.

Le projet simule un flux réel : deux sources hétérogènes → nettoyage → réconciliation des patients → entrepôt PostgreSQL → contrôles qualité.

Les données sont volontairement "sales" (formats de dates différents, codes sexe différents, doublons entre sources, valeurs manquantes, texte libre) pour se rapprocher de données de santé de vie réelle.

## Étapes du projet

1. **Données et audit** : génération des deux sources CSV et exploration (valeurs manquantes, doublons, formats incohérents)
2. **Nettoyage et réconciliation** : schéma commun, normalisation des dates et du sexe, rapprochement des patients sur nom + prénom + date de naissance
3. **NLP** : extraction du stade oncologique depuis les comptes-rendus en texte libre (regex)
4. **Base de données** : modélisation relationnelle et chargement dans PostgreSQL (Docker)
5. **SQL** : jointure, agrégation, fenêtrage et requêtes de contrôle qualité
6. **Git** : versionnement par étape, branche de fonctionnalité et pull request
7. **CI/CD** : tests automatiques avec GitHub Actions à chaque push

## Structure

```text
Mini-warehouse-oncology/
│
├── data/
│   ├── raw/                  # sources brutes (hôpital A et B)
│   └── processed/            # données nettoyées
│
├── src/
│   ├── generate_sources.py   # génère les deux CSV sources
│   ├── audit.py              # exploration, nettoyage, réconciliation, NLP
│   ├── load_db.py            # chargement dans PostgreSQL
│   └── test_pipeline.py      # tests qualité
│
├── sql/                      # requêtes d'analyse et de contrôle
│
├── .github/
│   └── workflows/
│       └── tests.yml         # workflow CI GitHub Actions
│
├── docker-compose.yml        # base PostgreSQL
├── requirements.txt
└── README.md
```

## Technologies

* Python (Pandas, NumPy)
* PostgreSQL
* Docker
* SQL
* Git / GitHub
* GitHub Actions

## Pipeline

```text
Données brutes (A + B)
      ↓
Audit qualité
      ↓
Nettoyage et normalisation
      ↓
Réconciliation des patients
      ↓
Extraction du stade (NLP)
      ↓
PostgreSQL (staging + tables Patient / Traitement)
      ↓
Requêtes SQL et contrôles qualité
      ↓
Tests automatiques (CI)
```

## Modèle de données

* **staging_hopital_a / staging_hopital_b** : copie brute des sources, sans transformation (traçabilité)
* **patient** : un patient par ligne, après fusion des doublons entre sources
* **traitement** : un traitement par ligne, relié au patient par clé étrangère

## Choix de conception

### Une ligne source = un traitement

Dans les fichiers sources, chaque ligne correspond à un traitement, pas à un patient. Un même patient apparaît donc sur plusieurs lignes (plusieurs traitements, parfois dans les deux hôpitaux).

C'est pourquoi les 103 lignes sources donnent 103 traitements, mais seulement 47 patients une fois les doublons fusionnés. On déduplique les patients, jamais les traitements.

### Réconciliation des patients

Deux lignes sont considérées comme le même patient si elles partagent, après normalisation (minuscules, sans accents, espaces nettoyés) :

* le nom
* le prénom
* la date de naissance

Ces trois champs forment la clé de rapprochement. Les autres informations (sexe, deuxième prénom, identifiant source) ne servent pas à identifier le patient.

Un seul regroupement sur cette clé traite tous les cas à la fois : les doublons à l'intérieur d'une même source comme les doublons entre les deux sources.

Si l'un des trois champs est manquant, la ligne n'est pas fusionnée : mieux vaut un doublon résiduel qu'une fusion erronée de deux patients différents.

### Complétude des patients

Un patient est marqué `est_complet = true` si son identité est fiable, c'est-à-dire si le nom, le prénom et la date de naissance sont présents.

Tous les patients sont chargés dans la table `patient`, complets ou non. La colonne `est_complet` permet de distinguer les données fiables des données à revoir, sans rien supprimer :

```sql
SELECT * FROM patient WHERE est_complet;      -- identité fiable
SELECT * FROM patient WHERE NOT est_complet;  -- à revoir
```

Les attributs secondaires (sexe, deuxième prénom) peuvent être absents même pour un patient complet : ce sont des valeurs manquantes de la source, conservées telles quelles.

### Pourquoi ne pas utiliser l'INS

En production, le rapprochement se ferait sur l'INS (Identité Nationale de Santé), un identifiant national unique qui rend la réconciliation fiable et déterministe.

Ce projet ne l'utilise volontairement pas, pour travailler sur le cas plus réaliste et plus difficile où aucun identifiant fiable n'est disponible (données anciennes, sources hétérogènes, INS non renseigné). Dans un système réel, l'INS servirait de clé principale, avec nom + prénom + date de naissance comme méthode de secours lorsqu'il est absent.

## Contrôles qualité

Le projet vérifie notamment :

* les valeurs manquantes
* les doublons de patients entre les sources
* les conflits de sexe entre sources
* les dates incohérentes (traitement avant la naissance, date dans le futur)
* le taux d'extraction du stade depuis le texte libre
* l'intégrité référentielle (clé étrangère Traitement → Patient)

## Installation

```bash
pip install -r requirements.txt
docker compose up -d
```

## Lancer le pipeline

```bash
python src/generate_sources.py
python src/audit.py
python src/load_db.py
```

Pour interroger la base :

```bash
docker compose exec postgres psql -U app -d entrepot
```

## Tests

```bash
python src/test_pipeline.py
```

Les tests sont aussi lancés automatiquement par GitHub Actions à chaque push et pull request.

## Résultat attendu

Le pipeline produit des données :

* nettoyées
* normalisées
* réconciliées entre les sources
* chargées dans un entrepôt relationnel
* contrôlées

avec un suivi des anomalies détectées.