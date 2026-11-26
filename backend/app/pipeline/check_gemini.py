"""
Verify Gemini API connectivity, list available Flash/generateContent models,
and perform one tiny test call using GEMINI_API_KEY and GEMINI_MODEL from backend/.env.

Usage:
    python -m backend.app.pipeline.check_gemini
"""

import sys

from google import genai

from backend.app.core.config import get_settings


def main() -> int:
    settings = get_settings()
    api_key = settings.GEMINI_API_KEY.strip()
    model_name = settings.GEMINI_MODEL.strip()

    if not api_key:
        print("ERROR: GEMINI_API_KEY is not set in backend/.env.")
        return 1

    try:
        client = genai.Client(api_key=api_key)
        print("1. Listing models supporting generateContent:")
        available = []
        for model in client.models.list():
            actions = getattr(model, "supported_actions", None) or []
            name = getattr(model, "name", "")
            if not actions or "generateContent" in actions:
                available.append(name)
                if "flash" in name.lower():
                    print(f"   [FLASH] {name}")

        if not available:
            print("   (No models returned)")
        else:
            print(f"   Total models listed: {len(available)}")

        if not model_name:
            print("ERROR: GEMINI_MODEL is not set in backend/.env.")
            return 1

        print(f"\n2. Running tiny test call with GEMINI_MODEL='{model_name}'...")
        response = client.models.generate_content(
            model=model_name,
            contents="Reply with exactly one Urdu word: سلام",
        )
        print(f"   Response: {(response.text or '').strip()}")
        print("SUCCESS: Gemini API check passed.")
        return 0
    except Exception as exc:
        print(f"ERROR: Gemini API check failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
