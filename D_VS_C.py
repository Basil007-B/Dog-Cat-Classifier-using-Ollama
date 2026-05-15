
import base64
import requests
import json
from pathlib import Path
from flask import Flask, request, Response, stream_with_context, render_template_string

app = Flask(__name__)

SUPPORTED = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
OLLAMA_URL = "http://localhost:11434/api/generate"

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>🐾 Dog or Cat?</title>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet"/>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --cream: #fdf6ec; --warm: #f5e6cc; --brown: #5c3d2e;
      --rust: #c0622f; --gold: #d4a853; --dark: #2a1a0e;
      --shadow: 0 8px 32px rgba(92,61,46,0.15);
    }
    body {
      min-height: 100vh; background: var(--cream);
      font-family: 'DM Sans', sans-serif; color: var(--dark);
      display: flex; flex-direction: column; align-items: center;
      padding: 40px 20px;
      background-image: radial-gradient(circle at 20% 20%, #f0dfc0 0%, transparent 50%),
                        radial-gradient(circle at 80% 80%, #e8d5b0 0%, transparent 50%);
    }
    header { text-align: center; margin-bottom: 40px; }
    header h1 {
      font-family: 'Playfair Display', serif;
      font-size: clamp(2rem, 5vw, 3.5rem); color: var(--brown);
    }
    header p { color: var(--rust); font-weight: 300; margin-top: 6px; font-size: 1.05rem; }
    .badge {
      display: inline-block; background: #2ecc71; color: white;
      font-size: 0.75rem; padding: 3px 10px; border-radius: 99px;
      margin-top: 8px; font-weight: 500;
    }
    .card {
      background: white; border-radius: 24px; box-shadow: var(--shadow);
      padding: 36px; width: 100%; max-width: 560px;
    }
    .drop-zone {
      border: 2.5px dashed var(--gold); border-radius: 16px;
      padding: 48px 24px; text-align: center; cursor: pointer;
      transition: all 0.25s ease; background: var(--cream); position: relative;
    }
    .drop-zone:hover, .drop-zone.active {
      border-color: var(--rust); background: var(--warm); transform: scale(1.01);
    }
    .drop-zone input[type="file"] {
      position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; height: 100%;
    }
    .drop-icon { font-size: 3rem; margin-bottom: 12px; }
    .drop-zone p { color: var(--brown); font-weight: 500; }
    .drop-zone span { color: #999; font-size: 0.85rem; }
    #preview-wrap { display: none; margin-top: 20px; text-align: center; }
    #preview {
      max-height: 280px; max-width: 100%; border-radius: 14px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.12); object-fit: contain;
    }
    button#classify-btn {
      display: block; width: 100%; margin-top: 22px; padding: 16px;
      background: var(--rust); color: white; border: none; border-radius: 12px;
      font-family: 'DM Sans', sans-serif; font-size: 1.05rem; font-weight: 500;
      cursor: pointer; transition: background 0.2s, transform 0.15s;
    }
    button#classify-btn:hover:not(:disabled) { background: var(--brown); transform: translateY(-1px); }
    button#classify-btn:disabled { opacity: 0.55; cursor: not-allowed; }
    #result-box {
      display: none; margin-top: 28px; padding: 24px;
      background: var(--cream); border-radius: 16px; border-left: 5px solid var(--gold);
    }
    .result-animal { font-family: 'Playfair Display', serif; font-size: 2rem; color: var(--brown); }
    .result-emoji { font-size: 2.8rem; margin-right: 10px; }
    .confidence-bar-wrap { margin: 14px 0 10px; }
    .confidence-label { font-size: 0.8rem; color: #888; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 1px; }
    .confidence-track { height: 10px; background: var(--warm); border-radius: 99px; overflow: hidden; }
    .confidence-fill {
      height: 100%; background: var(--rust); border-radius: 99px;
      transition: width 0.8s cubic-bezier(.4,0,.2,1); width: 0;
    }
    .explanation { font-size: 0.95rem; color: #555; margin-top: 10px; line-height: 1.6; font-style: italic; }
    .stream-text {
      font-size: 0.88rem; color: #888; margin-top: 14px; padding-top: 14px;
      border-top: 1px solid var(--warm); white-space: pre-wrap;
      line-height: 1.7; font-family: 'Courier New', monospace;
    }
    .error { color: #c0392b; margin-top: 16px; font-size: 0.9rem; }
    footer { margin-top: 40px; font-size: 0.8rem; color: #bbb; }
  </style>
</head>
<body>
<header>
  <h1>🐾 Dog or Cat?</h1>
  <p>Powered by Ollama LLaVA — runs fully on your machine</p>
  <span class="badge">✅ No API Key &nbsp;|&nbsp; 100% Free &nbsp;|&nbsp; Offline</span>
</header>

<div class="card">
  <div class="drop-zone" id="drop-zone">
    <input type="file" id="file-input" accept="image/*"/>
    <div class="drop-icon">📷</div>
    <p>Drop an image here</p>
    <span>JPG, PNG, WEBP, GIF supported</span>
  </div>
  <div id="preview-wrap"><img id="preview" alt="Preview"/></div>
  <button id="classify-btn" disabled>Classify Image</button>
  <div id="result-box">
    <div style="display:flex; align-items:center;">
      <span class="result-emoji" id="result-emoji"></span>
      <span class="result-animal" id="result-animal"></span>
    </div>
    <div class="confidence-bar-wrap">
      <div class="confidence-label">Confidence: <span id="conf-label"></span></div>
      <div class="confidence-track"><div class="confidence-fill" id="conf-fill"></div></div>
    </div>
    <div class="explanation" id="explanation"></div>
    <div class="stream-text" id="stream-text"></div>
  </div>
  <div class="error" id="error-msg"></div>
</div>

<footer>Running locally with Ollama LLaVA — no data leaves your machine 🔒</footer>

<script>
  const fileInput = document.getElementById('file-input');
  const dropZone = document.getElementById('drop-zone');
  const preview = document.getElementById('preview');
  const previewWrap = document.getElementById('preview-wrap');
  const classifyBtn = document.getElementById('classify-btn');
  const resultBox = document.getElementById('result-box');
  const errorMsg = document.getElementById('error-msg');
  let selectedFile = null;

  function handleFile(file) {
    if (!file || !file.type.startsWith('image/')) return;
    selectedFile = file;
    preview.src = URL.createObjectURL(file);
    previewWrap.style.display = 'block';
    classifyBtn.disabled = false;
    resultBox.style.display = 'none';
    errorMsg.textContent = '';
  }

  fileInput.addEventListener('change', e => handleFile(e.target.files[0]));
  dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('active'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('active'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault(); dropZone.classList.remove('active');
    handleFile(e.dataTransfer.files[0]);
  });

  classifyBtn.addEventListener('click', async () => {
    if (!selectedFile) return;
    classifyBtn.disabled = true;
    classifyBtn.textContent = 'Analyzing…';
    resultBox.style.display = 'none';
    errorMsg.textContent = '';
    document.getElementById('stream-text').textContent = '';

    const formData = new FormData();
    formData.append('image', selectedFile);

    try {
      const response = await fetch('/classify', { method: 'POST', body: formData });
      if (!response.ok) throw new Error(await response.text());

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullText = '';
      let parsed = false;

      resultBox.style.display = 'block';
      document.getElementById('stream-text').textContent = '⏳ LLaVA is thinking…';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        fullText += decoder.decode(value, { stream: true });
        document.getElementById('stream-text').textContent = fullText;
        if (!parsed && fullText.includes('EXPLANATION:')) {
          parsed = true; renderResult(fullText);
        }
      }
      if (!parsed) renderResult(fullText);

    } catch (err) {
      errorMsg.textContent = '❌ ' + err.message + ' — Is Ollama running? Try: ollama serve';
    } finally {
      classifyBtn.disabled = false;
      classifyBtn.textContent = 'Classify Image';
    }
  });

  function renderResult(text) {
    const lines = text.split('\\n');
    let animal = 'unknown', confidence = 'low', explanation = '';
    for (const line of lines) {
      if (line.startsWith('ANIMAL:')) animal = line.split(':')[1].trim().toLowerCase();
      else if (line.startsWith('CONFIDENCE:')) confidence = line.split(':')[1].trim().toLowerCase();
      else if (line.startsWith('EXPLANATION:')) explanation = line.split(':').slice(1).join(':').trim();
    }
    const emojiMap = { dog: '🐶', cat: '🐱', unknown: '❓' };
    const confMap = { high: { pct: '90%', label: 'High' }, medium: { pct: '55%', label: 'Medium' }, low: { pct: '25%', label: 'Low' } };
    const conf = confMap[confidence] || confMap.low;
    document.getElementById('result-emoji').textContent = emojiMap[animal] || '❓';
    document.getElementById('result-animal').textContent = animal.charAt(0).toUpperCase() + animal.slice(1);
    document.getElementById('conf-label').textContent = conf.label;
    document.getElementById('explanation').textContent = explanation;
    setTimeout(() => { document.getElementById('conf-fill').style.width = conf.pct; }, 100);
  }
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/classify", methods=["POST"])
def classify():
    if "image" not in request.files:
        return "No image uploaded", 400

    file = request.files["image"]
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED:
        return f"Unsupported format: {ext}", 400

    image_data = base64.standard_b64encode(file.read()).decode("utf-8")

    prompt = """Look at this image carefully and determine if it contains a dog or a cat.

Respond in this exact format:
ANIMAL: [dog/cat/unknown]
CONFIDENCE: [high/medium/low]
EXPLANATION: [one sentence describing what you see]

Rules:
- Use 'dog' if you see a dog (any breed)
- Use 'cat' if you see a cat (any breed)
- Use 'unknown' if neither animal is clearly visible"""

    def generate():
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": "llava",
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": True,
                },
                stream=True,
                timeout=120,
            )
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    yield chunk.get("response", "")
                    if chunk.get("done"):
                        break
        except requests.exceptions.ConnectionError:
            yield "\n❌ Cannot connect to Ollama. Please run: ollama serve"
        except Exception as e:
            yield f"\n❌ Error: {str(e)}"

    return Response(stream_with_context(generate()), mimetype="text/plain")


if __name__ == "__main__":
    print("🐾 Dog vs Cat Classifier (Ollama) running at http://localhost:5000")
    print("   Make sure Ollama is running: ollama serve")
    app.run(debug=True, port=5000)
