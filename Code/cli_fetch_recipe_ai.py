# recipe_cli.py  ──────────────────────────────────────────────────────────────
"""
Call the Ollama *CLI* (not the HTTP API) to generate a recipe.

Usage inside another script
---------------------------
from recipe_cli import generate_recipe

recipe = generate_recipe(
    ingredients=["selt", "chikan", "tomaeto"],
    model="gemma3:1b",          # optional
    timeout_sec=120,            # optional
    max_retries=3               # optional
)
print(recipe["generic_name"])
"""

from __future__ import annotations
import json, re, subprocess, textwrap, time
from typing import Dict, List
import ast

# ─── Configuration (override when calling generate_recipe) ───────────────────
MODEL_TAG   = "gemma3:1b"       # must exist in `ollama list`
TIMEOUT_SEC = 120
MAX_RETRIES = 3

# ─── Helpers ─────────────────────────────────────────────────────────────────
def _build_prompt(ingredients: List[str]) -> str:
    ing = ", ".join(ingredients)
    return f"""You are a professional chef-bot.

    Ingredients (may contain typos): {ing}

    Return ONLY valid JSON, **no markdown fences, no extra keys**:

    {{
    "generic_name": "concise dish name",
    "description": "≤300 words",
    "tags": ["tag1","tag2","tag3","tag4","tag5"],
    "nutrition": {{
        "calories": "",
        "total_fat": "",
        "sugar": "",
        "sodium": "",
        "protein": "",
        "saturated_fat": ""
    }},
    "ingredient": ["ingredient1","ingredient2","ingredient3","ingredient4","ingredient5"],
    "steps": ["step1","step2","step3","step4","step5"],
    "cuisine": "cuisine type",
    "prep_time": "e.g. 20 min"
    }}"""

def _run_ollama(prompt: str,
                model: str,
                timeout_sec: int,
                max_retries: int) -> str:
    """Launch the Ollama CLI and return UTF-8 decoded stdout."""
    cmd = ["ollama", "run", model, prompt]
    backoff = 2

    for attempt in range(1, max_retries + 1):
        try:
            completed = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,     # capture bytes
                stderr=subprocess.PIPE,
                check=True,
                timeout=timeout_sec
            )
            # Decode explicitly; never let Python pick the console code page
            return completed.stdout.decode("utf-8", errors="replace")

        except subprocess.TimeoutExpired:
            print(f"⏱  Timeout after {timeout_sec}s (attempt {attempt}).")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Ollama exited with {e.returncode}. "
                  f"stderr (first 120 chars): {e.stderr[:120]!r}")

        if attempt == max_retries:
            raise RuntimeError("Ollama CLI failed after several retries.")
        time.sleep(backoff)
        backoff *= 2


def _fix_json(blob: str) -> str:
    """
    Repair the most common Gemma/Ollama mistakes so `json.loads` succeeds.
    1. nutrition list-of-pairs  → dict
    2. trailing comma before } or ]
    3. smart quotes → straight quotes
    """

    # smart quotes
    blob = (blob
            .replace("“", '"').replace("”", '"')
            .replace("’", "'"))

    # nutrition: ["k":"v", ...]  →  {"k":"v", ...}
    def nutr_repl(m):
        inner = m.group(1)
        # grab "key": "value" pairs
        pairs = re.findall(r'"([^"]+)"\s*:\s*"([^"]+)"', inner)
        dict_str = ", ".join(f'"{k}":"{v}"' for k, v in pairs)
        return f'"nutrition": {{{dict_str}}}'

    blob = re.sub(r'"nutrition"\s*:\s*\[(.*?)\]', nutr_repl, blob, flags=re.S)

    # trailing commas  ,}
    blob = re.sub(r',(\s*[}\]])', r'\1', blob)

    return blob

# ─── New helper to build a theme-driven prompt ───────────────────────────────
def _build_prompt_from_theme(theme: str) -> str:
    return f"""You are a professional chef-bot.

The user says: "{theme}"

Invent ONE original recipe whose *flavour, presentation, or story* evokes that
idea.  Assume you have a full pantry; you may choose any ingredients.

Return ONLY valid JSON – no markdown fences, no commentary, exactly these keys:

{{
"generic_name": "concise dish name",
"description": "≤300 words",
"tags": ["tag1","tag2","tag3","tag4","tag5"],
"nutrition": {{
    "calories": "",
    "total_fat": "",
    "sugar": "",
    "sodium": "",
    "protein": "",
    "saturated_fat": ""
}},
"ingredient": ["ingredient1","ingredient2","ingredient3","ingredient4","ingredient5"],
"steps": ["step1","step2","step3","step4","step5"],
"cuisine": "cuisine type",
"prep_time": "e.g. 20 min"
}}"""

# ─── Public API: generate from an *arbitrary user prompt* ────────────────────
def generate_recipe_from_theme(
        *,
        theme: str,
        model: str = MODEL_TAG,
        timeout_sec: int = TIMEOUT_SEC,
        max_retries: int = MAX_RETRIES) -> Dict:
    """
    Return a recipe whose concept matches an imaginative theme or 'vibe'.

    Example
    -------
    >>> r = generate_recipe_from_theme(theme="I feel like the pyramids of Giza")
    >>> print(r["generic_name"])
    'Sun-Baked Sandstone Falafel'
    """
    prompt = _build_prompt_from_theme(theme)
    raw    = _run_ollama(prompt, model, timeout_sec, max_retries)
    recipe = _extract_json(raw)
    _normalise_nutrition(recipe)
    return recipe

def _extract_json(text: str) -> dict:
    clean = re.sub(r"```(?:json)?|```", "", text, flags=re.I).strip()
    match = re.search(r"\{.*\}", clean, re.S)
    if not match:
        raise ValueError("No JSON object found in model output.")

    blob = _fix_json(match.group(0))

    # 1st try strict JSON
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        # fallback: Python literal
        return ast.literal_eval(blob)

def _normalise_nutrition(recipe: Dict) -> None:
    KEYS = ["calories", "total_fat", "sugar",
            "sodium", "protein", "saturated_fat"]

    nutr = recipe.get("nutrition", {})
    if isinstance(nutr, list):
        recipe["nutrition"] = {k: nutr[i] if i < len(nutr) else ""
                               for i, k in enumerate(KEYS)}
    elif isinstance(nutr, dict):
        recipe["nutrition"] = {k: nutr.get(k, "") for k in KEYS}
    else:
        recipe["nutrition"] = {k: "" for k in KEYS}

# ─── Public API ──────────────────────────────────────────────────────────────
def generate_recipe(*,
                    ingredients: List[str],
                    model: str = MODEL_TAG,
                    timeout_sec: int = TIMEOUT_SEC,
                    max_retries: int = MAX_RETRIES) -> Dict:
    """
    Return a Python dict with the recipe JSON.

    Parameters
    ----------
    ingredients : list[str]
        Raw user ingredients.
    model, timeout_sec, max_retries : optional
        Override defaults at call-site.
    """
    prompt = _build_prompt(ingredients)
    raw    = _run_ollama(prompt, model, timeout_sec, max_retries)
    recipe = _extract_json(raw)
    _normalise_nutrition(recipe)
    return recipe

# ─── Optional CLI fallback (kept small) ──────────────────────────────────────
if __name__ == "__main__":
    import sys, json as _json
    if len(sys.argv) < 2:
        sys.exit("Usage: python recipe_cli.py salt,chicken,tomato")

    ingr = [x.strip() for x in sys.argv[1].split(",") if x.strip()]
    result = generate_recipe(ingredients=ingr)
    print(_json.dumps(result, indent=2))
