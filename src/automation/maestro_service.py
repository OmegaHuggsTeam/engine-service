"""
Maestro Service - Servico persistente de orquestracao visual.

Subsistemas:
  1. WindowArranger  - Posiciona Browser no Monitor 2, Cursor no Monitor 1 (pygetwindow + ctypes)
  2. TaskWatcher     - Monitora Neo4j por novas IdentityTasks e dispara e2e_runner
  3. VisualHeartbeat - Imprime coordenadas (X, Y) de cada acao Playwright no console
"""

import asyncio
import ctypes
import json
import logging
import sys
import time

if sys.platform == "win32":
    import ctypes.wintypes
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger("maestro")

PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "src" / "services" / "identity_config.json"

# ============================================================
# Subsystem 1: Window Arranger
# ============================================================

# Win32 constants for ShowWindow
SW_RESTORE = 9
SW_MAXIMIZE = 3


class MonitorInfo:
    """Geometria de um monitor detectada via EnumDisplayMonitors."""

    def __init__(self, index: int, left: int, top: int, right: int, bottom: int):
        self.index = index
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
        self.width = right - left
        self.height = bottom - top

    def __repr__(self) -> str:
        return f"Monitor({self.index}: {self.width}x{self.height} at ({self.left},{self.top}))"


def detect_monitors() -> list[MonitorInfo]:
    """Detecta monitores via Win32 EnumDisplayMonitors."""
    if sys.platform != "win32":
        return []

    monitors: list[MonitorInfo] = []

    def _callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
        r = lprcMonitor.contents
        monitors.append(
            MonitorInfo(len(monitors) + 1, r.left, r.top, r.right, r.bottom)
        )
        return True

    MonitorEnumProc = ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.POINTER(ctypes.wintypes.RECT),
        ctypes.c_double,
    )
    ctypes.windll.user32.EnumDisplayMonitors(
        None, None, MonitorEnumProc(_callback), 0
    )
    return monitors


def _find_window(title_substring: str):
    """Encontra janela por substring no titulo via pygetwindow."""
    import pygetwindow as gw

    for win in gw.getAllWindows():
        if title_substring.lower() in win.title.lower() and win.title.strip():
            return win
    return None


class WindowArranger:
    """Posiciona janelas nos monitores corretos no startup."""

    def __init__(
        self,
        cursor_match: str = "Cursor",
        browser_match: str = "Chromium",
    ):
        self.cursor_match = cursor_match
        self.browser_match = browser_match
        self.monitors = detect_monitors()

    def get_monitor(self, index: int) -> Optional[MonitorInfo]:
        """Retorna monitor por indice (1-based). None se nao existir."""
        for m in self.monitors:
            if m.index == index:
                return m
        return None

    def arrange(self) -> dict[str, Any]:
        """
        Move Cursor -> Monitor 1 (direita, menor), Browser -> Monitor 2 (esquerda, maior).
        Retorna relatorio do que foi feito.
        """
        report = {"monitors_detected": len(self.monitors), "actions": []}

        for m in self.monitors:
            report["actions"].append(f"  Detected {m}")
            logger.info(f"  {m}")

        if len(self.monitors) < 2:
            msg = "Apenas 1 monitor detectado - skip arrange"
            report["actions"].append(msg)
            logger.warning(msg)
            return report

        # Heuristica: monitor com menor left = Monitor 2 (esquerda/principal)
        # Monitor com maior left = Monitor 1 (direita, tipicamente o secundario)
        sorted_mons = sorted(self.monitors, key=lambda m: m.left)
        monitor_2 = sorted_mons[0]  # esquerda - browser vai aqui
        monitor_1 = sorted_mons[1]  # direita  - cursor vai aqui

        # Move Cursor para Monitor 1 (direita)
        cursor_win = _find_window(self.cursor_match)
        if cursor_win:
            self._move_window(cursor_win, monitor_1, "Cursor")
            report["actions"].append(
                f"  Cursor -> Monitor 1 ({monitor_1.left},{monitor_1.top})"
            )
        else:
            report["actions"].append(f"  Cursor window '{self.cursor_match}' nao encontrada")

        # Browser sera posicionado quando o Playwright abrir
        report["browser_target_monitor"] = {
            "index": monitor_2.index,
            "left": monitor_2.left,
            "top": monitor_2.top,
            "width": monitor_2.width,
            "height": monitor_2.height,
        }
        report["actions"].append(
            f"  Browser target -> Monitor 2 ({monitor_2.left},{monitor_2.top})"
        )

        return report

    def move_browser_to_monitor2(self) -> bool:
        """Busca janela do Chromium/browser e move para Monitor 2."""
        if len(self.monitors) < 2:
            return False

        sorted_mons = sorted(self.monitors, key=lambda m: m.left)
        monitor_2 = sorted_mons[0]

        browser_win = _find_window(self.browser_match)
        if browser_win:
            self._move_window(browser_win, monitor_2, "Browser")
            return True
        return False

    @staticmethod
    def _move_window(win, monitor: MonitorInfo, label: str):
        """Move e redimensiona janela para preencher o monitor."""
        try:
            if hasattr(win, "restore"):
                win.restore()
            win.moveTo(monitor.left, monitor.top)
            win.resizeTo(monitor.width, monitor.height)
            logger.info(
                f"  [{label}] -> ({monitor.left},{monitor.top}) "
                f"{monitor.width}x{monitor.height}"
            )
        except Exception as e:
            logger.warning(f"  [{label}] move falhou: {e}")


