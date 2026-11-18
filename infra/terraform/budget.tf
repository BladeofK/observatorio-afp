# BLINDAJE · capa 6: presupuesto con alertas por correo (a los administradores de
# facturación) y publicación en Pub/Sub, que activa el corte automático (capa 7).
# Recuerda: un presupuesto por sí solo NO detiene el gasto.

resource "google_pubsub_topic" "alertas_presupuesto" {
  name       = "alertas-presupuesto"
  depends_on = [google_project_service.apis]
}

resource "google_billing_budget" "presupuesto" {
  billing_account = var.cuenta_facturacion
  display_name    = "observatorio-afp-tope"

  budget_filter {
    projects = ["projects/${data.google_project.este.number}"]
  }

  amount {
    specified_amount {
      currency_code = var.moneda
      units         = tostring(var.monto_presupuesto)
    }
  }

  dynamic "threshold_rules" {
    for_each = [0.25, 0.5, 0.9, 1.0]
    content {
      threshold_percent = threshold_rules.value
    }
  }

  all_updates_rule {
    pubsub_topic                   = google_pubsub_topic.alertas_presupuesto.id
    schema_version                 = "1.0"
    disable_default_iam_recipients = false
  }

  depends_on = [google_project_service.apis]
}
