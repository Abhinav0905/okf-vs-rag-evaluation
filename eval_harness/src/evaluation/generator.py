"""Generator (LLM) adapters with Bedrock on-demand cost accounting.

Three backends behind one :class:`Generator` interface:

* :class:`BedrockGenerator` — **primary/paper**. Claude on Amazon Bedrock via
  ``InvokeModel`` (Messages API), temperature 0.
* :class:`OpenAIGenerator` — fallback generator (uses ``OPENAI_KEYS``).
* :class:`MockGenerator` — deterministic, offline; lets the whole pipeline and
  the acceptance-criteria call-count checks run without any network / creds.

Every call returns a :class:`GenResult` carrying token usage and USD cost
computed from the committed pricing table in ``eval_config.yaml``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

from .config import Config


@dataclass
class GenResult:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    model_id: str = ""
    calls: int = 1                       # LLM calls this GenResult represents
    raw: dict = field(default_factory=dict)


def _tok(text: str) -> int:
    try:
        import tiktoken

        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except Exception:
        return int(len(text.split()) * 1.3) + 1


class Generator:
    """Base generator; subclasses implement :meth:`_invoke`."""

    def __init__(self, config: Config, model_id: str):
        self.config = config
        self.model_id = model_id
        self._price = config.price(model_id)

    def cost(self, in_tok: int, out_tok: int) -> float:
        return (in_tok / 1e6) * self._price["input_per_mtok"] + \
               (out_tok / 1e6) * self._price["output_per_mtok"]

    def generate(self, prompt: str, system: Optional[str] = None,
                 max_tokens: Optional[int] = None,
                 temperature: Optional[float] = None) -> GenResult:
        mt = max_tokens or self.config.generator.max_tokens
        temp = self.config.generator.temperature if temperature is None else temperature
        return self._invoke(prompt, system, mt, temp)

    def _invoke(self, prompt, system, max_tokens, temperature) -> GenResult:  # noqa
        raise NotImplementedError


class BedrockGenerator(Generator):
    """Claude via Bedrock ``InvokeModel`` (Anthropic Messages API)."""

    def __init__(self, config: Config, model_id: Optional[str] = None):
        super().__init__(config, model_id or config.generator.bedrock_model_id)
        import boto3
        from botocore.config import Config as BotoConfig

        # Adaptive retries survive throttling during long, high-volume runs.
        self._client = boto3.client(
            "bedrock-runtime", region_name=config.generator.region,
            config=BotoConfig(retries={"max_attempts": 8, "mode": "adaptive"},
                              read_timeout=120, connect_timeout=15),
        )

    def _invoke(self, prompt, system, max_tokens, temperature) -> GenResult:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        }
        if system:
            body["system"] = system
        resp = self._client.invoke_model(modelId=self.model_id, body=json.dumps(body))
        payload = json.loads(resp["body"].read())
        text = "".join(b.get("text", "") for b in payload.get("content", []))
        usage = payload.get("usage", {})
        in_tok = int(usage.get("input_tokens", _tok((system or "") + prompt)))
        out_tok = int(usage.get("output_tokens", _tok(text)))
        return GenResult(text=text, input_tokens=in_tok, output_tokens=out_tok,
                         cost_usd=self.cost(in_tok, out_tok), model_id=self.model_id,
                         raw=payload)


class OpenAIGenerator(Generator):
    """OpenAI chat-completions fallback generator."""

    def __init__(self, config: Config, model_id: Optional[str] = None):
        super().__init__(config, model_id or config.generator.openai_model)
        from openai import OpenAI

        key = os.environ.get("OPENAI_API_KEY") or (os.environ.get("OPENAI_KEYS", "").split(",")[0].strip())
        self._client = OpenAI(api_key=key)

    def _invoke(self, prompt, system, max_tokens, temperature) -> GenResult:
        messages = ([{"role": "system", "content": system}] if system else []) + \
                   [{"role": "user", "content": prompt}]
        resp = self._client.chat.completions.create(
            model=self.model_id, messages=messages,
            max_tokens=max_tokens, temperature=temperature,
        )
        text = resp.choices[0].message.content or ""
        u = resp.usage
        in_tok, out_tok = (u.prompt_tokens, u.completion_tokens) if u else (_tok(prompt), _tok(text))
        return GenResult(text=text, input_tokens=in_tok, output_tokens=out_tok,
                         cost_usd=self.cost(in_tok, out_tok), model_id=self.model_id)


class MockGenerator(Generator):
    """Deterministic offline generator for smoke tests / CI.

    Builds a plausible answer by echoing the first context chunk and citing its
    id, so citation parsing and cost accounting exercise real code paths. If the
    context is empty or clearly signals no-answer, it returns the canonical
    refusal string (important for the negative-question / G3 path).
    """

    REFUSAL = "The retrieved context does not contain sufficient information to answer this."

    def __init__(self, config: Config, model_id: str = "mock"):
        super().__init__(config, model_id)

    def _invoke(self, prompt, system, max_tokens, temperature) -> GenResult:
        import re

        cids = re.findall(r"\[([A-Z]{2,3}-\d{5})", prompt)
        # Detect an explicit "no context" marker the systems insert when empty.
        if "NO_CONTEXT" in prompt or not cids:
            text = self.REFUSAL
        else:
            snippet = ""
            m = re.search(r"\[" + re.escape(cids[0]) + r"[^\]]*\]\n(.+)", prompt)
            if m:
                snippet = m.group(1)[:240]
            text = (f"Based on the retrieved WMP context, the answer references "
                    f"the relevant program details. ({cids[0]}) {snippet}").strip()
        in_tok, out_tok = _tok((system or "") + prompt), _tok(text)
        return GenResult(text=text, input_tokens=in_tok, output_tokens=out_tok,
                         cost_usd=self.cost(in_tok, out_tok), model_id=self.model_id)


def get_generator(config: Config, backend: Optional[str] = None) -> Generator:
    backend = backend or config.generator.backend
    if backend == "bedrock":
        return BedrockGenerator(config)
    if backend == "openai":
        return OpenAIGenerator(config)
    if backend == "mock":
        return MockGenerator(config)
    raise ValueError(f"unknown generator backend: {backend}")