# ============================================================
# Subsystem 2: Task Watcher (Neo4j polling)
# ============================================================

class TaskWatcher:
    """
    Monitora Neo4j por IdentityTasks pendentes.
    Quando detecta tasks novas, dispara callback.
    """

    def __init__(
        self,
        graph_manager=None,
        poll_interval: float = 5.0,
        on_new_tasks: Callable | None = None,
    ):
        self._graph = graph_manager
        self._poll_interval = poll_interval
        self._on_new_tasks = on_new_tasks
        self._seen_task_ids: set[str] = set()
        self._running = False

    async def start(self):
        """Inicia loop de polling."""
        self._running = True
        logger.info(f"TaskWatcher iniciado (poll cada {self._poll_interval}s)")

        while self._running:
            try:
                new_tasks = self._poll_once()
                if new_tasks and self._on_new_tasks:
                    await self._on_new_tasks(new_tasks)
            except Exception as e:
                logger.error(f"TaskWatcher poll error: {e}")

            await asyncio.sleep(self._poll_interval)

    def stop(self):
        """Para o loop de polling."""
        self._running = False
        logger.info("TaskWatcher parado")

    def _poll_once(self) -> list[dict]:
        """Faz uma query ao Neo4j e retorna tasks nao vistas."""
        if not self._graph:
            return []

        from src.neural_link.graph.queries import GET_PENDING_TASKS_BY_TYPE

        try:
            results = self._graph.execute_read(
                GET_PENDING_TASKS_BY_TYPE, {"task_type": "provisioning"}
            )
        except Exception as e:
            logger.debug(f"Neo4j poll falhou (esperado sem Neo4j): {e}")
            return []

        new_tasks = []
        for row in results:
            task_data = row.get("t", row)
            task_id = task_data.get("id", "")
            if task_id and task_id not in self._seen_task_ids:
                self._seen_task_ids.add(task_id)
                new_tasks.append(task_data)

        if new_tasks:
            logger.info(f"TaskWatcher: {len(new_tasks)} novas tasks detectadas")

        return new_tasks


# ============================================================
# Subsystem 3: Visual Heartbeat
# ============================================================

# ANSI colors for terminal output
_C_CYAN = "\033[96m"
_C_GREEN = "\033[92m"
_C_YELLOW = "\033[93m"
_C_RED = "\033[91m"
_C_BOLD = "\033[1m"
_C_RESET = "\033[0m"

_STEP_ICONS = {
    "navigate": f"{_C_CYAN}->{_C_RESET}",
    "fill_form": f"{_C_GREEN}[F]{_C_RESET}",
    "submit": f"{_C_YELLOW}[S]{_C_RESET}",
    "verify": f"{_C_GREEN}[V]{_C_RESET}",
    "extract_key": f"{_C_CYAN}[K]{_C_RESET}",
    "store_key": f"{_C_GREEN}[+]{_C_RESET}",
}


