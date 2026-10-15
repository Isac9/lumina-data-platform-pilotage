"""
Installe AUTOMATIQUEMENT dans Superset (par son API) :
  1. la connexion à l'entrepôt PostgreSQL ;
  2. les jeux de données (datasets) + les MÉTRIQUES officielles (PAR 30, etc.) ;
  3. 15 graphiques répartis dans 3 tableaux de bord ;
  4. un filtre "Pays" sur chaque tableau de bord ;
  5. 3 directeurs pays qui ne voient QUE leur pays (Row Level Security).

C'est du "dashboard as code" : on peut tout réinstaller à l'identique.
"""

import json
import time

import psycopg2
import requests

SUPERSET = "http://superset:8088"
# Superset lit l'entrepôt avec le compte "direction_groupe" (lecture seule, tous pays)
URI_ENTREPOT = "postgresql://direction_groupe:groupe123@dwh-db:5432/dwh"
NOM_BASE = "Entrepôt Lumina"
PAYS = {"CI": "Côte d'Ivoire", "SN": "Sénégal", "BF": "Burkina Faso"}

# Métriques officielles : définies UNE fois, réutilisées par tous les graphiques
METRIQUES = {
    "kpi_par": [
        ("encours_total", "sum(encours)", "Encours (FCFA)", ",.0f"),
        ("par30", "sum(encours_par30) / nullif(sum(encours), 0)", "PAR 30", ".1%"),
        ("par60", "sum(encours_par60) / nullif(sum(encours), 0)", "PAR 60", ".1%"),
        ("par90", "sum(encours_par90) / nullif(sum(encours), 0)", "PAR 90", ".1%"),
        ("par120", "sum(encours_par120) / nullif(sum(encours), 0)", "PAR 120", ".1%"),
        ("provisions", "sum(provisions)", "Provisions (FCFA)", ",.0f"),
        ("nb_prets_actifs", "sum(nb_prets_actifs)", "Prêts actifs", ",d"),
    ],
    "kpi_provisions": [
        ("encours_total", "sum(encours)", "Encours (FCFA)", ",.0f"),
        ("provision", "sum(provision)", "Provision (FCFA)", ",.0f"),
        ("nb_prets", "sum(nb_prets)", "Nombre de prêts", ",d"),
    ],
    "kpi_roll_rates": [
        ("nb_prets", "sum(nb_prets)", "Nombre de prêts", ",d"),
    ],
    "kpi_recouvrement": [
        ("taux_recouvrement", "sum(montant_encaisse) / nullif(sum(montant_du), 0)", "Taux de recouvrement", ".1%"),
        ("montant_encaisse", "sum(montant_encaisse)", "Encaissé (FCFA)", ",.0f"),
        ("montant_du", "sum(montant_du)", "Dû (FCFA)", ",.0f"),
    ],
    "kpi_commercial": [
        ("montant_finance", "sum(montant_finance)", "Montant financé (FCFA)", ",.0f"),
        ("nb_ventes", "sum(nb_ventes)", "Nombre de ventes", ",d"),
    ],
    "kpi_agents": [],
    "rapport_institutionnel": [],
}

DERNIER_ARRETE = {"expressionType": "SQL", "sqlExpression": "est_dernier_arrete", "clause": "WHERE"}


# ------------------------------------------------------------------ attentes
def attendre_tables():
    """Attend que le pipeline Airflow du projet 2 ait créé les tables d'indicateurs."""
    print("Attente des tables d'indicateurs (créées par le pipeline Airflow)...", flush=True)
    for _ in range(180):  # jusqu'à 30 minutes
        try:
            with psycopg2.connect(host="dwh-db", dbname="dwh", user="lumina", password="lumina") as conn:
                with conn.cursor() as cur:
                    cur.execute("select to_regclass('reporting.rapport_institutionnel') is not null")
                    if cur.fetchone()[0]:
                        print("Tables prêtes.", flush=True)
                        return
        except psycopg2.OperationalError:
            pass
        time.sleep(10)
    raise SystemExit("Les tables reporting n'existent pas : vérifiez le pipeline dans Airflow.")


