"""Baja de Kaggle los puntajes de los envios del Experimento 07 y arma las tablas por variante.

  python exp07_bajar_puntajes.py                 baja la lista de envios y resume
  python exp07_bajar_puntajes.py --solo-resumen  no toca Kaggle; resume lo que ya hay en puntajes_kaggle_*.csv

Se usan solo los 6 cortes del notebook de a 100, de 800 a 1300, y un recorte es mejor que V0 si el test de Wilcoxon
pareado por semilla da p < 0,05 a su favor. Este resumen rapido mide cada corrida con el promedio Public de los 6
cortes; el analisis final, con el maximo Public (criterio de la catedra) y el promedio como chequeo, esta en
exp07_resultados.py.

Salidas (en puntajes/ dentro del repositorio; en la carpeta del script si no hay puntajes/):
  puntajes_kaggle_<usuario>.csv     un renglon por envio del experimento: variante, semilla, envios, public, fecha
  puntajes_resumen_cortes.csv       por variante y corte: n semillas, media, desvio, min, max
  puntajes_corridas.csv             por corrida: cortes puntuados y ganancia (promedio de los 6 cortes)
  puntajes_resumen_variantes.csv    por variante: ganancia media, diferencia pareada contra V0, semillas que
                                    superan a V0, p de Wilcoxon y veredicto

Si el companero sube desde su cuenta, corre este mismo script en su PC y manda su
puntajes_kaggle_<usuario>.csv; al copiarlo junto al propio el resumen junta los dos.
Si un mismo archivo se subio dos veces, se queda con el envio mas reciente.
Solo entran las semillas de SEMILLAS_VECTOR (5 de Facundo + 5 de Francisco); las demas corridas quedan afuera.
"""
import argparse
import json
import re
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
# En el repositorio los scripts estan en scripts/ y los datos un nivel arriba; en la carpeta de trabajo, todo junto.
BASE = AQUI.parent if AQUI.name == "scripts" else AQUI
CARPETA_PUNTAJES = BASE / "puntajes" if (BASE / "puntajes").is_dir() else BASE
COMPETENCIA = "labo-1-virtual-2026-manager"
ORDEN_VARIANTES = ["V0_todo", "V1_sinASPO", "V2_2021", "V3_ultimos4"]
PRIMER_MES = {"V0_todo": 202005, "V1_sinASPO": 202011, "V2_2021": 202101, "V3_ultimos4": 202103}
CORTES = list(range(800, 1301, 100))
# vector de semillas del experimento: las 5 primigenias de Facundo + las 5 de Francisco.
# Lo que no esta en el vector (por ejemplo las otras 5 semillas de Facundo, que tambien corrieron) no entra en el resumen.
SEMILLAS_FACUNDO = [150001, 222247, 199999, 777781, 999983]
SEMILLAS_FRANCISCO = [101929, 232327, 456791, 454451, 123457]   # las 5 primigenias de Francisco (archivo del 02-nov)
SEMILLAS_VECTOR = SEMILLAS_FACUNDO + SEMILLAS_FRANCISCO
PATRON = re.compile(r"KA07_(?P<variante>.+)_s(?P<semilla>\d+)_(?P<envios>\d+)\.csv$")
PATRON_MSG = re.compile(r"exp07 (?P<variante>\S+) s(?P<semilla>\d+) envios=(?P<envios>\d+)")


def usuario_kaggle():
    try:
        return json.load(open(Path.home() / ".kaggle" / "kaggle.json"))["username"]
    except Exception:  # noqa: BLE001
        return "desconocido"


def bajar_envios():
    """Todos los envios de la competencia, siguiendo el token de pagina de la API."""
    from kaggle.api.kaggle_api_extended import KaggleApi
    from kagglesdk.competitions.types.competition_api_service import ApiListSubmissionsRequest
    from kagglesdk.competitions.types.competition_enums import SubmissionGroup, SubmissionSortBy

    api = KaggleApi()
    api.authenticate()
    envios, token, paginas = [], "", 0
    while True:
        with api.build_kaggle_client() as kaggle:
            req = ApiListSubmissionsRequest()
            req.competition_name = COMPETENCIA
            req.group = SubmissionGroup.SUBMISSION_GROUP_ALL
            req.sort_by = SubmissionSortBy.SUBMISSION_SORT_BY_DATE
            api._set_paging(req, 200, token, -1)
            resp = kaggle.competitions.competition_api_client.list_submissions(req)
        subs = resp.submissions or []
        envios.extend(subs)
        paginas += 1
        token = getattr(resp, "next_page_token", "") or ""
        if not token or not subs or paginas > 50:
            break
    return envios


def filtrar_experimento(envios):
    filas = []
    for s in envios:
        m = PATRON.match(s.file_name or "") or PATRON_MSG.search(s.description or "")
        if not m:
            continue
        if "COMPLETE" not in str(s.status) or s.public_score in (None, ""):
            continue
        filas.append({"variante": m["variante"], "semilla": int(m["semilla"]), "envios": int(m["envios"]),
                      "public": float(s.public_score), "fecha": str(s.date), "ref": s.ref,
                      "archivo": s.file_name})
    df = pd.DataFrame(filas, columns=["variante", "semilla", "envios", "public", "fecha", "ref", "archivo"])
    # si un archivo se subio mas de una vez, me quedo con el mas reciente
    return (df.sort_values("fecha")
              .drop_duplicates(["variante", "semilla", "envios"], keep="last")
              .sort_values(["variante", "semilla", "envios"])
              .reset_index(drop=True))


