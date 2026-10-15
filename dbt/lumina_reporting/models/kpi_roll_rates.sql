-- Matrice de transition ("roll rates") : d'un mois à l'autre, dans quelle
-- tranche de retard passent les prêts ? (ex. : combien de prêts "1 à 30 j"
-- sont passés à "31 à 60 j" ?). C'est un signal d'alerte précoce.
{{ config(post_hook="{{ appliquer_rls() }}") }}

with situation as (
    select date_arrete, id_pret, code_entite, tranche_retard, encours
    from {{ ref('fct_situation_prets') }}
),

periodes as (
    select date_arrete, date_arrete_precedente, est_dernier_arrete
    from {{ ref('dates_arrete') }}
    where date_arrete_precedente is not null
)

select
    p.date_arrete,
    p.est_dernier_arrete,
    debut.code_entite,
    debut.tranche_retard                              as tranche_debut,
    coalesce(fin.tranche_retard, '6 - Soldé')         as tranche_fin,
    count(*)                                          as nb_prets,
    sum(debut.encours)                                as encours_debut
from periodes p
join situation debut on debut.date_arrete = p.date_arrete_precedente
left join situation fin on fin.date_arrete = p.date_arrete and fin.id_pret = debut.id_pret
group by 1, 2, 3, 4, 5