# ------------------------------------------------------------------ API Superset
class Superset:
    def __init__(self):
        self.s = requests.Session()
        jeton = self.s.post(f"{SUPERSET}/api/v1/security/login", json={
            "username": "admin", "password": "admin", "provider": "db", "refresh": True,
        }).json()["access_token"]
        self.s.headers["Authorization"] = f"Bearer {jeton}"
        csrf = self.s.get(f"{SUPERSET}/api/v1/security/csrf_token/").json()["result"]
        self.s.headers.update({"X-CSRFToken": csrf, "Referer": SUPERSET})

    def appel(self, methode, chemin, **kwargs):
        reponse = self.s.request(methode, f"{SUPERSET}/api/v1/{chemin}", **kwargs)
        if reponse.status_code >= 400:
            raise RuntimeError(f"{methode} {chemin} -> {reponse.status_code} : {reponse.text[:500]}")
        return reponse.json()

    def chercher(self, ressource, colonne, valeur):
        q = f"(filters:!((col:{colonne},opr:eq,value:'{valeur}')))"
        resultats = self.appel("GET", f"{ressource}/", params={"q": q})["result"]
        return resultats[0] if resultats else None


def creer_base(api):
    base = api.chercher("database", "database_name", NOM_BASE)
    if base:
        return base["id"]
    return api.appel("POST", "database/", json={
        "database_name": NOM_BASE, "sqlalchemy_uri": URI_ENTREPOT, "expose_in_sqllab": True,
    })["id"]


def creer_datasets(api, id_base):
    ids = {}
    for table, metriques in METRIQUES.items():
        existant = api.chercher("dataset", "table_name", table)
        if existant:
            ids[table] = existant["id"]
            continue
        id_ds = api.appel("POST", "dataset/", json={"database": id_base, "schema": "reporting", "table_name": table})["id"]
        if metriques:
            api.appel("PUT", f"dataset/{id_ds}", json={"metrics": [
                {"metric_name": nom, "expression": expr, "verbose_name": libelle, "d3format": fmt}
                for nom, expr, libelle, fmt in metriques
            ]})
        ids[table] = id_ds
        print(f"  dataset {table} : id {id_ds}", flush=True)
    return ids


# ------------------------------------------------------------------ graphiques
def grand_nombre(titre, metrique, fmt, filtre=DERNIER_ARRETE):
    return {"viz_type": "big_number_total", "metric": metrique, "y_axis_format": fmt,
            "adhoc_filters": [filtre], "header_font_size": 0.4, "subheader_font_size": 0.15,
            "_titre": titre}


def courbe(titre, x, metriques, fmt, groupby=None, filtres=None):
    return {"viz_type": "echarts_timeseries_line", "x_axis": x, "time_grain_sqla": "P1M",
            "metrics": metriques, "groupby": groupby or [], "adhoc_filters": filtres or [],
            "y_axis_format": fmt, "row_limit": 10000, "show_legend": True, "rich_tooltip": True,
            "markerEnabled": True, "_titre": titre}


def barres(titre, x, metrique, groupby, fmt=",.0f"):
    return {"viz_type": "echarts_timeseries_bar", "x_axis": x, "time_grain_sqla": "P1M",
            "metrics": [metrique], "groupby": groupby, "adhoc_filters": [], "stack": "Stack",
            "y_axis_format": fmt, "row_limit": 10000, "show_legend": True, "rich_tooltip": True,
            "_titre": titre}


def tableau(titre, colonnes, tri, formats, filtres=None):
    return {"viz_type": "table", "query_mode": "raw", "all_columns": colonnes,
            "order_by_cols": [json.dumps([tri, False])], "adhoc_filters": filtres or [],
            "row_limit": 1000, "server_page_length": 20, "table_timestamp_format": "%d/%m/%Y",
            "column_config": {c: {"d3NumberFormat": f} for c, f in formats.items()},
            "_titre": titre}


