{#
  Même règle de sécurité que dans le projet 1 :
  la direction voit tout, chaque lecteur ne voit que son pays.
  (Les lignes "GROUPE" des totaux ne sont visibles que par la direction.)
#}
{% macro appliquer_rls() %}
    alter table {{ this }} enable row level security;
    create policy filtre_par_entite on {{ this }}
        for select
        using (
            pg_has_role(current_user, 'direction_groupe', 'member')
            or code_entite = upper(replace(current_user, 'lecteur_', ''))
        );
{% endmacro %}