class VisualHeartbeat:
    """
    Intercepta acoes do Playwright e printa coordenadas (X, Y) no console.
    Funciona como wrapper em torno do StagingSandboxRunner.
    """

    def __init__(self, output_fn: Callable[[str], None] | None = None):
        self.output_fn = output_fn or self._default_output
        self.action_log: list[dict] = []

    @staticmethod
    def _default_output(msg: str):
        safe = msg.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
            sys.stdout.encoding or "utf-8", errors="replace"
        )
        sys.stdout.write(safe + "\n")
        sys.stdout.flush()

    def _timestamp(self) -> str:
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]

    def pulse(
        self,
        step: str,
        provider: str,
        selector: str | None,
        x: float,
        y: float,
        detail: str = "",
    ):
        """Emite um heartbeat no console com coordenadas."""
        icon = _STEP_ICONS.get(step, "?")
        coord = f"({int(x):>5}, {int(y):>4})"

        line = (
            f"  {_C_BOLD}[{self._timestamp()}]{_C_RESET} "
            f"{icon} {step:<12} "
            f"{_C_BOLD}{provider:<8}{_C_RESET} "
            f"@ {coord} "
            f"{selector or ''} "
            f"{_C_CYAN}{detail}{_C_RESET}"
        )
        self.output_fn(line)
        self.action_log.append({
            "time": self._timestamp(),
            "step": step,
            "provider": provider,
            "x": x,
            "y": y,
            "selector": selector,
            "detail": detail,
        })


async def _get_element_coords(page, selector: str | None) -> tuple[float, float]:
    """Extrai coordenadas centrais de um elemento Playwright."""
    if not selector:
        return (0.0, 0.0)
    try:
        element = await page.query_selector(selector)
        if element:
            box = await element.bounding_box()
            if box:
                cx = box["x"] + box["width"] / 2
                cy = box["y"] + box["height"] / 2
                return (cx, cy)
    except Exception:
        pass
    return (0.0, 0.0)


class InstrumentedRunner:
    """
    Wrapper sobre StagingSandboxRunner que injeta Visual Heartbeat.
    Cada acao Playwright emite um pulse com coordenadas (X, Y).
    """

    def __init__(self, config, heartbeat: VisualHeartbeat, headless: bool = False):
        self.config = config
        self.heartbeat = heartbeat
        self.headless = headless

    async def run_all(self) -> dict[str, dict]:
        from playwright.async_api import async_playwright

        results = {}

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)

            for provider_config in self.config.providers:
                if not provider_config.enabled:
                    continue

                provider = provider_config.provider.value
                page = await browser.new_page()
                result = {"provider": provider, "steps": [], "success": True}

                try:
                    for step_config in provider_config.steps:
                        step_name = step_config.step.value
                        step_result = await self._run_step(
                            page, step_config, provider_config, provider
                        )
                        result["steps"].append(step_result)
                        if not step_result.get("success"):
                            result["success"] = False
                            break
                except Exception as e:
                    result["success"] = False
                    result["error"] = str(e)
                finally:
                    await page.close()

                results[provider] = result

            await browser.close()

        return results

    async def _run_step(self, page, step_config, provider_config, provider: str) -> dict:
        """Executa um step e emite heartbeat com coordenadas."""
        step_name = step_config.step.value
        selector = step_config.selector

        try:
            if step_name == "navigate":
                await page.goto(provider_config.base_url)
                if selector:
                    await page.wait_for_selector(selector, timeout=step_config.timeout_ms)
                x, y = await _get_element_coords(page, selector)
                self.heartbeat.pulse(step_name, provider, selector, x, y, provider_config.base_url)
                output = f"navigated to {provider_config.base_url}"

            elif step_name == "fill_form":
                value = ""
                if step_config.value_field:
                    value = provider_config.form_fields.get(step_config.value_field, "")
                if selector:
                    x, y = await _get_element_coords(page, selector)
                    await page.fill(selector, value)
                    self.heartbeat.pulse(step_name, provider, selector, x, y, f"'{value}'")
                output = f"filled {selector} with '{value}'"

            elif step_name == "submit":
                if selector:
                    x, y = await _get_element_coords(page, selector)
                    await page.click(selector)
                    self.heartbeat.pulse(step_name, provider, selector, x, y, "click")
                    await page.wait_for_load_state("networkidle")
                output = f"submitted via {selector}"

            elif step_name == "verify":
                if selector:
                    element = await page.wait_for_selector(
                        selector, timeout=step_config.timeout_ms
                    )
                    x, y = await _get_element_coords(page, selector)
                    text = await element.inner_text() if element else ""
                    self.heartbeat.pulse(step_name, provider, selector, x, y, text)
                    output = f"verified: {text}"
                else:
                    output = "verify: no selector"

            elif step_name == "extract_key":
                if selector:
                    element = await page.wait_for_selector(
                        selector, timeout=step_config.timeout_ms
                    )
                    x, y = await _get_element_coords(page, selector)
                    key = await element.inner_text() if element else ""
                    masked = key[:8] + "..." if len(key) > 8 else key
                    self.heartbeat.pulse(step_name, provider, selector, x, y, masked)
                    output = key
                else:
                    output = ""

            elif step_name == "store_key":
                self.heartbeat.pulse(step_name, provider, selector, 0, 0, "vault")
                output = "key stored"

            else:
                output = "unknown step"

            return {"step": step_name, "success": True, "output": output}

        except Exception as e:
            self.heartbeat.pulse(
                step_name, provider, selector, 0, 0, f"ERROR: {e}"
            )
            return {"step": step_name, "success": False, "error": str(e)}


