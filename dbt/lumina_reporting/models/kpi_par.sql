-- Portefeuille à Risque (PAR) par pays et par date d'arrêté.
-- PAR 30 = encours des prêts ayant plus de 30 jours de retard / encours total.
-- ⚠️ On garde aussi les MONTANTS (pas seulement les %), pour pouvoir
--    consolider correctement : PAR Groupe = somme des encours à risque / somme des encours.
{{ config(post_hook="{{ appliquer_rls() }}") }}

select
    date_arrete,
    est_dernier_arrete,
    code_entite,
    count(*)                                                        as nb_prets_actifs,
    count(distinct id_client)                                       as nb_clients_actifs,
    sum(encours)                                                    as encours,
    sum(arrieres)                                                   as arrieres,
    coalesce(sum(encours) filter (where jours_retard > 30), 0)      as encours_par30,
    coalesce(sum(encours) filter (where jours_retard > 60), 0)      as encours_par60,
    coalesce(sum(encours) filter (where jours_retard > 90), 0)      as encours_par90,
    coalesce(sum(encours) filter (where jours_retard > 120), 0)     as encours_par120,
    round(coalesce(sum(encours) filter (where jours_retard > 30), 0)  / nullif(sum(encours), 0), 4) as par30,
    round(coalesce(sum(encours) filter (where jours_retard > 60), 0)  / nullif(sum(encours), 0), 4) as par60,
    round(coalesce(sum(encours) filter (where jours_retard > 90), 0)  / nullif(sum(encours), 0), 4) as par90,
    round(coalesce(sum(encours) filter (where jours_retard > 120), 0) / nullif(sum(encours), 0), 4) as par120,
    sum(provision)                                                  as provisions
from {{ ref('fct_situation_prets') }}
group by date_arrete, est_dernier_arrete, code_entite
