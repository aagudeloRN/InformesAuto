"""Parsers puros de las fuentes del directorio local (DT-050).

Transforman filas crudas (dicts que entrega el wrapper ``infrastructure/sources/excel_reader``) en
DTOs estructurales, **sin BD ni políticas de estado/fuente** (esas las aplica el script de siembra
con las constantes canónicas de ``data/models/entidad``). Deterministas y testeables con fixtures.
"""