# ============================================================
# MaestroService - Orquestrador principal
# ============================================================

class MaestroService:
    """
    Servico persistente que unifica:
      - WindowArranger: posiciona janelas nos monitores
      - TaskWatcher: monitora Neo4j por novas tasks
      - VisualHeartbeat: imprime coordenadas de cada acao Playwright
    """

    def __init__(
        self,
        graph_manager=None,
        poll_interval: float = 5.0,
        headless: bool = False,
        cursor_match: str = "Cursor",
        browser_match: str = "Chromium",
        router=None,
    ):
        self.heartbeat = VisualHeartbeat()
        self.arranger = WindowArranger(
            cursor_match=cursor_match,
            browser_match=browser_match,
        )
        self.watcher = TaskWatcher(
            graph_manager=graph_manager,
            poll_interval=poll_interval,
            on_new_tasks=self._handle_new_tasks,
        )
        self._graph = graph_manager
        self._headless = headless
        self._running = False
        self._router = router

    async def start(self):
        """Inicia o Maestro Service."""
        self._running = True

        _banner()
        logger.info("[1/3] Window Arranger...")
        report = self.arranger.arrange()
        for action in report.get("actions", []):
            logger.info(action)

        logger.info("[2/3] Visual Heartbeat pronto")
        logger.info("[3/3] TaskWatcher iniciando...")

        if self._graph:
            await self.watcher.start()
        else:
            logger.warning(
                "Neo4j nao disponivel - Maestro em modo standalone "
                "(use run_e2e_now() para execucao manual)"
            )
            # Fica vivo aguardando comandos
            while self._running:
                await asyncio.sleep(1)

    def stop(self):
        """Para todos os subsistemas."""
        self._running = False
        self.watcher.stop()
        logger.info("Maestro Service parado.")

    async def _handle_new_tasks(self, tasks: list[dict]):
        """Callback do TaskWatcher: classifica tasks via router e despacha."""
        if not self._router:
            logger.info(f"Disparando E2E para {len(tasks)} novas tasks...")
            await self.run_e2e_now()
            return

        from src.middleware.groq_router import RouterRequest, TaskComplexity

        structural_tasks = []
        for task in tasks:
            task_id = task.get("id", "unknown")
            task_desc = task.get("description", str(task))
            req = RouterRequest(
                task_description=task_desc,
                task_type=task.get("type", "provisioning"),
                context=task,
                source="maestro_service",
            )
            resp = self._router.route(req)

            if resp.complexity == TaskComplexity.REPETITIVE and not resp.escalate:
                logger.info(f"Router handled task {task_id}: {resp.reason}")
                if self._graph and resp.result:
                    from src.neural_link.graph.queries import UPDATE_TASK_STATUS
                    self._graph.execute_write(
                        UPDATE_TASK_STATUS,
                        {"task_id": task_id, "status": "completed", "output": json.dumps(resp.result)},
                    )
            else:
                structural_tasks.append(task)

        if structural_tasks:
            logger.info(f"Escalating {len(structural_tasks)} structural tasks to E2E runner")
            await self.run_e2e_now()

    async def run_e2e_now(self) -> dict[str, dict]:
        """Executa o E2E runner com Visual Heartbeat integrado."""
        from src.services.identity_manager import IdentityManager

        if self._router:
            from src.middleware.groq_router import RouterRequest
            req = RouterRequest(
                task_description="Pre-flight check for E2E execution",
                task_type="pre_flight",
                context={"config_path": str(CONFIG_PATH), "headless": self._headless},
                source="maestro_service",
            )
            resp = self._router.route(req)
            if not resp.escalate and resp.result:
                logger.info(f"Router pre-flight: {resp.reason}")

        im = IdentityManager(graph_manager=self._graph)
        config = im.load_config(str(CONFIG_PATH))

        self.heartbeat.output_fn(
            f"\n{'=' * 60}\n"
            f"  {_C_BOLD}MAESTRO E2E - {config.identity_name}{_C_RESET}\n"
            f"  Providers: {[p.provider.value for p in config.providers if p.enabled]}\n"
            f"{'=' * 60}"
        )

        runner = InstrumentedRunner(
            config=config,
            heartbeat=self.heartbeat,
            headless=self._headless,
        )

        results = await runner.run_all()

        # Tenta posicionar browser no Monitor 2 assim que o Chromium abrir
        self.arranger.move_browser_to_monitor2()

        # Sumario
        self.heartbeat.output_fn(f"\n{'=' * 60}")
        for prov, res in results.items():
            status = f"{_C_GREEN}OK{_C_RESET}" if res["success"] else f"{_C_RED}FAIL{_C_RESET}"
            n_steps = len(res.get("steps", []))
            self.heartbeat.output_fn(f"  {prov:<8} {status}  ({n_steps} steps)")
        self.heartbeat.output_fn(
            f"  Heartbeat: {len(self.heartbeat.action_log)} pulses emitidos\n"
            f"{'=' * 60}\n"
        )

        return results


