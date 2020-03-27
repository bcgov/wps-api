-- TABLE

CREATE SEQUENCE temperature_rid_seq;

CREATE TABLE wps.temperature
(
    rid integer NOT NULL DEFAULT nextval('temperature_rid_seq'::regclass),
    rast raster,
    filename text COLLATE pg_catalog."default",
    CONSTRAINT temperature_pkey PRIMARY KEY (rid)
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;

ALTER TABLE wps.temperature
    OWNER to wps;
