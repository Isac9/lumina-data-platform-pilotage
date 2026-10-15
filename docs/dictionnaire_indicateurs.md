# Dictionnaire des indicateurs

> Une seule définition par indicateur, la même partout : dans dbt (calcul), dans Superset (métriques enregistrées) et dans ce document.

## Conventions

- **Date d'arrêté** : jour où l'on « photographie » le portefeuille. C'est le dernier jour de chaque mois écoulé, plus aujourd'hui (table `reporting.dates_arrete`).
- **Prêt actif** : prêt décaissé au plus tard à la date d'arrêté et pas encore soldé (encours > 0).
- **Règle FIFO** : un paiement rembourse toujours en premier l'échéance impayée la plus ancienne.
- **Devise** : FCFA (XOF), sans conversion.
- **Consolidation Groupe** : on additionne les **montants** des pays, puis on calcule les ratios. On ne fait **jamais** la moyenne des pourcentages.

## Indicateurs de risque

| Indicateur | Définition | Formule | Table / métrique | Fréquence | Propriétaire |
|---|---|---|---|---|---|
| **Encours** | Reste à rembourser sur les prêts actifs | montant financé − total payé à la date d'arrêté | `fct_situation_prets.encours` ; métrique `encours_total` | Mensuelle + quotidienne | Direction financière |
| **Jours de retard** | Ancienneté de la plus ancienne échéance impayée (règle FIFO) | date d'arrêté − date de la plus ancienne échéance impayée | `fct_situation_prets.jours_retard` | idem | Risque |
| **Arriérés** | Montant échu et non payé | dû à date − payé à date | `fct_situation_prets.arrieres` | idem | Risque |
| **PAR 30** | Part de l'encours portée par des prêts en retard de plus de 30 jours | Σ encours (retard > 30 j) / Σ encours | `kpi_par.par30` ; métrique `par30` | idem | Risque |
| **PAR 60 / 90 / 120** | Même principe, seuils de 60, 90 et 120 jours | Σ encours (retard > N j) / Σ encours | `kpi_par.par60/90/120` | idem | Risque |
| **Provision** | Perte probable couverte comptablement | encours × taux de la tranche de retard | `fct_situation_prets.provision` ; métrique `provisions` | Mensuelle | Direction financière |
| **Taux de provisionnement** | Couverture du portefeuille | Σ provisions / Σ encours | `rapport_institutionnel.taux_provisionnement` | Trimestrielle | Direction financière |
| **Matrice de transition (roll rates)** | Passage des prêts d'une tranche à l'autre entre deux arrêtés | nombre de prêts (tranche début → tranche fin) | `kpi_roll_rates` | Mensuelle | Risque |

### Barème de provisionnement (paramétrable dans `seeds/regles_provisionnement.csv`)

| Tranche | Jours de retard | Taux |
|---|---|---|
| 0 - À jour | 0 | 1 % |
| 1 - 1 à 30 j | 1-30 | 5 % |
| 2 - 31 à 60 j | 31-60 | 25 % |
| 3 - 61 à 90 j | 61-90 | 50 % |
| 4 - 91 à 120 j | 91-120 | 75 % |
| 5 - Plus de 120 j | > 120 | 100 % |

*Barème illustratif de politique interne. Il est à aligner sur la réglementation applicable (BCEAO / commission bancaire) et sur la politique du Groupe.*

## Indicateurs de recouvrement

| Indicateur | Définition | Formule | Table / métrique |
|---|---|---|---|
| **Montant dû du mois** | Échéances tombant dans le mois | Σ montant des échéances dont la date est dans le mois | `kpi_recouvrement.montant_du` |
| **Montant encaissé du mois** | Paiements reçus dans le mois, quelle que soit l'échéance | Σ paiements du mois | `kpi_recouvrement.montant_encaisse` |
| **Taux de recouvrement** | Capacité à encaisser ce qui est dû | encaissé du mois / dû du mois (peut dépasser 100 % en cas de rattrapage) | métrique `taux_recouvrement` |
| **Part mobile money** | Poids des paiements digitaux | encaissé par mobile money / encaissé total | `kpi_recouvrement.part_mobile_money` |

## Indicateurs commerciaux

| Indicateur | Définition | Table |
|---|---|---|
| **Nombre de ventes** | Prêts décaissés dans la période | `kpi_commercial.nb_ventes` |
| **Montant financé** | Montant à rembourser par les clients (frais inclus) | `kpi_commercial.montant_finance` |
| **Chiffre d'affaires HT** | Ventes comptabilisées dans l'ERP | `kpi_commercial.chiffre_affaires_ht` |
| **PAR 30 par agent** | Qualité du portefeuille vendu par un agent | `kpi_agents.par30` |

## Contrôles qualité associés

| Contrôle | Règle |
|---|---|
| `par_coherents` | 0 ≤ PAR ≤ 100 % et PAR 30 ≥ PAR 60 ≥ PAR 90 ≥ PAR 120 |
| `encours_egal_entrepot` | Encours du reporting = encours de l'entrepôt (projet 1), pays par pays |
| `consolidation_groupe` | La ligne GROUPE est exactement la somme des pays |
| `situation_unique_par_pret_et_date` | Un prêt n'apparaît qu'une fois par date d'arrêté |
