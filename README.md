# Mini-entrepôt de données oncologiques

## Description

Projet de Data Engineering basé sur deux sources de données hospitalières.

Le projet permet de contrôler, nettoyer, intégrer et analyser les données.

## Objectifs

* Auditer les données
* Détecter les erreurs
* Nettoyer les données
* Normaliser les valeurs
* Réconcilier les patients entre les sources
* Extraire le stade oncologique
* Stocker les données dans SQLite
* Effectuer des contrôles SQL
* Ajouter des tests
* Automatiser les tests avec GitHub Actions

## Structure

```text
mini-entrepot-oncologie/
│
├── data/
│   ├── raw/
│   │   ├── source_hopital_A.csv
│   │   └── source_hopital_B.csv
│   │
│   └── processed/
│
├── src/
│   ├── audit.py
│   ├── cleaning.py
│   ├── nlp.py
│   └── database.py
│
├── sql/
│   ├── analysis.sql
│   └── quality_checks.sql
│
├── tests/
│   └── test_pipeline.py
│
├── .github/
│   └── workflows/
│       └── tests.yml
│
├── requirements.txt
└── README.md
```

## Technologies

* Python
* Pandas
* NumPy
* SQLite
* SQL
* GitHub Actions

## Pipeline

```text
Données brutes
      ↓
Audit qualité
      ↓
Nettoyage
      ↓
Normalisation
      ↓
Réconciliation des patients
      ↓
Extraction du stade oncologique
      ↓
Base SQLite
      ↓
Contrôles qualité
      ↓
Tests
```

## Contrôles qualité

Le projet vérifie notamment :

* les valeurs manquantes
* les doublons
* les types de données
* les dates incohérentes
* les valeurs invalides
* les doublons de patients
* les différences entre les sources

## Installation

```bash
pip install -r requirements.txt
```

## Lancer l'audit

```bash
python src/audit.py
```

## Résultat attendu

Le pipeline permet d'obtenir des données :

* nettoyées
* normalisées
* intégrées
* contrôlées

avec un suivi des erreurs et des anomalies détectées.
