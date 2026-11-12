import asyncio
import edge_tts
import os

# Voice mappings for Pakistani Urdu & English Anchors
VOICE_MAP = {
    ("ur", "Anchor_A"): "ur-PK-UzmaNeural",   # Female Urdu Anchor
    ("ur", "Anchor_B"): "ur-PK-AsadNeural",   # Male Urdu Anchor
    ("en", "Anchor_A"): "en-US-AvaNeural",    # Female English Anchor
    ("en", "Anchor_B"): "en-US-AndrewNeural", # Male English Anchor
}

async def generate_speech(text: str, language: str = "ur", anchor: str = "Anchor_A", output_filepath: str = "output.mp3") -> str:
    """
    Generates high quality neural audio using Microsoft Edge-TTS (100% Free).
    Returns path to the saved MP3 file.
    """
    voice = VOICE_MAP.get((language, anchor), "ur-PK-UzmaNeural" if language == "ur" else "en-US-AndrewNeural")
    os.makedirs(os.path.dirname(os.path.abspath(output_filepath)), exist_ok=True)
    
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_filepath)
    return output_filepath

if __name__ == "__main__":
    test_text_ur = "السلام علیکم! نیوز سٹوڈیو میں خوش آمدید۔ آج کی اہم خبروں کے ساتھ میں ہوں عظمیٰ۔"
    asyncio.run(generate_speech(test_text_ur, language="ur", anchor="Anchor_A", output_filepath="./test_ur.mp3"))
    print("Urdu TTS test completed.")
