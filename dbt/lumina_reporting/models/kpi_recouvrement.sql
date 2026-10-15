-- Recouvrement mensuel par pays.
-- Taux de recouvrement = argent encaissé dans le mois / montant des échéances du mois.
-- (Il peut dépasser 100 % quand des clients rattrapent des retards.)
{{ config(post_hook="{{ appliquer_rls() }}") }}

with du as (
    select code_entite, date_trunc('month', date_echeance)::date as mois,
           sum(montant_du) as montant_du, count(*) as nb_echeances
    from {{ source('entrepot', 'fact_echeances') }}
    where date_echeance <= current_date
    group by 1, 2
),

encaisse as (
    select code_entite, date_trunc('month', date_paiement)::date as mois,
           sum(montant)                                               as montant_encaisse,
           sum(montant) filter (where famille_canal = 'Mobile money') as montant_mobile_money,
           count(*)                                                   as nb_paiements
    from {{ source('entrepot', 'fact_remboursements') }}
    group by 1, 2
)

select
    coalesce(du.mois, e.mois)                                     as mois,
    coalesce(du.code_entite, e.code_entite)                       as code_entite,
    coalesce(du.montant_du, 0)                                    as montant_du,
    coalesce(e.montant_encaisse, 0)                               as montant_encaisse,
    coalesce(e.montant_mobile_money, 0)                           as montant_mobile_money,
    coalesce(du.nb_echeances, 0)                                  as nb_echeances,
    coalesce(e.nb_paiements, 0)                                   as nb_paiements,
    round(coalesce(e.montant_encaisse, 0) / nullif(du.montant_du, 0), 4)              as taux_recouvrement,
    round(coalesce(e.montant_mobile_money, 0) / nullif(e.montant_encaisse, 0), 4)    as part_mobile_money,
    coalesce(du.mois, e.mois) < date_trunc('month', current_date)                    as est_mois_complet,
    coalesce(du.mois, e.mois) = date_trunc('month', current_date) - interval '1 month' as est_dernier_mois_complet
from du
full outer join encaisse e on e.code_entite = du.code_entite and e.mois = du.mois
