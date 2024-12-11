-----------------------------------------------------------------------
-- /* Se crea el campo geom para las tablas provenientes del IDE */ --
-----------------------------------------------------------------------

/* 1. Centros de Acuicultura */

-- Se crea una nueva columna

ALTER TABLE entradas.concesiones_acuicultura
ADD COLUMN geom geometry(Geometry, 4326);

-- Se pobla la nueva columna con la geometria basada en el campo 'geometry'

UPDATE entradas.concesiones_acuicultura
SET geom = ST_PolygonFromText(geometry, 4326);

-- Se elimina la columna que contiene la geometria como texto

ALTER TABLE entradas.conc
