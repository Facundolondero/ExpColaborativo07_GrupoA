# -*- coding: utf-8 -*-
"""Arma resultados/hiperparametros_elegidos.csv a partir de los PARAM.yml de cada corrida, en
   corridas/<variante>/s<semilla>/ en el repositorio y en runs/<variante>/s<semilla>/ en la carpeta de trabajo:
   hiperparametros elegidos por el grid search, AUC de validacion e iteraciones del modelo final, con las marcas de
   borde de la grilla (num_leaves en 64 o 512, min_data_in_leaf en 64 o 2048) y de tope de iteraciones (2048).
   La columna `vector` marca las corridas de las 10 semillas del experimento (5 de Facundo, 5 de Francisco).

   python exp07_hiperparametros.py
"""
import pandas as pd
import yaml

from exp07_bajar_puntajes import BASE, SEMILLAS_VECTOR

RUNS = BASE / "corridas" if (BASE / "corridas").is_dir() else BASE / "runs"
SALIDA = BASE / "resultados" / "hiperparametros_elegidos.csv"
GRILLA_LEAVES = (64, 512)
GRILLA_MDL = (64, 2048)
TOPE_ITER = 2048
ORDEN = ["V0_todo", "V1_sinASPO", "V2_2021", "V3_ultimos4"]

filas = []
for param in sorted(RUNS.glob("*/s*/PARAM.yml")):
    y = yaml.safe_load(param.read_text(encoding="utf-8"))
    lgbm = y["out"]["lgbm"]
    mejores = lgbm["mejores_hiperparametros"]
    semilla = int(float(y["semilla_primigenia"]))
    nl, mdl, it = int(mejores["num_leaves"]), int(mejores["min_data_in_leaf"]), int(mejores["num_iterations"])
    filas.append({
        "variante": y["variante"], "semilla": semilla, "num_leaves": nl, "min_data_in_leaf": mdl,
        "num_iterations": it, "AUC": round(float(lgbm["AUC"]), 4), "vector": semilla in SEMILLAS_VECTOR,
        "borde_leaves": nl in GRILLA_LEAVES, "borde_mdl": mdl in GRILLA_MDL, "iter_tope": it >= TOPE_ITER,
    })

df = pd.DataFrame(filas)
df["orden"] = df["variante"].map({v: i for i, v in enumerate(ORDEN)})
df = df.sort_values(["orden", "vector", "semilla"], ascending=[True, False, True]).drop(columns="orden")
df.to_csv(SALIDA, index=False)

v = df[df["vector"]]
print(f"corridas: {len(df)} | del vector: {len(v)} ({v['semilla'].nunique()} semillas x {v['variante'].nunique()} variantes)")
faltan = [(s, var) for s in SEMILLAS_VECTOR for var in ORDEN if not ((v["semilla"] == s) & (v["variante"] == var)).any()]
print("faltan:", faltan if faltan else "ninguna")
print(f"min_data_in_leaf = 64 en {(v['min_data_in_leaf'] == 64).sum()} | num_leaves = 512 en {(v['num_leaves'] == 512).sum()} "
      f"| num_leaves = 64 en {(v['num_leaves'] == 64).sum()} | tope de iteraciones en {v['iter_tope'].sum()}")
print(v.groupby("variante")[["AUC", "num_iterations"]].agg(AUC=("AUC", "mean"), iter_mediana=("num_iterations", "median")).round(3).to_string())
print("guardado:", SALIDA)