def definir_tableaux_de_bord():
    pct = ".1%"
    return [
        {
            "titre": "1. Pilotage Groupe", "slug": "pilotage-groupe", "dataset_filtre": "kpi_par",
            "lignes": [
                [("kpi_par", grand_nombre("Encours total (FCFA)", "encours_total", ",.0f"), 3, 40),
                 ("kpi_par", grand_nombre("PAR 30", "par30", pct), 3, 40),
                 ("kpi_par", grand_nombre("PAR 90", "par90", pct), 3, 40),
                 ("kpi_par", grand_nombre("Provisions (FCFA)", "provisions", ",.0f"), 3, 40)],
                [("kpi_par", courbe("Évolution du PAR 30 et du PAR 90 (consolidé)", "date_arrete", ["par30", "par90"], pct), 6, 60),
                 ("kpi_par", barres("Encours par pays (FCFA)", "date_arrete", "encours_total", ["code_entite"]), 6, 60)],
                [("rapport_institutionnel", tableau(
                    "Reporting institutionnel trimestriel",
                    ["periode", "code_entite", "nb_clients_actifs", "nb_prets_actifs", "montant_decaisse",
                     "montant_encaisse", "encours", "par30", "par90", "provisions", "taux_provisionnement"],
                    "date_arrete",
                    {"par30": pct, "par90": pct, "taux_provisionnement": pct, "encours": ",.0f",
                     "provisions": ",.0f", "montant_decaisse": ",.0f", "montant_encaisse": ",.0f"}), 12, 60)],
            ],
        },
        {
            "titre": "2. Risque crédit", "slug": "risque-credit", "dataset_filtre": "kpi_par",
            "lignes": [
                [("kpi_par", courbe("PAR 30 par pays", "date_arrete", ["par30"], pct, ["code_entite"]), 6, 60),
                 ("kpi_provisions", barres("Encours par tranche de retard (FCFA)", "date_arrete", "encours_total", ["tranche_retard"]), 6, 60)],
                [("kpi_provisions", {
                    "viz_type": "table", "query_mode": "aggregate", "groupby": ["tranche_retard", "taux_provision"],
                    "metrics": ["nb_prets", "encours_total", "provision"], "adhoc_filters": [DERNIER_ARRETE],
                    "timeseries_limit_metric": {"expressionType": "SQL", "sqlExpression": "min(tranche_retard)", "label": "ordre"},
                    "order_desc": False, "row_limit": 100, "show_totals": True,
                    "column_config": {"taux_provision": {"d3NumberFormat": ".0%"}},
                    "_titre": "Provisions par tranche (aujourd'hui)"}, 6, 50),
                 ("kpi_roll_rates", {
                    "viz_type": "pivot_table_v2", "groupbyRows": ["tranche_debut"], "groupbyColumns": ["tranche_fin"],
                    "metrics": ["nb_prets"], "metricsLayout": "COLUMNS", "aggregateFunction": "Sum",
                    "adhoc_filters": [DERNIER_ARRETE], "rowOrder": "key_a_to_z", "colOrder": "key_a_to_z",
                    "valueFormat": "SMART_NUMBER", "rowTotals": True, "colTotals": True, "row_limit": 1000,
                    "_titre": "Matrice de transition depuis la fin du mois dernier (nb de prêts)"}, 6, 50)],
            ],
        },
        {
            "titre": "3. Recouvrement et commercial", "slug": "recouvrement-commercial", "dataset_filtre": "kpi_recouvrement",
            "lignes": [
                [("kpi_recouvrement", grand_nombre(
                    "Taux de recouvrement (dernier mois complet)", "taux_recouvrement", pct,
                    {"expressionType": "SQL", "clause": "WHERE", "sqlExpression": "est_dernier_mois_complet"}), 4, 50),
                 ("kpi_recouvrement", courbe("Taux de recouvrement mensuel par pays", "mois", ["taux_recouvrement"], pct,
                                             ["code_entite"], [{"expressionType": "SQL", "clause": "WHERE", "sqlExpression": "est_mois_complet"}]), 8, 50)],
                [("kpi_commercial", barres("Montant financé par mois et par produit (FCFA)", "mois", "montant_finance", ["code_produit"]), 6, 60),
                 ("kpi_agents", tableau(
                    "Agents commerciaux : ventes et qualité du portefeuille",
                    ["nom_agent", "code_entite", "zone", "nb_ventes", "montant_finance", "encours", "par30"],
                    "montant_finance", {"par30": pct, "montant_finance": ",.0f", "encours": ",.0f"}), 6, 60)],
            ],
        },
    ]


def disposition(titre, lignes):
    pos = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {"type": "GRID", "id": "GRID_ID", "children": [], "parents": ["ROOT_ID"]},
        "HEADER_ID": {"id": "HEADER_ID", "type": "HEADER", "meta": {"text": titre}},
    }
    for i, ligne in enumerate(lignes):
        id_ligne = f"ROW-{i}"
        pos["GRID_ID"]["children"].append(id_ligne)
        pos[id_ligne] = {"type": "ROW", "id": id_ligne, "children": [], "parents": ["ROOT_ID", "GRID_ID"],
                         "meta": {"background": "BACKGROUND_TRANSPARENT"}}
        for id_graphique, nom, largeur, hauteur in ligne:
            cle = f"CHART-{id_graphique}"
            pos[id_ligne]["children"].append(cle)
            pos[cle] = {"type": "CHART", "id": cle, "children": [], "parents": ["ROOT_ID", "GRID_ID", id_ligne],
                        "meta": {"chartId": id_graphique, "width": largeur, "height": hauteur, "sliceName": nom}}
    return pos


