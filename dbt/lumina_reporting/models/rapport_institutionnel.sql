-- Reporting institutionnel trimestriel (format type bailleur / régulateur).
-- Une ligne par pays + une ligne GROUPE (consolidée) par trimestre.
{{ config(post_hook="{{ appliquer_rls() }}") }}

with trimestres as (
    select date_arrete, est_dernier_arrete,
           date_trunc('quarter', date_arrete)::date as debut_trimestre
    from {{ ref('dates_arrete') }}
    where est_fin_trimestre
),

stock as (
    select k.*, t.debut_trimestre
    from {{ ref('kpi_par') }} k
    join trimestres t using (date_arrete)
),

decaissements as (
    select t.date_arrete, p.code_entite, sum(p.montant_finance) as montant_decaisse, count(*) as nb_prets_decaisses
    from trimestres t
    join {{ source('entrepot', 'fact_prets') }} p
      on p.date_decaissement between t.debut_trimestre and t.date_arrete
    group by 1, 2
),

encaissements as (
    select t.date_arrete, r.code_entite, sum(r.montant) as montant_encaisse
    from trimestres t
    join {{ source('entrepot', 'fact_remboursements') }} r
      on r.date_paiement between t.debut_trimestre and t.date_arrete
    group by 1, 2
),

par_entite as (
    select s.*, coalesce(d.montant_decaisse, 0) as montant_decaisse,
           coalesce(d.nb_prets_decaisses, 0) as nb_prets_decaisses,
           coalesce(e.montant_encaisse, 0) as montant_encaisse
    from stock s
    left join decaissements d using (date_arrete, code_entite)
    left join encaissements e using (date_arrete, code_entite)
)

select
    date_arrete,
    'T' || extract(quarter from date_arrete) || ' ' || extract(year from date_arrete)
        || case when bool_or(est_dernier_arrete) then ' (en cours)' else '' end   as periode,
    coalesce(code_entite, 'GROUPE')                                  as code_entite,
    sum(nb_clients_actifs)                                           as nb_clients_actifs,
    sum(nb_prets_actifs)                                             as nb_prets_actifs,
    sum(nb_prets_decaisses)                                          as nb_prets_decaisses,
    sum(montant_decaisse)                                            as montant_decaisse,
    sum(montant_encaisse)                                            as montant_encaisse,
    sum(encours)                                                     as encours,
    round(sum(encours_par30) / nullif(sum(encours), 0), 4)           as par30,
    round(sum(encours_par90) / nullif(sum(encours), 0), 4)           as par90,
    sum(provisions)                                                  as provisions,
    round(sum(provisions) / nullif(sum(encours), 0), 4)              as taux_provisionnement
from par_entite
group by grouping sets ((date_arrete, code_entite), (date_arrete))
