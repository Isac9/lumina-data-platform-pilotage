-- CONTRÔLE : dans le rapport institutionnel, la ligne GROUPE doit être
-- exactement la somme des pays (encours, clients, provisions).

with pays as (
    select date_arrete, sum(encours) as encours, sum(nb_clients_actifs) as clients, sum(provisions) as provisions
    from {{ ref('rapport_institutionnel') }}
    where code_entite <> 'GROUPE'
    group by date_arrete
),
groupe as (
    select date_arrete, encours, nb_clients_actifs as clients, provisions
    from {{ ref('rapport_institutionnel') }}
    where code_entite = 'GROUPE'
)
select g.date_arrete
from groupe g
join pays p using (date_arrete)
where g.encours <> p.encours or g.clients <> p.clients or g.provisions <> p.provisions
