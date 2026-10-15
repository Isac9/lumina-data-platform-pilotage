-- CONTRÔLE : un prêt n'apparaît qu'une seule fois par date d'arrêté.

select date_arrete, id_pret, count(*) as nb
from {{ ref('fct_situation_prets') }}
group by date_arrete, id_pret
having count(*) > 1
