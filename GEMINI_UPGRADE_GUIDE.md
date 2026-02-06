# Fix Gemini API - Library Upgrade Required

## Problem
The current code uses **deprecated `google.generativeai`** library which:
- Uses v1beta API (old)
- Does NOT support modern Gemini models
- Returns 404 for: `gemini-pro`, `gemini-1.5-flash`, `gemini-2.0-flash`

## Solution

### Step 1: Uninstall Old Library
```bash
pip uninstall -y google-generativeai
```

### Step 2: Install New Library
```bash
pip install google-genai
```

### Step 3: Update Code
File: `d:/hackathon_zero/src/agents/file_processor.py`

**Change Line 6:**
```python
# OLD:
import google.generativeai as genai

# NEW:
from google import genai
```

**Change Line 28-29:**
```python
# OLD:
genai.configure(api_key=self.api_key)
self.model = genai.GenerativeModel('gemini-1.5-flash')

# NEW:
client = genai.Client(api_key=self.api_key)
self.model = client.models.generate_content
self.model_name = 'gemini-1.5-flash'
```

**Change Line 112:**
```python
# OLD:
response = self.model.generate_content(contents=content)

# NEW:
response = self.model(model=self.model_name, contents=content)
```

### Step 4: Test
```bash
Start-Process python -ArgumentList "-m src.cli.main start" -WorkingDirectory "d:/hackathon_zero" -NoNewWindow
```

Drop a file in `/Inbox` and check `/Done` folder.

---

**Alternative: Keep Mock Mode**
If library upgrade is not possible right now, Mock Mode already works perfectly for demo purposes.
