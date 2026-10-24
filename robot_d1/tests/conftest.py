"""Configuración común de pytest: importa el paquete d1 desde robot_d1/ y da un reloj falso."""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class FakeClock:
    """Reloj manual: las pruebas avanzan el tiempo a mano."""

    def __init__(self, t: float = 1000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> float:
        self.t += dt
        return self.t


@pytest.fixture
def clock():
    return FakeClock()
