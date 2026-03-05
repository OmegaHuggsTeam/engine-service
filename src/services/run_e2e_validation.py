"""
Validacao E2E do Workflow de Energia.
1. Carrega identity_config.json
2. Executa Playwright contra staging sandbox (localhost:9090)
3. Valida entrega de chave simulada no KeyManager
"""

import asyncio
import hashlib
import json
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("e2e_validation")

PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "src" / "services" / "identity_config.json"


async def run_validation():
    from src.services.identity_manager import IdentityManager
    from src.services.e2e_runner import StagingSandboxRunner
    from src.utils.llm_client import KeyManager

    logger.info("=" * 60)
    logger.info("WORKFLOW DE ENERGIA - VALIDACAO E2E")
    logger.info("=" * 60)

    # --- Phase 1: Load config & generate task queue ---
    logger.info("\n[PHASE 1] Carregando identity_config.json...")
    im = IdentityManager()
    config = im.load_config(str(CONFIG_PATH))
    tasks = im.generate_task_queue(config)

    logger.info(f"  Identity: {config.identity_name}")
    logger.info(f"  Providers: {[p.provider.value for p in config.providers if p.enabled]}")
    logger.info(f"  Tasks geradas: {len(tasks)}")
    for t in tasks:
        deps = f" (depends: {t.depends_on[0]})" if t.depends_on else ""
        logger.info(f"    [{t.id}] {t.step.value}{deps}")

    # --- Phase 2: Run Playwright E2E (headed mode) ---
    logger.info("\n[PHASE 2] Executando Playwright E2E contra sandbox...")
    logger.info("  Mode: headed (visivel no navegador)")
    logger.info("  Target: http://localhost:9090")

    runner = StagingSandboxRunner(config, headless=False)
    results = await runner.run_all()

    extracted_key = None
    all_success = True
    for provider, result in results.items():
        status = "OK" if result["success"] else "FAIL"
        logger.info(f"\n  [{provider.upper()}] {status}")
        for step in result.get("steps", []):
            icon = "+" if step["success"] else "x"
            output = step.get("output", step.get("error", ""))
            logger.info(f"    [{icon}] {step['step']}: {output}")
            # Captura a chave extraida do Groq mock
            if step["step"] == "extract_key" and step["success"]:
                extracted_key = step["output"]
        if not result["success"]:
            all_success = False

    # --- Phase 3: Validate KeyManager integration ---
    logger.info("\n[PHASE 3] Validando KeyManager SecretVault...")

    km = KeyManager([])  # Vault vazio para teste isolado
    logger.info(f"  Vault inicial: {km.get_vault_status()}")

    if extracted_key:
        logger.info(f"  Chave extraida do sandbox: {extracted_key[:20]}...")
        checksum = hashlib.sha256(extracted_key.encode()).hexdigest()
        logger.info(f"  SHA-256 checksum: {checksum[:32]}...")

        registered = km.register_key(extracted_key, checksum, provider="groq")
        logger.info(f"  register_key() -> {registered}")

        vault_status = km.get_vault_status()
        logger.info(f"  Vault apos registro: {vault_status}")

        # Validacao cruzada
        valid = km.validate_checksum(extracted_key, checksum)
        logger.info(f"  validate_checksum() -> {valid}")

        bad = km.validate_checksum(extracted_key, "bad_checksum_here")
        logger.info(f"  validate_checksum(bad) -> {bad}")
    else:
        logger.warning("  Nenhuma chave extraida do sandbox!")
        all_success = False

    # --- Summary ---
    logger.info("\n" + "=" * 60)
    if all_success and extracted_key:
        logger.info("RESULTADO: WORKFLOW VALIDADO COM SUCESSO")
    else:
        logger.info("RESULTADO: WORKFLOW COM FALHAS")
    logger.info("=" * 60)

    return all_success


if __name__ == "__main__":
    success = asyncio.run(run_validation())
    sys.exit(0 if success else 1)
