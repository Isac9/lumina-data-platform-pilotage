-- LA table centrale du risque crédit.
-- Une ligne = un prêt encore actif, photographié à une date d'arrêté.
-- On y calcule : l'encours, les arriérés, les JOURS DE RETARD et la tranche.
{{ config(
    post_hook="{{ appliquer_rls() }}",
    indexes=[{'columns': ['date_arrete', 'code_entite']}, {'columns': ['id_pret']}]
) }}

with arretes as (
    select date_arrete, est_dernier_arrete from {{ ref('dates_arrete') }}
),

prets as (
    select id_pret, id_client, id_agent, code_entite, code_produit, date_decaissement, montant_finance
    from {{ source('entrepot', 'fact_prets') }}
),

-- Total payé par chaque prêt, à chaque date d'arrêté
paye as (
    select a.date_arrete, r.id_pret, sum(r.montant) as total_paye
    from arretes a
    join {{ source('entrepot', 'fact_remboursements') }} r on r.date_paiement <= a.date_arrete
    group by a.date_arrete, r.id_pret
),

-- Échéancier avec le montant dû CUMULÉ (1re échéance, 1re + 2e, etc.)
echeancier as (
    select
        id_pret,
        date_echeance,
        montant_du,
        sum(montant_du) over (partition by id_pret order by numero_echeance) as cumul_du
    from {{ source('entrepot', 'fact_echeances') }}
),

base as (
    select a.date_arrete, a.est_dernier_arrete, p.*, coalesce(pa.total_paye, 0) as total_paye
    from arretes a
    join prets p on p.date_decaissement <= a.date_arrete
    left join paye pa on pa.date_arrete = a.date_arrete and pa.id_pret = p.id_pret
),

-- Règle FIFO : l'argent reçu rembourse d'abord les échéances les plus anciennes.
-- Une échéance est impayée si le cumul dû jusqu'à elle dépasse le total payé.
plus_ancienne_impayee as (
    select b.date_arrete, b.id_pret, min(e.date_echeance) as date_impayee
    from base b
    join echeancier e
      on e.id_pret = b.id_pret
     and e.date_echeance < b.date_arrete
     and e.cumul_du > b.total_paye
    group by b.date_arrete, b.id_pret
),

du_a_date as (
    select b.date_arrete, b.id_pret, sum(e.montant_du) as du_a_date
    from base b
    join echeancier e on e.id_pret = b.id_pret and e.date_echeance <= b.date_arrete
    group by b.date_arrete, b.id_pret
),

situation as (
    select
        b.date_arrete,
        b.est_dernier_arrete,
        b.id_pret,
        b.id_client,
        b.id_agent,
        b.code_entite,
        b.code_produit,
        b.date_decaissement,
        b.montant_finance,
        b.total_paye,
        b.montant_finance - b.total_paye                          as encours,
        greatest(coalesce(d.du_a_date, 0) - b.total_paye, 0)      as arrieres,
        coalesce(b.date_arrete - i.date_impayee, 0)               as jours_retard
    from base b
    left join plus_ancienne_impayee i on i.date_arrete = b.date_arrete and i.id_pret = b.id_pret
    left join du_a_date d on d.date_arrete = b.date_arrete and d.id_pret = b.id_pret
    where b.montant_finance - b.total_paye > 0   -- seulement les prêts pas encore soldés
)

select
    s.*,
    r.tranche_retard,
    r.taux_provision,
    round(s.encours * r.taux_provision) as provision
from situation s
join {{ ref('regles_provisionnement') }} r
  on s.jours_retard between r.jours_min and r.jours_max
