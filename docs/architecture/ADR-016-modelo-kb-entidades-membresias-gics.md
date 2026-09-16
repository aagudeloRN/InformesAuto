# ADR-016: Modelo de Knowledge Base de Entidades y Membresías Sectoriales GICS

## Estado
Aceptado

## Fecha
2026-09-16

## Contexto
El sistema de Inteligencia Competitiva requiere identificar, catalogar y enriquecer competidores y aliados estratégicos en múltiples niveles geográficos (globales, regionales, locales/startups). Anteriormente, las entidades estaban vinculadas a un único sector GICS de forma plana o dependían de strings dispersos, lo que impedía que una empresa multisectorial o conglomerado perteneciera a múltiples cadenas de valor y dificultaba la deduplicación por NIT y normalización canónica de nombres.

## Decisión
Se establece un modelo canónico de Knowledge Base en PostgreSQL estructurado en:
1. **entidades**: Registro maestro de la entidad (id, nombre, nombre_normalizado, nit, pais, segmento [competidor, startup, aliado], estado [candidato, verificado, descartado], fuente, updated_at).
2. **entidad_sectores**: Membresías sectoriales N:M que relacionan una entidad con un grupo GICS (sector_gics), especificando sub_gics, lcance (global, regional, local) y 
elevancia_score.
3. **entidad_atributos**: Pares clave-valor EAV versionados para atributos específicos (portafolio, propuesta_valor, ingresos, empleados, diferenciadores, etc.).

## Consecuencias
- **Positivas**:
  - Soporte nativo para empresas presentes en múltiples sectores sin duplicar el registro canónico.
  - Trazabilidad y gobernanza de curación (estados: candidato vs. verificado).
  - Consultas vectoriales y de emparejamiento semántico desacopladas de la persistencia de atributos.
- **Negativas**:
  - Requiere queries con joins para obtener fichas completas, mitigado con repositorios y vistas especializadas en EntidadRepository.
