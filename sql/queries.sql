-- Requête 1 — Jointure
SELECT p.nom_norm, p.age,
       t.date_traitement, t.type_traitement, t.stade
FROM Traitement t
JOIN Patient p ON t.patient_uid = p.patient_uid
ORDER BY p.nom_norm, t.date_traitement;

-- Requête 2 — Agrégation par stade
SELECT t.stade,
       COUNT(DISTINCT t.patient_uid) AS nb_patients,
       COUNT(*)                      AS nb_traitements
FROM Traitement t
JOIN Patient p ON t.patient_uid = p.patient_uid
GROUP BY t.stade
ORDER BY t.stade;

-- Requête 3 — Fenêtrage : dernier traitement par patient
SELECT *
FROM (
    SELECT t.patient_uid, t.date_traitement, t.type_traitement, t.stade,
           ROW_NUMBER() OVER (
               PARTITION BY t.patient_uid
               ORDER BY t.date_traitement DESC
           ) AS rang
    FROM Traitement t
) classe
WHERE rang = 1;

-- Requête 4 — Anomalies qualité
SELECT t.id_traitement, p.nom_norm, p.date_naissance, t.date_traitement, t.stade,
       CASE
           WHEN t.date_traitement < p.date_naissance THEN 'traitement avant naissance'
           WHEN t.date_traitement > CURRENT_DATE      THEN 'date dans le futur'
           WHEN t.stade IS NULL                       THEN 'stade non extrait'
       END AS anomalie
FROM Traitement t
JOIN Patient p ON t.patient_uid = p.patient_uid
WHERE t.date_traitement < p.date_naissance
   OR t.date_traitement > CURRENT_DATE
   OR t.stade IS NULL;