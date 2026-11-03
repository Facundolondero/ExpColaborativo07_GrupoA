# Experimentos Colaborativos 2026 - Problema #07 "Utilizacion de los meses de pandemia" (Gerencial)
# Corre todas las combinaciones  variante x semilla  del workflow de la catedra, en secuencia.
#
#   Rscript exp07_batch.R full A     -> Grupo A: 4 variantes x 10 semillas, deja los csv para Kaggle (carpeta runs/)
#   Rscript exp07_batch.R full B     -> Grupo B: 5 variantes x 10 semillas, calcula la ganancia en 202107 (runs_B/)
#   Rscript exp07_batch.R test A     -> prueba corta de punta a punta (runs_test/), idem  test B  (runs_test_B/)
#
# Es reanudable: si una corrida ya tiene su PARAM.yml, la saltea. Se puede cortar y relanzar.
# No sube nada a Kaggle. Si falta el dataset, lo descarga.
# Cada corrida del A deja 6 csv para Kaggle, los cortes del notebook de a 100 (800 a 1300).
# Resumen: una fila por corrida en resultados_grid.csv (A) o resultados_grid_B.csv (B).

args <- commandArgs(trailingOnly = TRUE)
modo  <- if (length(args) >= 1) args[1] else "full"              # full | test
grupo <- if (length(args) >= 2) toupper(args[2]) else "A"        # A | B
stopifnot(modo %in% c("full", "test"), grupo %in% c("A", "B"))

# carpeta base = la carpeta donde esta este script (asi corre igual en cualquier PC o en Colab)
arg_file <- grep("^--file=", commandArgs(), value = TRUE)
base <- if (length(arg_file)) dirname(normalizePath(sub("^--file=", "", arg_file[1]))) else getwd()
setwd(base)
source("exp07_lib.R")

# ---- dataset ----
archivo_dataset <- "datasets/gerencial_competencia_2026.csv.gz"
if (!file.exists(archivo_dataset)) {
  dir.create("datasets", showWarnings = FALSE)
  download.file("https://storage.googleapis.com/open-courses/austral2026-5da5/labo1/gerencial_competencia_2026.csv.gz",
                archivo_dataset, mode = "wb")
}

# ---- diseno experimental ----
# Lo unico que cambia entre variantes es el primer mes de training.
# Grupo A: validation = 202107, final_train = training + 202107, future = 202109 (Kaggle).
variantes_A <- list(
  list(nombre = "V0_todo",     desde = 202005,
       descripcion = "linea base de la catedra: todos los meses, incluye el ASPO (202005-202106)"),
  list(nombre = "V1_sinASPO",  desde = 202011,
       descripcion = "sin los meses de ASPO: desde noviembre 2020, cuando AMBA pasa a DISPO (202011-202106)"),
  list(nombre = "V2_2021",     desde = 202101,
       descripcion = "solo 2021, desde el inicio de la vacunacion (202101-202106)"),
  list(nombre = "V3_ultimos4", desde = 202103,
       descripcion = "solo los ultimos 4 meses de training (202103-202106)")
)
# Grupo B: todo corrido dos meses atras: validation = 202105, final_train = training + 202105,
# future = 202107 (clase conocida, ganancia calculada localmente). Como las ventanas quedan mas
# cortas, en vez de 4 variantes se barre el mes de inicio de a dos meses: si la ganancia cambia
# de a poco es efecto de la cantidad de datos; si salta al sacar el ASPO, es efecto de la pandemia.
variantes_B <- list(
  list(nombre = "B_desde202005", desde = 202005, descripcion = "todos los meses, incluye el ASPO (202005-202104, 12 meses)"),
  list(nombre = "B_desde202007", desde = 202007, descripcion = "desde julio 2020 (202007-202104, 10 meses)"),
  list(nombre = "B_desde202009", desde = 202009, descripcion = "desde septiembre 2020 (202009-202104, 8 meses)"),
  list(nombre = "B_desde202011", desde = 202011, descripcion = "sin ASPO: desde noviembre 2020 (202011-202104, 6 meses)"),
  list(nombre = "B_desde202101", desde = 202101, descripcion = "solo 2021 (202101-202104, 4 meses)")
)
variantes <- if (grupo == "A") variantes_A else variantes_B

# 10 semillas primas: 553897 (la usada en toda la materia), 4 generadas en la Tarea Hogar 02 y las 5 del
# CheckIn de Facundo. Van en este orden; cada semilla corre las 4 variantes antes de pasar a la siguiente.
# (El Grupo B reemplaza este vector por sus propias semillas; ver README_grupoB.txt)
semillas <- c(553897, 761897, 815197, 906187, 919531,
              150001, 222247, 199999, 777781, 999983)

sufijo <- if (grupo == "A") "" else "_B"
if (modo == "test") {
  carpeta_runs <- paste0("runs_test", sufijo)
  archivo_resumen <- paste0("resultados_test", sufijo, ".csv")
  variantes <- variantes[c(1, length(variantes))]
  semillas <- semillas[1]
  grid <- CJ(num_leaves = c(64, 512), min_data_in_leaf = c(128))
  num_iterations <- 60
  early_stopping_rounds <- 20
} else {
  carpeta_runs <- paste0("runs", sufijo)
  archivo_resumen <- paste0("resultados_grid", sufijo, ".csv")
  grid <- CJ(num_leaves = c(64, 128, 256, 512),
             min_data_in_leaf = c(64, 256, 512, 1024, 2048))
  num_iterations <- 2048
  early_stopping_rounds <- 200
}

message(format(Sys.time(), "%a %b %d %X %Y"), "  modo=", modo, "  grupo=", grupo, "  inicio del batch")
t0 <- Sys.time()

dataset <- preprocesar(archivo_dataset)
message(format(Sys.time(), "%a %b %d %X %Y"), "  preprocesado: ",
        nrow(dataset), " filas x ", ncol(dataset), " columnas")

# semilla afuera, variante adentro: asi todas las variantes quedan comparables desde la primera semilla
for (semilla in semillas) {
  for (variante in variantes) {
    carpeta <- file.path(carpeta_runs, variante$nombre, paste0("s", semilla))
    if (file.exists(file.path(carpeta, "PARAM.yml"))) {
      message("  ya corrida, salteo: ", carpeta)
      next
    }
    message(format(Sys.time(), "%a %b %d %X %Y"), "  === ", variante$nombre, "  semilla ", semilla,
            "  training desde ", variante$desde, " ===")
    fila <- correr_experimento(
      dataset, variante, semilla, carpeta, grupo = grupo,
      grid = grid, num_iterations = num_iterations,
      early_stopping_rounds = early_stopping_rounds
    )
    fwrite(fila, file = archivo_resumen, sep = ",", append = file.exists(archivo_resumen))
    message(format(Sys.time(), "%a %b %d %X %Y"), "  fin ", variante$nombre, " s", semilla,
            "  AUC ", round(fila$AUC_valid, 5), "  mejores nl=", fila$num_leaves,
            " mdil=", fila$min_data_in_leaf, " niter=", fila$num_iterations,
            if (grupo == "B") paste0("  ganancia max ", fila$ganancia_max_suav, " en ", fila$envios_optimo, " envios") else "",
            "  (", fila$minutos, " min)")
  }
}

message(format(Sys.time(), "%a %b %d %X %Y"), "  batch terminado en ",
        round(as.numeric(difftime(Sys.time(), t0, units = "mins")), 1), " min")
