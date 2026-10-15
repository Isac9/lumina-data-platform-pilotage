-- Provisions par tranche de retard (règles dans seeds/regles_provisionnement.csv).
{{ config(post_hook="{{ appliquer_rls() }}") }}

select
    date_arrete,
    est_dernier_arrete,
    code_entite,
    tranche_retard,
    taux_provision,
    count(*)        as nb_prets,
    sum(encours)    as encours,
    sum(provision)  as provision
from {{ ref('fct_situation_prets') }}
group by date_arrete, est_dernier_arrete, code_entite, tranche_retard, taux_provision
