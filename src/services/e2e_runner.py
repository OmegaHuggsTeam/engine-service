"""
E2E Runner - Playwright automation contra staging sandbox.
Executa steps de provisionamento em localhost:9090.
"""

import asyncio
import logging
from typing import Any

from src.services.models import (
    IdentityConfig,
    ProviderConfig,
    ProvisioningStep,
    StepConfig,
)

logger = logging.getLogger(__name__)


class StagingSandboxRunner:
    """Executa steps de provisionamento via Playwright contra o sandbox local."""

    def __init__(self, config: IdentityConfig, headless: bool = True):
        self.config = config
        self.headless = headless

    async def run_provider(self, provider_config: ProviderConfig) -> dict[str, Any]:
        """Executa todos os steps de um provider."""
        from playwright.async_api import async_playwright

        result = {"provider": provider_config.provider.value, "steps": [], "success": True}

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()

            try:
                for step_config in provider_config.steps:
                    step_result = await self._execute_step(
                        page, step_config, provider_config
                    )
                    result["steps"].append(step_result)
                    if not step_result.get("success"):
                        result["success"] = False
                        break
            except Exception as e:
                result["success"] = False
                result["error"] = str(e)
                logger.error(f"E2E error for {provider_config.provider.value}: {e}")
            finally:
                await browser.close()

        return result

    async def _execute_step(
        self, page, step_config: StepConfig, provider_config: ProviderConfig
    ) -> dict[str, Any]:
        """Dispatch de um step individual."""
        handlers = {
            ProvisioningStep.NAVIGATE: self._navigate,
            ProvisioningStep.FILL_FORM: self._fill_form,
            ProvisioningStep.SUBMIT: self._submit,
            ProvisioningStep.VERIFY: self._verify,
            ProvisioningStep.EXTRACT_KEY: self._extract_key,
            ProvisioningStep.STORE_KEY: self._store_key,
        }
        handler = handlers.get(step_config.step)
        if not handler:
            return {"step": step_config.step.value, "success": False, "error": "unknown step"}

        try:
            if step_config.step == ProvisioningStep.FILL_FORM:
                output = await handler(page, step_config, provider_config.form_fields)
            elif step_config.step == ProvisioningStep.NAVIGATE:
                output = await handler(page, step_config, provider_config.base_url)
            else:
                output = await handler(page, step_config)
            return {"step": step_config.step.value, "success": True, "output": output}
        except Exception as e:
            return {"step": step_config.step.value, "success": False, "error": str(e)}

    async def _navigate(self, page, step: StepConfig, base_url: str) -> str:
        """Navega para a URL base e aguarda o seletor."""
        await page.goto(base_url)
        if step.selector:
            await page.wait_for_selector(step.selector, timeout=step.timeout_ms)
        return f"navigated to {base_url}"

    async def _fill_form(self, page, step: StepConfig, form_fields: dict) -> str:
        """Preenche campo de formulario com valor do config."""
        value = form_fields.get(step.value_field, "") if step.value_field else ""
        if step.selector:
            await page.fill(step.selector, value)
        return f"filled {step.selector} with '{value}'"

    async def _submit(self, page, step: StepConfig) -> str:
        """Clica no botao de submit e aguarda navegacao."""
        if step.selector:
            await page.click(step.selector)
            await page.wait_for_load_state("networkidle")
        return f"submitted via {step.selector}"

    async def _verify(self, page, step: StepConfig) -> str:
        """Verifica que o seletor de sucesso esta visivel."""
        if step.selector:
            element = await page.wait_for_selector(step.selector, timeout=step.timeout_ms)
            text = await element.inner_text() if element else ""
            return f"verified: {text}"
        return "verify: no selector"

    async def _extract_key(self, page, step: StepConfig) -> str:
        """Extrai texto (API key) do seletor."""
        if step.selector:
            element = await page.wait_for_selector(step.selector, timeout=step.timeout_ms)
            key = await element.inner_text() if element else ""
            return key
        return ""

    async def _store_key(self, page, step: StepConfig) -> str:
        """Placeholder para armazenamento de key (integra com KeyManager)."""
        return "key stored (placeholder)"

    async def run_all(self) -> dict[str, dict]:
        """Executa todos os providers habilitados."""
        results = {}
        for provider_config in self.config.providers:
            if provider_config.enabled:
                result = await self.run_provider(provider_config)
                results[provider_config.provider.value] = result
        return results
