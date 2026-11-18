"""Desvincula la facturación del proyecto cuando el gasto alcanza el presupuesto.

Recibe las notificaciones del presupuesto vía Pub/Sub. Cada mensaje trae, entre otros,
`costAmount` (gasto acumulado del mes) y `budgetAmount` (monto del presupuesto).
"""

import base64
import json
import os

import functions_framework
from google.cloud import billing_v1

PROYECTO_ID = os.environ["PROYECTO_ID"]


@functions_framework.cloud_event
def cortar_facturacion(cloud_event):
    mensaje = base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
    datos = json.loads(mensaje)
    costo = float(datos.get("costAmount", 0))
    presupuesto = float(datos.get("budgetAmount", 0))

    if presupuesto <= 0 or costo < presupuesto:
        print(f"Gasto {costo} bajo el presupuesto {presupuesto}. Sin acción.")
        return

    cliente = billing_v1.CloudBillingClient()
    nombre = f"projects/{PROYECTO_ID}"
    info = cliente.get_project_billing_info(name=nombre)
    if not info.billing_enabled:
        print("La facturación ya estaba desvinculada.")
        return

    cliente.update_project_billing_info(
        name=nombre,
        project_billing_info=billing_v1.ProjectBillingInfo(billing_account_name=""),
    )
    print(f"Facturación desvinculada: gasto {costo} >= presupuesto {presupuesto}.")
