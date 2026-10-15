-- CONTRÔLE : les PAR sont entre 0 et 100 %, et toujours dans l'ordre
-- PAR 30 >= PAR 60 >= PAR 90 >= PAR 120 (un prêt à 95 jours est aussi à plus de 30 jours).

select *
from {{ ref('kpi_par') }}
where par30 not between 0 and 1
   or par30 < par60
   or par60 < par90
   or par90 < par120