def wilcoxon_p(dif):
    """p a dos colas del test de Wilcoxon de rangos con signo (exacto si scipy lo permite)."""
    from scipy.stats import wilcoxon
    try:
        return float(wilcoxon(dif, method="exact").pvalue)
    except (TypeError, ValueError):
        return float(wilcoxon(dif).pvalue)


def resumir():
    archivos = sorted(a for a in CARPETA_PUNTAJES.glob("puntajes_kaggle_*.csv") if not a.name.startswith("puntajes_kaggle_v2_"))
    if not archivos:
        print("No hay archivos puntajes_kaggle_*.csv todavia.")
        return
    df = pd.concat([pd.read_csv(a) for a in archivos], ignore_index=True)
    df = (df.sort_values("fecha").drop_duplicates(["variante", "semilla", "envios"], keep="last"))
    df = df[df["envios"].isin(CORTES)]   # los cortes que no son de los 6 quedan afuera
    df = df[df["semilla"].isin(SEMILLAS_VECTOR)]   # solo las semillas del vector del experimento
    df["variante"] = pd.Categorical(df["variante"], categories=ORDEN_VARIANTES, ordered=True)

    # por variante y corte
    cortes = (df.groupby(["variante", "envios"], observed=True)["public"]
                .agg(n="count", media="mean", desvio="std", minimo="min", maximo="max")
                .round(3).reset_index())
    cortes.to_csv(CARPETA_PUNTAJES / "puntajes_resumen_cortes.csv", index=False)

    # por corrida: la ganancia es el promedio de los 6 cortes; solo entran las corridas con los 6 puntuados
    corridas = (df.groupby(["variante", "semilla"], observed=True)["public"]
                  .agg(cortes="count", ganancia="mean").reset_index())
    corridas.to_csv(CARPETA_PUNTAJES / "puntajes_corridas.csv", index=False)
    completas = corridas[corridas["cortes"] == len(CORTES)]

    # por variante, con comparacion pareada contra V0 (misma semilla)
    base = completas[completas["variante"] == "V0_todo"].set_index("semilla")["ganancia"]
    filas = []
    for v in ORDEN_VARIANTES:
        c = completas[completas["variante"] == v]
        if c.empty:
            continue
        fila = {"variante": v, "n_semillas": len(c), "ganancia_media": round(c["ganancia"].mean(), 3),
                "desvio_entre_semillas": round(c["ganancia"].std(), 3) if len(c) > 1 else None}
        if v != "V0_todo":
            pares = c.set_index("semilla")["ganancia"].to_frame("v").join(base.to_frame("v0"), how="inner")
            dif = pares["v"] - pares["v0"]
            fila.update({"n_pares_vs_V0": len(pares),
                         "dif_media_vs_V0": round(dif.mean(), 3) if len(pares) else None,
                         "semillas_que_superan_V0": int((dif > 0).sum())})
            if len(pares) >= 5 and (dif != 0).any():
                fila["wilcoxon_p"] = round(wilcoxon_p(dif), 4)
            # regla fijada antes de ver resultados: un recorte es mejor que V0 si el Wilcoxon da p < 0,05 a su favor
            if len(pares) < 10:
                fila["veredicto"] = f"faltan semillas ({len(pares)} de 10)"
            else:
                gana = fila.get("wilcoxon_p", 1) < 0.05 and fila["dif_media_vs_V0"] > 0
                fila["veredicto"] = "gana" if gana else "no gana"
        filas.append(fila)
    variantes = pd.DataFrame(filas)
    variantes.to_csv(CARPETA_PUNTAJES / "puntajes_resumen_variantes.csv", index=False)

    pd.set_option("display.width", 160)
    print(f"\nEnvios de los 6 cortes con puntaje: {len(df)}  (archivos: {', '.join(a.name for a in archivos)})")
    estado = "completo" if len(SEMILLAS_VECTOR) >= 10 else "provisorio, faltan las semillas de Francisco"
    print(f"Semillas del vector: {len(SEMILLAS_VECTOR)} de 10 ({estado})")
    print("\nGanancia Public media por corte (filas) y variante (columnas):")
    print(cortes.pivot(index="envios", columns="variante", values="media").round(1).to_string())
    print("\nPor variante (ganancia = promedio de los 6 cortes de cada corrida):")
    print(variantes.to_string(index=False))

    # recomendacion concreta: desde que mes entrenar en la z719
    recortes = variantes[variantes["variante"] != "V0_todo"]
    if len(recortes) == 3 and (recortes["n_pares_vs_V0"] >= 10).all():
        ganadoras = recortes[recortes["veredicto"] == "gana"]
        if len(ganadoras):
            mejor = ganadoras.loc[ganadoras["dif_media_vs_V0"].idxmax(), "variante"]
            print(f"\nRecomendacion: entrenar desde {PRIMER_MES[mejor]} ({mejor})")
        else:
            print("\nRecomendacion: ningun recorte cumple la regla, entrenar con todos los meses desde 202005")
    else:
        print("\nLa recomendacion sale cuando las tres comparaciones tengan las 10 semillas.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--solo-resumen", action="store_true", help="no consulta Kaggle, solo resume los csv locales")
    args = ap.parse_args()
    if not args.solo_resumen:
        envios = bajar_envios()
        df = filtrar_experimento(envios)
        salida = CARPETA_PUNTAJES / f"puntajes_kaggle_{usuario_kaggle()}.csv"
        df.to_csv(salida, index=False)
        print(f"Kaggle: {len(envios)} envios en la competencia, {len(df)} del experimento -> {salida.name}")
    resumir()


if __name__ == "__main__":
    main()
