# Experimentos Colaborativos 2026 - Problema #07  "Utilizacion de los meses de pandemia"
# Modalidad Gerencial, Grupo A  (future = 202109)
#
# Replica paso a paso el workflow de la catedra  z610_WorkFlow_01_gerencial_grupoA.ipynb
# Entre corridas SOLO cambian:
#   - la variante  = primer mes de training (202005 = todo, como el notebook)
#   - la semilla
# Todo lo demas (CA, FE intra, FE historico, grid search, final train) es el del notebook.
# Los cortes para Kaggle son los del notebook de a 100: 800 a 1300 (6 por corrida, pedido de
# Denicolay el 29-oct; las corridas viejas de runs/ tienen ademas los archivos de 600 a 1300 de a 50).
#
# Unica diferencia deliberada (corregir_bug = TRUE): el notebook arma los parametros del
# modelo final con  c(fijos, mejores)  y eso deja num_leaves y min_data_in_leaf DUPLICADOS;
# LightGBM se queda con el PRIMER valor (64 y 128), o sea que ignora el grid search.
# Aca se usa modifyList(), que es lo que el notebook quiere hacer.
# (La version con la grilla que se amplia en los bordes quedo en version2_grilla_ampliada/.)

suppressMessages({
  require("data.table")
  require("lightgbm")
  require("yaml")
})

# ---------------------------------------------------------------------------
# 6.3.1  Preprocesamiento (es identico para todas las variantes y semillas,
#        asi que se hace una sola vez por batch)
# ---------------------------------------------------------------------------

catastrophe_analysis <- function(dataset) {
  # el notebook asigna NA a las variables que en 202006 estan todas en cero
  dataset[ foto_mes==202006, internet:=NA]
  dataset[ foto_mes==202006, mrentabilidad:=NA]
  dataset[ foto_mes==202006, mrentabilidad_annual:=NA]
  dataset[ foto_mes==202006, mcomisiones:=NA]
  dataset[ foto_mes==202006, mactivos_margen:=NA]
  dataset[ foto_mes==202006, mpasivos_margen:=NA]
  dataset[ foto_mes==202006, mcuentas_saldo:=NA]
  dataset[ foto_mes==202006, ctarjeta_visa_transacciones:=NA]
  dataset[ foto_mes==202006, mtarjeta_visa_consumo:=NA]
  dataset[ foto_mes==202006, mtarjeta_master_consumo:=NA]
  dataset[ foto_mes==202006, ccallcenter_transacciones:=NA]
  dataset[ foto_mes==202006, chomebanking_transacciones:=NA]
  invisible(dataset)
}

fe_intra_manual <- function(dataset) {
  atributos_presentes <- function(patributos) {
    atributos <- unique(patributos)
    comun <- intersect(atributos, colnames(dataset))
    return(length(atributos) == length(comun))
  }
  if (atributos_presentes(c("foto_mes")))
    dataset[, kmes := foto_mes %% 100]
  if (atributos_presentes(c("mpayroll", "cliente_edad")))
    dataset[, mpayroll_sobre_edad := mpayroll / cliente_edad]
  invisible(dataset)
}

fe_historico <- function(dataset) {
  # el notebook confia en que, dentro de cada cliente, las filas vienen en orden cronologico
  # (el csv viene ordenado por foto_mes y luego por cliente, asi que se cumple); lo verifico
  stopifnot(dataset[, all(diff(foto_mes) > 0), by = numero_de_cliente][, all(V1)])

  cols_lagueables <- copy(setdiff(
    colnames(dataset),
    c("numero_de_cliente", "foto_mes", "clase_ternaria")
  ))

  dataset[,
    paste0(cols_lagueables, "_lag1") := shift(.SD, 1, NA, "lag"),
    by = numero_de_cliente,
    .SDcols = cols_lagueables
  ]
  dataset[,
    paste0(cols_lagueables, "_lag2") := shift(.SD, 2, NA, "lag"),
    by = numero_de_cliente,
    .SDcols = cols_lagueables
  ]
  for (vcol in cols_lagueables) {
    dataset[, paste0(vcol, "_delta1") := get(vcol) - get(paste0(vcol, "_lag1"))]
    dataset[, paste0(vcol, "_delta2") := get(vcol) - get(paste0(vcol, "_lag2"))]
  }
  invisible(dataset)
}

