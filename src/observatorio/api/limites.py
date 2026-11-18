"""Límites de uso en memoria para el endpoint del LLM.

Funciona porque Cloud Run corre con máximo 1 instancia: el estado en memoria es global.
Si algún día se escala a más instancias, mover esto a un almacén compartido.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from datetime import date


class LimiteExcedido(Exception):
    pass


class Limitador:
    def __init__(self, max_por_minuto_ip: int, max_diario: int, reloj=time.monotonic):
        self.max_por_minuto_ip = max_por_minuto_ip
        self.max_diario = max_diario
        self._reloj = reloj
        self._por_ip: dict[str, deque[float]] = defaultdict(deque)
        self._dia = date.today()
        self._usos_dia = 0
        self._lock = threading.Lock()

    def registrar(self, ip: str, hoy: date | None = None) -> None:
        hoy = hoy or date.today()
        ahora = self._reloj()
        with self._lock:
            if hoy != self._dia:
                self._dia, self._usos_dia = hoy, 0
            if self._usos_dia >= self.max_diario:
                raise LimiteExcedido("Se alcanzó el máximo diario de preguntas. Vuelve mañana.")

            ventana = self._por_ip[ip]
            while ventana and ahora - ventana[0] > 60:
                ventana.popleft()
            if len(ventana) >= self.max_por_minuto_ip:
                raise LimiteExcedido("Demasiadas preguntas por minuto. Espera un momento.")

            ventana.append(ahora)
            self._usos_dia += 1
