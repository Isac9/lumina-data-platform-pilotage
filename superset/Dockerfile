FROM apache/superset:4.1.1

# L'image officielle ne contient pas le "pilote" pour parler à PostgreSQL : on l'ajoute.
USER root
RUN pip install --no-cache-dir psycopg2-binary==2.9.10
USER superset