preprocesar <- function(archivo_dataset) {
  dataset <- fread(archivo_dataset)
  catastrophe_analysis(dataset)
  fe_intra_manual(dataset)
  fe_historico(dataset)
  dataset
}

# ---------------------------------------------------------------------------
# meses de training de una variante: desde `desde` hasta 202106, en orden
# descendente como los escribe el notebook
# ---------------------------------------------------------------------------
meses_training <- function(desde, hasta = 202106) {
  todos <- c(202005, 202006, 202007, 202008, 202009, 202010, 202011, 202012,
             202101, 202102, 202103, 202104, 202105, 202106, 202107)
  rev(todos[todos >= desde & todos <= hasta])
}

# ---------------------------------------------------------------------------
# 6.3.2 + 6.3.3  Modelado y produccion para UNA (variante, semilla)
# ---------------------------------------------------------------------------
correr_experimento <- function(dataset, variante, semilla, carpeta, grupo = "A",
                               grid = CJ(num_leaves = c(64, 128, 256, 512),
                                         min_data_in_leaf = c(64, 256, 512, 1024, 2048)),
                               num_iterations = 2048, early_stopping_rounds = 200,
                               cortes = seq(800, 1300, by = 100),
                               corregir_bug = TRUE, guardar_modelo = FALSE) {

  t0 <- Sys.time()
  dir.create(carpeta, recursive = TRUE, showWarnings = FALSE)

  # Grupo A = notebook z610: valida en 202107, entrena hasta 202106, predice 202109 y sube a Kaggle
  # Grupo B = notebook z611: todo corrido dos meses atras; predice 202107, donde la clase es
  #           conocida, y calcula la ganancia localmente (no usa Kaggle)
  if (grupo == "A") {
    mes_validate <- 202107; mes_hasta <- 202106; mes_future <- 202109
  } else if (grupo == "B") {
    mes_validate <- 202105; mes_hasta <- 202104; mes_future <- 202107
  } else stop("grupo debe ser A o B")

  PARAM <- list()
  PARAM$problema <- paste0("07 - Utilizacion de los meses de pandemia (Gerencial, Grupo ", grupo, ")")
  PARAM$grupo <- grupo
  PARAM$semilla_primigenia <- semilla
  PARAM$variante <- variante$nombre
  PARAM$variante_descripcion <- variante$descripcion
  PARAM$dataset <- "gerencial_competencia_2026.csv.gz"
  PARAM$corregir_bug_c_fijos_mejores <- corregir_bug

  # --- 6.3.2.1 Training Strategy ---
  PARAM$trainingstrategy$validate <- c(mes_validate)
  PARAM$trainingstrategy$training <- meses_training(variante$desde, mes_hasta)
  PARAM$trainingstrategy$training_pct <- 1.0
  PARAM$trainingstrategy$positivos <- c("BAJA+1", "BAJA+2")

  dataset[, clase01 := ifelse(clase_ternaria %in% PARAM$trainingstrategy$positivos, 1, 0)]

  # en el notebook estas columnas auxiliares todavia no existen cuando se define
  # campos_buenos; como aca el dataset se reutiliza entre corridas, las excluyo explicitamente
  campos_buenos <- copy(setdiff(
    colnames(dataset),
    c("clase_ternaria", "clase01", "azar", "fold_train", "fold_final_train")
  ))

  set.seed(PARAM$semilla_primigenia, kind = "L'Ecuyer-CMRG")
  dataset[, azar := runif(nrow(dataset))]

  dataset[, fold_train := foto_mes %in% PARAM$trainingstrategy$training &
    (clase_ternaria %in% c("BAJA+1", "BAJA+2") |
     azar < PARAM$trainingstrategy$training_pct)]

  dtrain <- lgb.Dataset(
    data = data.matrix(dataset[fold_train == TRUE, campos_buenos, with = FALSE]),
    label = dataset[fold_train == TRUE, clase01],
    free_raw_data = TRUE
  )
  dvalidate <- lgb.Dataset(
    data = data.matrix(dataset[foto_mes %in% PARAM$trainingstrategy$validate, campos_buenos, with = FALSE]),
    label = dataset[foto_mes %in% PARAM$trainingstrategy$validate, clase01],
    free_raw_data = TRUE
  )

  PARAM$out$n_train <- dataset[fold_train == TRUE, .N]
  PARAM$out$pos_train <- dataset[fold_train == TRUE, sum(clase01)]
  PARAM$out$baja2_train <- dataset[fold_train == TRUE, sum(clase_ternaria == "BAJA+2")]

  # --- 6.3.2.2 Hyperparameter Tuning (grid search, identico al notebook) ---
  PARAM$lgbm$param_fijos <- list(
    objective = "binary",
    metric = "auc",
    first_metric_only = TRUE,
    boost_from_average = TRUE,
    feature_pre_filter = FALSE,
    verbosity = -100,
    force_row_wise = TRUE,
    seed = PARAM$semilla_primigenia,
    max_bin = 31,
    learning_rate = 0.03,
    feature_fraction = 0.5,
    num_iterations = num_iterations,
    early_stopping_rounds = early_stopping_rounds,
    num_leaves = 64,
    min_data_in_leaf = 128
  )

  Estimar_AUC_lightgbm <- function(x) {
    param_completo <- modifyList(PARAM$lgbm$param_fijos, x)
    modelo_train <- lgb.train(
      data = dtrain,
      valids = list(valid = dvalidate),
      eval = "auc",
      param = param_completo,
      verbose = -100
    )
    AUC <- modelo_train$record_evals$valid$auc$eval[[modelo_train$best_iter]]
    niter <- modelo_train$best_iter
    message(format(Sys.time(), "%a %b %d %X %Y  "), variante$nombre, " s", semilla, "  ",
            toString(x), " niter ", niter, " AUC ", AUC)
    rm(modelo_train)
    gc(full = TRUE, verbose = FALSE)
    return(list(AUC, niter))
  }

  tb_nueva <- copy(grid)
  tb_nueva[, c("AUC", "num_iterations") := Estimar_AUC_lightgbm(as.list(.SD)),
           by = 1:nrow(tb_nueva)]
  tb_nueva[, `:=`(variante = variante$nombre, semilla = semilla)]
  fwrite(tb_nueva, file = file.path(carpeta, "tb_grid_search.txt"), sep = "\t")

  setorder(tb_nueva, -AUC)
  PARAM$out$lgbm$AUC <- tb_nueva[1, AUC]
  PARAM$out$lgbm$mejores_hiperparametros <- as.list(tb_nueva[1, list(num_leaves, min_data_in_leaf, num_iterations)])

  # --- 6.3.3 Produccion: Final Training ---
  PARAM$trainingstrategy$final_train <- c(mes_validate, PARAM$trainingstrategy$training)
  dataset[, fold_final_train := foto_mes %in% PARAM$trainingstrategy$final_train]

  dfinal_train <- lgb.Dataset(
    data = data.matrix(dataset[fold_final_train == TRUE, campos_buenos, with = FALSE]),
    label = dataset[fold_final_train == TRUE, clase01],
    free_raw_data = TRUE
  )
  PARAM$out$n_final_train <- dataset[fold_final_train == TRUE, .N]

  fijos <- copy(PARAM$lgbm$param_fijos)
  fijos$num_iterations <- NULL
  fijos$early_stopping_rounds <- NULL

  if (corregir_bug) {
    param_final <- modifyList(fijos, PARAM$out$lgbm$mejores_hiperparametros)
  } else {
    param_final <- c(fijos, PARAM$out$lgbm$mejores_hiperparametros)  # tal cual el notebook
  }
  PARAM$out$param_final <- param_final

  final_model <- lgb.train(data = dfinal_train, param = param_final, verbose = -100)
  if (guardar_modelo) lgb.save(final_model, file.path(carpeta, "modelo.txt"))

  tb_importancia <- as.data.table(lgb.importance(final_model))
  fwrite(tb_importancia, file = file.path(carpeta, "impo.txt"), sep = "\t")

  # --- Scoring del futuro ---
  PARAM$trainingstrategy$future <- c(mes_future)
  dfuture <- dataset[foto_mes %in% PARAM$trainingstrategy$future]
  prediccion <- predict(final_model, data.matrix(dfuture[, campos_buenos, with = FALSE]))

  tb_prediccion <- dfuture[, list(numero_de_cliente)]
  tb_prediccion[, prob := prediccion]
  fwrite(tb_prediccion, file = file.path(carpeta, "prediccion.txt"), sep = "\t")

  # los cortes en los que el Grupo A sube a Kaggle (`cortes`: los del notebook de a 100, de 800 a 1300);
  # el Grupo B mide la ganancia en los mismos cortes para poner las curvas una al lado de la otra.
  extra <- list()

  if (grupo == "A") {
    # --- Archivos para Kaggle (NO se suben desde aca) ---
    PARAM$kaggle$competencia <- "labo-1-virtual-2026-manager"
    PARAM$kaggle$cortes <- cortes
    setorder(tb_prediccion, -prob)
    dir.create(file.path(carpeta, "kaggle"), showWarnings = FALSE)
    for (envios in PARAM$kaggle$cortes) {
      tb_prediccion[, Predicted := 0L]
      tb_prediccion[1:envios, Predicted := 1L]
      fwrite(tb_prediccion[, list(numero_de_cliente, Predicted)],
             file = file.path(carpeta, "kaggle",
                              paste0("KA07_", variante$nombre, "_s", semilla, "_", envios, ".csv")),
             sep = ",")
    }
  } else {
    # --- Curva de Ganancia (bloque del z611): en 202107 la clase es conocida ---
    tb_prediccion[, clase_ternaria := dfuture$clase_ternaria]
    tb_prediccion[, ganancia := -0.025]
    tb_prediccion[clase_ternaria == "BAJA+2", ganancia := 0.975]
    setorder(tb_prediccion, -prob)
    tb_prediccion[, gan_acum := cumsum(ganancia)]
    # (el z611 pasa hasNA = TRUE; en data.table 1.18 esta obsoleto y lo detecta solo)
    tb_prediccion[, gan_suavizada := frollmean(x = gan_acum, n = 400, align = "center", na.rm = TRUE)]
    resultado <- list()
    resultado$ganancia_suavizada_max <- max(tb_prediccion$gan_suavizada, na.rm = TRUE)
    resultado$envios <- which.max(tb_prediccion$gan_suavizada)
    resultado$ganancia_cruda_max <- max(tb_prediccion$gan_acum)
    resultado$envios_cruda <- which.max(tb_prediccion$gan_acum)
    resultado$baja2_en_future <- tb_prediccion[, sum(clase_ternaria == "BAJA+2")]
    fwrite(tb_prediccion, file = file.path(carpeta, "ganancias.txt"), sep = "\t")

    tb_prediccion[, envios := .I]
    pdf(file.path(carpeta, "curva_de_ganancia.pdf"))
    plot(x = tb_prediccion$envios, y = tb_prediccion$gan_acum, type = "l", col = "gray",
         xlim = c(0, 3000), ylim = c(0, max(30, resultado$ganancia_cruda_max)),
         main = paste0(variante$nombre, " s", semilla, "  mejor gan prom= ",
                       round(resultado$ganancia_suavizada_max, 2), " envios= ", resultado$envios),
         xlab = "Envios", ylab = "Ganancia", panel.first = grid())
    lines(x = tb_prediccion$envios, y = tb_prediccion$gan_suavizada, col = "red")
    dev.off()

    PARAM$resultado <- resultado
    extra <- c(list(ganancia_max_suav = round(resultado$ganancia_suavizada_max, 4),
                    envios_optimo = resultado$envios,
                    ganancia_max_cruda = round(resultado$ganancia_cruda_max, 4),
                    envios_optimo_crudo = resultado$envios_cruda),
               setNames(as.list(round(tb_prediccion$gan_acum[cortes], 4)), paste0("gan_", cortes)))
  }

  PARAM$out$minutos <- round(as.numeric(difftime(Sys.time(), t0, units = "mins")), 2)
  write_yaml(PARAM, file.path(carpeta, "PARAM.yml"))

  rm(dtrain, dvalidate, dfinal_train, final_model)
  gc(full = TRUE, verbose = FALSE)

  # mismas 12 columnas de siempre para el A (resultados_grid.csv se va llenando por append);
  # el B agrega al final las columnas de ganancia
  as.data.table(c(list(
    variante = variante$nombre, desde = variante$desde, semilla = semilla,
    n_train = PARAM$out$n_train, pos_train = PARAM$out$pos_train, baja2_train = PARAM$out$baja2_train,
    n_final_train = PARAM$out$n_final_train,
    AUC_valid = PARAM$out$lgbm$AUC,
    num_leaves = PARAM$out$lgbm$mejores_hiperparametros$num_leaves,
    min_data_in_leaf = PARAM$out$lgbm$mejores_hiperparametros$min_data_in_leaf,
    num_iterations = PARAM$out$lgbm$mejores_hiperparametros$num_iterations,
    minutos = PARAM$out$minutos
  ), extra))
}
