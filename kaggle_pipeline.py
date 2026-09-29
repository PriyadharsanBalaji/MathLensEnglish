import fitz
import ollama
import subprocess
import os

print("--- Extracting text from 5 pages ---")
doc = fitz.open("iemh101.pdf")
full_book_text = ""
num_pages = min(5, len(doc))
for i in range(num_pages):
    full_book_text += doc[i].get_text() + "\n\n"

# ---------------------------------------------------------
# STEP 1 & 3: Storyboarding (using Qwen)
# ---------------------------------------------------------
storyboard_prompt = f"""
You are an expert math teacher. Read the following text from a math book and create ONE comprehensive, continuous Manim storyboard that explains the core concepts and problems found in the text.

The text is: 
{full_book_text}

Follow this exact format for the audio list:
## Audio Generation List
| Scene | Filename | Narration Text | Duration | Speaker | Emotion |
| 1 | audio_001_intro.wav | "Hello, let's explore these concepts." | | xiaoxiao | calm |
| 2 | audio_002_step1.wav | "First, we look at..." | | xiaoxiao | calm |

Also clearly describe the visual animations for each scene.
"""

print("Generating Unified Storyboard with Qwen2.5...")
response = ollama.chat(model='qwen2.5:14b', messages=[{'role': 'user', 'content': storyboard_prompt}])
storyboard_content = response['message']['content']

storyboard_file = "storyboard_full_book.md"
with open(storyboard_file, "w", encoding="utf-8") as f:
    f.write(storyboard_content)

# ---------------------------------------------------------
# STEP 4: Generate TTS Audio
# ---------------------------------------------------------
print("Generating TTS and Sync Points...")
os.makedirs("audio", exist_ok=True)
subprocess.run(["python", "scripts/generate_tts.py", storyboard_file, "./audio", "--voice", "xiaoxiao"])

# ---------------------------------------------------------
# STEP 5: Validate Audio
# ---------------------------------------------------------
print("Validating Audio...")
subprocess.run(["python", "scripts/validate_audio.py", storyboard_file, "./audio"])

# ---------------------------------------------------------
# STEP 6 & 7: Generate Manim Code (using Manim-Coder)
# ---------------------------------------------------------
print("Generating Manim Code with manim-coder...")
with open("templates/script_scaffold.py", "r", encoding="utf-8") as f:
    scaffold = f.read()
    
code_prompt = f"""
You are an expert in Manim animation. I will give you a storyboard and a python scaffold.
You must fill in the TODOs in the scaffold to create a working Manim scene called MathScene.

Storyboard:
{storyboard_content}

Scaffold:
{scaffold}
"""

response = ollama.chat(model='maternion/manim-coder', messages=[{'role': 'user', 'content': code_prompt}])
manim_code = response['message']['content']

if "```python" in manim_code:
    manim_code = manim_code.split("```python")[1].split("```")[0]
    
script_file = "script.py"
with open(script_file, "w", encoding="utf-8") as f:
    f.write(manim_code)

# ---------------------------------------------------------
# STEP 8: Check and Render
# ---------------------------------------------------------
print("Checking and Rendering Video...")
subprocess.run(["python", "scripts/render.py", "-f", script_file, "-s", "MathScene", "-q", "m", "--no-preview"])
print("✅ Finished Processing Entire Book!")
