FROM postgres:16

COPY ./src/schema/schema.sql /docker-entrypoint-initdb.d/01-schema.sql
COPY ./src/schema/data.sql /docker-entrypoint-initdb.d/02-data.sql

EXPOSE 5432