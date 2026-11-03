# Experimento Colaborativo #07: Utilización de los meses de pandemia

Laboratorio de Implementación I, Universidad Austral, 2026. Modalidad Gerencial, Grupo A: Facundo Londero y
Francisco Medina Raed. Grupo B: Gabriela Armoa.

## Qué se hizo

Se corrió el workflow z610 de la cátedra tal cual, cambiando solamente el primer mes de entrenamiento:

| Variante | Primer mes | Meses de training |
|---|---|---|
| V0 todos los meses (línea base) | 202005 | 14 |
| V1 sin ASPO | 202011 | 8 |
| V2 solo 2021 | 202101 | 6 |
| V3 últimos cuatro meses | 202103 | 4 |

Validación en 202107, entrenamiento final hasta 202107 y predicción de 202109 (Kaggle). Cada variante se corrió con
las mismas 10 semillas (5 de cada integrante) y en cada corrida se repitió el grid search completo. Por corrida se
subieron a Kaggle los 6 cortes del notebook (800 a 1.300 envíos de a 100): 240 envíos en total.

Único cambio al notebook, igual en las cuatro variantes: el modelo final usa `modifyList(fijos, mejores)` en vez de
`c(fijos, mejores)`, porque con `c()` LightGBM ignora lo que eligió el grid search.

La ganancia de cada corrida es el máximo del Public entre los 6 cortes (criterio de la cátedra para Kaggle); el
promedio de los 6 cortes, que era la métrica del diseño original, queda como chequeo. Cada recorte se compara con V0
de a pares por semilla con el test de Wilcoxon de rangos con signo; la regla, fijada antes de ver resultados, es que
un recorte es mejor que V0 si p < 0,05 a su favor. Además se reportan las 6 comparaciones entre variantes con
corrección de Holm.

## Resultado

| Variante | Ganancia media (máximo Public) | Diferencia vs V0 | Semillas que superan a V0 | p Wilcoxon |
|---|---|---|---|---|
| V0 todos los meses | 20,0 | | | |
| V1 sin ASPO | 21,6 | +1,7 | 7 de 10 | 0,131 |
| V2 solo 2021 | 24,5 | +4,5 | 8 de 10 | 0,014 |
| V3 últimos cuatro meses | 25,0 | +5,1 | 10 de 10 | 0,002 |

Recomendación: entrenar el modelo final de la z719 desde 202103 (meses 202103 a 202107). Detalle en
`resultados/resumen.txt` y en las filminas.

## Qué hay en cada carpeta

- `scripts/`: `exp07_lib.R` y `exp07_batch.R` (las corridas en una PC con R), `exp07_grupoA_colab.ipynb` (lo mismo
  en Colab, kernel R; la copia `_Francisco` ya viene en modo full), `exp07_subir.py` y `exp07_vigilar.py` (subidas a
  Kaggle respetando el cupo diario), `exp07_bajar_puntajes.py` (baja los puntajes de Kaggle; ahí está el vector de
  semillas), `exp07_resultados.py` (tablas, gráficos y tests) y `scripts/slides/` (las filminas).
- `puntajes/`: los puntajes Public de cada envío, por integrante.
- `resultados/`: tablas por semilla y variante, por corte, comparaciones contra V0, todos contra todos con Holm,
  chequeo con el promedio, hiperparámetros elegidos por el grid en cada corrida, gráficos y `resumen.txt`.
- `corridas/<variante>/s<semilla>/`: de cada corrida, `PARAM.yml` (configuración, hiperparámetros elegidos, AUC de
  validación), `tb_grid_search.txt` (las 20 combinaciones del grid con su AUC y sus iteraciones) e `impo.txt`
  (importancia de variables). Los archivos de predicción no se suben por tamaño.
- `filminas/`: las filminas del experimento en PDF.

## Cómo replicar

1. Instalar R con `data.table`, `lightgbm`, `yaml` y `R.utils`.
2. `Rscript scripts/exp07_batch.R full A` corre las 40 corridas (descarga el dataset si falta). Para probar en dos
   minutos: `Rscript scripts/exp07_batch.R test A`.
3. `python scripts/exp07_subir.py --subir` sube los 6 cortes de cada corrida a Kaggle (hace falta `kaggle.json`);
   `python scripts/exp07_vigilar.py` lo hace solo a medida que terminan las corridas, respetando los 100 envíos por día.
4. `python scripts/exp07_bajar_puntajes.py` baja los puntajes y `python scripts/exp07_resultados.py` arma las tablas,
   los gráficos y los tests en `resultados/`.

En Colab alcanza con subir `scripts/exp07_grupoA_colab.ipynb` (entorno de ejecución R) y correr las celdas en orden.