def creer_tableaux_de_bord(api, datasets):
    for tdb in definir_tableaux_de_bord():
        if api.chercher("dashboard", "slug", tdb["slug"]):
            print(f"Tableau de bord « {tdb['titre']} » déjà présent.", flush=True)
            continue
        id_tdb = api.appel("POST", "dashboard/", json={"dashboard_title": tdb["titre"], "slug": tdb["slug"], "published": True})["id"]
        lignes, ids_graphiques = [], []
        for ligne in tdb["lignes"]:
            ligne_creee = []
            for table, params, largeur, hauteur in ligne:
                titre = params.pop("_titre")
                params["datasource"] = f"{datasets[table]}__table"
                id_g = api.appel("POST", "chart/", json={
                    "slice_name": titre, "viz_type": params["viz_type"], "datasource_id": datasets[table],
                    "datasource_type": "table", "params": json.dumps(params), "dashboards": [id_tdb],
                })["id"]
                ids_graphiques.append(id_g)
                ligne_creee.append((id_g, titre, largeur, hauteur))
            lignes.append(ligne_creee)
        filtre_pays = {
            "id": "NATIVE_FILTER-pays", "name": "Pays", "filterType": "filter_select", "type": "NATIVE_FILTER",
            "targets": [{"datasetId": datasets[tdb["dataset_filtre"]], "column": {"name": "code_entite"}}],
            "controlValues": {"enableEmptyFilter": False, "defaultToFirstItem": False, "multiSelect": True,
                              "searchAllOptions": False, "inverseSelection": False},
            "defaultDataMask": {"extraFormData": {}, "filterState": {}, "ownState": {}},
            "cascadeParentIds": [], "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
            "chartsInScope": ids_graphiques, "tabsInScope": [], "description": "Choisir un ou plusieurs pays",
        }
        api.appel("PUT", f"dashboard/{id_tdb}", json={
            "position_json": json.dumps(disposition(tdb["titre"], lignes)),
            "json_metadata": json.dumps({
                "native_filter_configuration": [filtre_pays], "color_scheme": "supersetColors",
                "cross_filters_enabled": True, "refresh_frequency": 0, "expanded_slices": {},
                "label_colors": {}, "timed_refresh_immune_slices": [], "chart_configuration": {},
            }),
        })
        print(f"Tableau de bord « {tdb['titre']} » créé ({len(ids_graphiques)} graphiques).", flush=True)


# ------------------------------------------------------------------ sécurité
def id_permission(api, nom_permission):
    permission = api.chercher("security/permissions", "name", nom_permission)
    q = f"(filters:!((col:permission,opr:rel_o_m,value:{permission['id']})))"
    return api.appel("GET", "security/permissions-resources/", params={"q": q})["result"][0]["id"]


def creer_directeurs_pays(api, datasets):
    gamma = api.chercher("security/roles", "name", "Gamma")["id"]
    acces_donnees = id_permission(api, "all_datasource_access")
    tables_par_pays = [i for t, i in datasets.items()]  # toutes les tables ont une colonne code_entite
    for code, nom_pays in PAYS.items():
        nom_role = f"Lecteur_{code}"
        if api.chercher("security/roles", "name", nom_role):
            continue
        id_role = api.appel("POST", "security/roles/", json={"name": nom_role})["id"]
        api.appel("POST", f"security/roles/{id_role}/permissions", json={"permission_view_menu_ids": [acces_donnees]})
        api.appel("POST", "rowlevelsecurity/", json={
            "name": f"Filtre {nom_pays}", "filter_type": "Regular", "tables": tables_par_pays,
            "roles": [id_role], "clause": f"code_entite = '{code}'", "group_key": "",
            "description": f"Le directeur {nom_pays} ne voit que les lignes {code}",
        })
        api.appel("POST", "security/users/", json={
            "active": True, "first_name": "Directeur", "last_name": nom_pays,
            "username": f"directeur_{code.lower()}", "email": f"directeur.{code.lower()}@exemple.com",
            "password": f"{code.lower()}2026", "roles": [gamma, id_role],
        })
        print(f"Utilisateur directeur_{code.lower()} créé (ne voit que {code}).", flush=True)


if __name__ == "__main__":
    attendre_tables()
    api = Superset()
    id_base = creer_base(api)
    datasets = creer_datasets(api, id_base)
    creer_tableaux_de_bord(api, datasets)
    creer_directeurs_pays(api, datasets)
    print("✅ Superset est prêt : http://localhost:8088", flush=True)
