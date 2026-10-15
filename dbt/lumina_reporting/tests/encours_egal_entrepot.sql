-- CONTRÔLE : l'encours d'aujourd'hui dans le reporting doit être égal
-- à l'encours calculé dans l'entrepôt (projet 1), pour chaque pays.
-- Si ce test échoue, les deux projets ne racontent pas la même histoire.

with reporting as (
    select code_entite, sum(encours) as encours
    from {{ ref('fct_situation_prets') }}
    where est_dernier_arrete
    group by code_entite
),
entrepot as (
    select code_entite, sum(encours) as encours
    from {{ source('entrepot', 'fact_prets') }}
    group by code_entite
)
select e.code_entite, e.encours as encours_entrepot, r.encours as encours_reporting
from entrepot e
full outer join reporting r using (code_entite)
where coalesce(e.encours, 0) <> coalesce(r.encours, 0)