def _banner():
    """Imprime banner de startup do Maestro."""
    banner = (
        f"\n{_C_BOLD}{_C_CYAN}"
        "  +----------------------------------------------+\n"
        "  |         MAESTRO SERVICE v1.0                 |\n"
        "  |   Window Arranger | Task Watcher | Heartbeat |\n"
        "  +----------------------------------------------+\n"
        f"{_C_RESET}"
    )
    safe = banner.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
        sys.stdout.encoding or "utf-8", errors="replace"
    )
    print(safe)


# ============================================================
# CLI Entrypoint
# ============================================================

async def _main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Tenta conectar ao Neo4j (graceful fallback)
    graph = None
    try:
        from src.neural_link.graph.manager import GraphManager
        graph = GraphManager.from_env()
        graph.verify_connectivity()
        logger.info("Neo4j conectado")
    except Exception as e:
        logger.warning(f"Neo4j indisponivel ({e}) - modo standalone")
        graph = None

    maestro = MaestroService(
        graph_manager=graph,
        poll_interval=5.0,
        headless=False,
    )

    try:
        # Executa E2E imediatamente no startup
        await maestro.run_e2e_now()

        # Depois fica em modo watcher
        if graph:
            logger.info("Entrando em modo watcher (Ctrl+C para sair)...")
            await maestro.watcher.start()
        else:
            logger.info("E2E completo. Sem Neo4j, nao ha watcher.")
    except KeyboardInterrupt:
        pass
    finally:
        maestro.stop()


if __name__ == "__main__":
    asyncio.run(_main())
