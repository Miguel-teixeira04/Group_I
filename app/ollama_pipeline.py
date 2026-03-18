"""
ollama_pipeline.py – Ollama integration for the AI Environmental Risk workflow.

Responsibilities:
  1. Load model configuration from models.yaml.
  2. Ensure the required Ollama models are available (pull if missing).
  3. Call a vision model to describe a satellite image.
  4. Call a text model to assess environmental risk from the description.
  5. Persist every run as a row in database/images.csv.
"""

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import ollama
import yaml


# ──────────────────────────────────────────────
# 1.  Config loader
# ──────────────────────────────────────────────

_ROOT = Path(__file__).resolve().parent.parent  # project root


def load_config(path: Path | None = None) -> dict:
    """Read models.yaml and return the parsed dict."""
    path = path or _ROOT / "models.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ──────────────────────────────────────────────
# 2.  Model availability check
# ──────────────────────────────────────────────

def ensure_model(model_name: str) -> None:
    """Pull *model_name* from the Ollama registry if it
    is not already present on the local machine."""
    local_models = [m.model for m in ollama.list().models]
    if model_name not in local_models:
        print(f"[ollama] Pulling {model_name} — this may take a few minutes …")
        ollama.pull(model_name)
        print(f"[ollama] {model_name} ready.")


# ──────────────────────────────────────────────
# 3.  Image description  (vision model)
# ──────────────────────────────────────────────

def describe_image(image_path: str, config: dict) -> str:
    """Send the satellite image to the vision model and return the
    natural-language description it produces."""
    cfg = config["image_model"]
    model = cfg["name"]
    prompt = cfg["prompt"]

    ensure_model(model)

    response = ollama.chat(
        model=model,
        messages=[{
            "role": "user",
            "content": prompt,
            "images": [image_path],
        }],
        options={
            "temperature": cfg.get("temperature", 0.3),
            "num_predict": cfg.get("max_tokens", 512),
        },
    )
    return response.message.content.strip()


# ──────────────────────────────────────────────
# 4.  Risk assessment  (text model)
# ──────────────────────────────────────────────

def assess_risk(description: str, config: dict) -> dict:
    """Given an image description, ask the text model whether the area
    is at environmental risk.

    Returns
    -------
    dict  with keys  "danger" (str "Y"/"N") and "justification" (str).
    """
    cfg = config["text_model"]
    model = cfg["name"]
    prompt = cfg["prompt"]

    ensure_model(model)

    full_prompt = f"{prompt}\n\nImage description:\n{description}"

    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": full_prompt}],
        options={
            "temperature": cfg.get("temperature", 0.2),
            "num_predict": cfg.get("max_tokens", 256),
        },
    )

    raw = response.message.content.strip()

    # Try to parse a JSON object from the model output.
    try:
        # The model may wrap the JSON in markdown code fences — strip them.
        cleaned = raw
        if "```" in cleaned:
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        result = json.loads(cleaned)
        danger = str(result.get("danger", "N")).upper()
        justification = result.get("justification", raw)
    except (json.JSONDecodeError, IndexError):
        # Fallback: treat the whole response as justification and guess
        # danger flag from keywords.
        danger_keywords = ["risk", "danger", "deforest", "erosion", "pollut",
                           "degrad", "threat", "alarm", "concern"]
        danger = "Y" if any(kw in raw.lower() for kw in danger_keywords) else "N"
        justification = raw

    return {"danger": danger, "justification": justification}


# ──────────────────────────────────────────────
# 5.  Persistence  (append to database/images.csv)
# ──────────────────────────────────────────────

_CSV_PATH = _ROOT / "database" / "images.csv"

_FIELDNAMES = [
    "timestamp", "latitude", "longitude", "zoom",
    "image_description", "image_prompt", "image_model",
    "text_description", "text_prompt", "text_model", "danger",
]


def save_to_database(
    latitude: float,
    longitude: float,
    zoom: int,
    image_description: str,
    risk_result: dict,
    config: dict,
) -> None:
    """Append one row to database/images.csv."""
    os.makedirs(_CSV_PATH.parent, exist_ok=True)

    row = {
        "timestamp":          datetime.now(timezone.utc).isoformat(),
        "latitude":           latitude,
        "longitude":          longitude,
        "zoom":               zoom,
        "image_description":  image_description,
        "image_prompt":       config["image_model"]["prompt"].strip(),
        "image_model":        config["image_model"]["name"],
        "text_description":   risk_result["justification"],
        "text_prompt":        config["text_model"]["prompt"].strip(),
        "text_model":         config["text_model"]["name"],
        "danger":             risk_result["danger"],
    }

    file_exists = _CSV_PATH.exists() and _CSV_PATH.stat().st_size > 0
    with open(_CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
