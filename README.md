# CelesteOS Cloud Entity Extraction

Maritime entity extraction service optimized for cloud deployment.

## Architecture

- **Flask API** on Render.com
- **Regex + spaCy** for deterministic extraction (80% queries, <50ms, $0)
- **OpenAI GPT-4** for residual extraction (20% queries, 1-3s, $0.024/query)
- **Production-ready** with health checks, metrics, rate limiting

## Pipeline

```
Text Input
  ↓
1. Text Cleaning & Normalization
  ↓
2. Regex Pattern Matching (confidence: 0.8-0.95)
  ↓
3. Coverage Controller (trigger AI if coverage < 85%)
  ↓
4. OpenAI GPT-4 Residual Extraction (conditional)
  ↓
5. Entity Merger (overlap resolution, confidence filtering)
  ↓
Output: {"equipment": [...], "model": [...], "fault_code": [...]}
```

## Entity Types

- `equipment`: Main engines, generators, pumps, compressors
- `model`: CAT 3516C, Cummins QSM11, Northern Lights M843W
- `org`: Caterpillar, Yanmar, Cummins, Fischer Panda
- `location_on_board`: Engine room, bridge, galley, lazarette
- `measurement`: 95°C, 27.6V, 1800 RPM, 3.5 bar
- `fault_code`: SPN 1234 FMI 5, WARN-335, ERR-52
- `symptom`: Overheating, vibration, leak, not starting
- `action`: Check, inspect, repair, replace, troubleshoot
- `status`: Running, failed, scheduled, alarm

## Deployment

### Local Testing

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export OPENAI_API_KEY="sk-..."
export MAX_BODY_KB=64

python api/app.py
# Runs on http://localhost:5400
```

### Render.com

1. Push to GitHub
2. Create new Web Service on Render.com
3. Set environment variables:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `MAX_BODY_KB`: 64
4. Deploy

## API Endpoints

### `POST /extract`

Extract entities from text.

**Request:**
```json
{
  "text": "CAT 3516C main engine overheating at 95°C in engine room"
}
```

**Response:**
```json
{
  "entities": {
    "equipment": ["Main Engine"],
    "model": ["CAT 3516C"],
    "org": ["Caterpillar"],
    "location_on_board": ["engine room"],
    "measurement": ["95 °C"],
    "symptom": ["overheating"]
  }
}
```

**Debug Mode:**
```json
{
  "text": "...",
  "debug": true
}
```

Returns full metadata including coverage, latency, AI invocation.

### `GET /health`

Health check with metrics.

**Response:**
```json
{
  "ok": true,
  "uptime_s": 3600,
  "requests": 1523,
  "errors": 2,
  "ai_rate": 0.18,
  "p95_ms": 45,
  "components": {
    "cleaner": "ok",
    "regex_extractor": "ok",
    "controller": "ok",
    "ai_extractor": "ok",
    "merger": "ok"
  }
}
```

### `GET /metrics`

Prometheus-compatible metrics.

## Performance

- **P95 Latency**: 45ms (regex only), 1.2s (with AI)
- **AI Invocation Rate**: 18% (82% handled by regex)
- **Cost**: ~$10/month OpenAI + $7/month Render.com = $17/month

## Migration from Local

Replaced:
- ❌ Ollama qwen2.5:3b (localhost) → ✅ OpenAI GPT-4 Turbo (cloud)
- ❌ BGE-LARGE embeddings → ✅ N/A (entity extraction doesn't use embeddings)
- ❌ BM25 search → ✅ N/A (document search is separate system)

Kept:
- ✅ Regex patterns (1000+ maritime equipment patterns)
- ✅ spaCy NER (en_core_web_sm)
- ✅ Entity merger with confidence scoring
- ✅ Overlap resolution algorithm
- ✅ Canonical normalization

## License

Proprietary - CelesteOS
