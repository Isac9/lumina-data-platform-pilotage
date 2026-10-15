-- Activité commerciale mensuelle par pays et par gamme de produits.
{{ config(post_hook="{{ appliquer_rls() }}") }}

select
    date_trunc('month', p.date_decaissement)::date  as mois,
    p.code_entite,
    p.code_produit,
    count(*)                                        as nb_ventes,
    sum(p.prix_vente)                               as montant_ventes_ttc,
    sum(p.apport_initial)                           as apports_encaisses,
    sum(p.montant_finance)                          as montant_finance,
    coalesce(sum(v.montant_ht), 0)                  as chiffre_affaires_ht
from {{ source('entrepot', 'fact_prets') }} p
left join {{ source('entrepot', 'fact_ventes') }} v on v.id_pret = p.id_pret
group by 1, 2, 3
