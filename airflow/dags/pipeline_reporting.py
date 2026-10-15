"""
DAG Airflow : calcul des indicateurs de pilotage (projet 2).

Il ne démarre PAS à heure fixe : il attend le signal "lumina://dwh/marts"
envoyé par le pipeline du projet 1 quand l'entrepôt est prêt ET testé.

    [pipeline_entrepot_lumina] ──signal──> dbt_seed ──> dbt_run ──> dbt_test
"""

from datetime import datetime, timedelta

from airflow.datasets import Dataset
from airflow.decorators import dag
from airflow.operators.bash import BashOperator

DBT = (
    "cd /opt/dbt_reporting/lumina_reporting && /home/airflow/dbt_venv/bin/dbt"
)
OPTIONS = "--profiles-dir . --target-path /tmp/dbt_target_reporting"

MARTS_PRETS = Dataset("lumina://dwh/marts")
REPORTING_PRET = Dataset("lumina://dwh/reporting")


@dag(
    dag_id="pipeline_reporting_lumina",
    description="Indicateurs de crédit (PAR, recouvrement, provisions) pour Superset",
    schedule=[MARTS_PRETS],
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=2)},
    tags=["lumina", "reporting", "superset"],
)
def pipeline_reporting_lumina():
    dbt_seed = BashOperator(task_id="dbt_seed", bash_command=f"{DBT} seed {OPTIONS}")
    dbt_run = BashOperator(task_id="dbt_run", bash_command=f"{DBT} run {OPTIONS}")
    dbt_test = BashOperator(task_id="dbt_test", bash_command=f"{DBT} test {OPTIONS}", outlets=[REPORTING_PRET])

    dbt_seed >> dbt_run >> dbt_test


pipeline_reporting_lumina()
