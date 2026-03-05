"""
Kill Switch Monitor - Mecanismo de segurança física.

Monitora a posição do mouse em thread separada. Quando o mouse está
no canto superior esquerdo (x < 10, y < 10), dispara o kill switch
para interromper imediatamente todas as ações de autonomia.

Requisito 6: Kill Switch Safety Mechanism
"""

import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


def _get_mouse_position() -> tuple[int, int]:
    """Obtém posição do mouse. Fallback para (0,0) se pyautogui indisponível."""
    try:
        import pyautogui
        return pyautogui.position()
    except Exception:
        return (0, 0)


class KillSwitchMonitor:
    """
    Mecanismo de segurança que monitora a posição do mouse e dispara
    parada de emergência quando o mouse está no canto (0,0).
    Executa em thread separada para garantir responsividade.
    """

    def __init__(
        self,
        trigger_zone: tuple[int, int] = (10, 10),
        check_interval: float = 0.1,
        on_trigger: Optional[Callable[[], None]] = None,
    ):
        """
        Inicializa o monitor de kill switch.

        Args:
            trigger_zone: (largura, altura) da zona de trigger no canto superior esquerdo.
                         Trigger quando x < trigger_zone[0] e y < trigger_zone[1].
            check_interval: Segundos entre verificações de posição (padrão 100ms).
            on_trigger: Callback opcional chamado quando o kill switch é acionado.
        """
        self.trigger_zone = trigger_zone
        self.check_interval = check_interval
        self.on_trigger = on_trigger

        self._triggered = False
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def _in_trigger_zone(self, x: int, y: int) -> bool:
        """Verifica se (x, y) está na zona de trigger."""
        return x < self.trigger_zone[0] and y < self.trigger_zone[1]

    def _monitor_loop(self) -> None:
        """Loop principal do monitor em background."""
        while not self._stop_event.is_set():
            try:
                x, y = _get_mouse_position()
                if self._in_trigger_zone(x, y):
                    with self._lock:
                        self._triggered = True
                    logger.warning(
                        "⚠️ Kill Switch acionado: mouse em (%d, %d) - zona de segurança",
                        x, y,
                    )
                    if self.on_trigger:
                        try:
                            self.on_trigger()
                        except Exception as e:
                            logger.exception("Erro no callback on_trigger: %s", e)
                    self._stop_event.set()
                    return
            except Exception as e:
                logger.debug("KillSwitchMonitor check error: %s", e)
            self._stop_event.wait(self.check_interval)

    def start(self) -> None:
        """Inicia o monitoramento em thread de background."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._triggered = False
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()
        logger.debug("KillSwitchMonitor iniciado (zona: %s, intervalo: %ss)",
                     self.trigger_zone, self.check_interval)

    def stop(self) -> None:
        """Para o monitoramento e limpa a thread."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.debug("KillSwitchMonitor parado")

    def is_triggered(self) -> bool:
        """Retorna True se o kill switch foi acionado."""
        with self._lock:
            return self._triggered

    def reset(self) -> None:
        """Reseta o estado do kill switch (não reinicia o monitor)."""
        with self._lock:
            self._triggered = False
        self._stop_event.clear()
        logger.debug("KillSwitchMonitor resetado")
