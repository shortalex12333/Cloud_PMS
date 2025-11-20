# CelesteOS Predictive Maintenance Engine

**Version:** 1.0.0
**Status:** Production-Ready
**Architecture:** Statistical & Rule-Based (V1 - No ML)

---

## Overview

The CelesteOS Predictive Maintenance Engine is a cloud-based microservice that analyzes yacht equipment data to predict failures before they occur. It combines 19+ signals from multiple data sources to compute risk scores, detect anomalies, and generate actionable insights.

### Key Features

- **19+ Signal Analysis** - Fault patterns, work orders, crew behavior, parts, global knowledge, and graph relationships
- **Weighted Risk Scoring** - 0.0-1.0 risk scores using scientifically-weighted formula
- **Anomaly Detection** - Statistical detection of unusual patterns and spikes
- **Insight Generation** - Human-readable explanations with recommendations
- **Fleet Comparisons** - Anonymized benchmarking against fleet averages
- **REST API** - FastAPI-based endpoints for integration
- **Background Worker** - 6-hour cron jobs for automated processing
- **Per-Yacht Isolation** - Complete data isolation with RLS

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Predictive Maintenance Engine               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐    │
│  │   Signal    │  │   Scoring    │  │    Anomaly      │    │
│  │ Collectors  │─▶│    Engine    │─▶│   Detection     │    │
│  └─────────────┘  └──────────────┘  └─────────────────┘    │
│                           │                    │              │
│                           ▼                    ▼              │
│                    ┌──────────────────────────────┐          │
│                    │   Insight Generator          │          │
│                    └──────────────────────────────┘          │
│                                  │                            │
│                                  ▼                            │
│                    ┌──────────────────────────────┐          │
│                    │   Supabase PostgreSQL        │          │
│                    │   (predictive_state,         │          │
│                    │    predictive_insights)      │          │
│                    └──────────────────────────────┘          │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Signal Categories

### 1. Fault Signals (35% weight)
- Fault frequency
- Recency patterns
- Fault code clustering
- Severity distribution
- Fault cascade chains

### 2. Work Order Signals (25% weight)
- Overdue tasks
- Repeated corrective maintenance
- Reappearing tasks (<90 days)
- Partially completed work orders

### 3. Crew Behavior Signals (15% weight)
- Search query frequency (Crew Pain Index)
- User diversity (multiple crew investigating)
- Note creation patterns
- Photo/documentation frequency

### 4. Part Consumption Signals (15% weight)
- Inventory depletion rate
- Part replacement frequency
- Abnormal consumption patterns

### 5. Global Knowledge Signals (10% weight)
- Fleet-wide fault rate comparison
- Manufacturer known issues
- Industry bulletins

### 6. Additional Signals
- Equipment behavior (MTBF)
- Graph relationships
- Operational context

---

## Risk Score Formula

```
risk_score =
  0.35 × fault_signal +
  0.25 × work_order_signal +
  0.15 × crew_activity_signal +
  0.15 × part_consumption_signal +
  0.10 × global_knowledge_signal
```

### Risk Thresholds

| Range | Category | Action |
|-------|----------|--------|
| 0.00 - 0.40 | Normal | Monitor |
| 0.40 - 0.60 | Monitor | Increased attention |
| 0.60 - 0.75 | Emerging Risk | Inspect equipment |
| 0.75 - 1.00 | High Risk | Immediate action required |

---

## Installation

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ with pgvector extension
- Supabase account (or self-hosted Supabase)
- Docker (optional, for containerized deployment)

### Environment Variables

Create a `.env` file:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# Optional: Logging
LOG_LEVEL=INFO
```

### Local Development Setup

```bash
# Clone the repository
cd predictive-engine

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
# (Execute migrations/001_create_predictive_tables.sql in Supabase SQL Editor)

# Run the web server
uvicorn main:app --reload

# Or run the worker
python worker.py run-all
```

### Docker Deployment

```bash
# Build image
docker build -t celeste-predictive:latest .

# Run web server
docker run -d \
  --name celeste-predictive \
  -p 8000:8000 \
  -e SUPABASE_URL=your-url \
  -e SUPABASE_KEY=your-key \
  celeste-predictive:latest

# Run worker (cron mode)
docker run -d \
  --name celeste-worker \
  -e SUPABASE_URL=your-url \
  -e SUPABASE_KEY=your-key \
  celeste-predictive:latest \
  python worker.py run-all
```

---

## API Endpoints

### Risk State Endpoints

#### `GET /v1/predictive/state`
Get risk states for yacht or equipment.

**Query Parameters:**
- `yacht_id` (required): Yacht UUID
- `equipment_id` (optional): Equipment UUID

**Response:**
```json
{
  "yacht_id": "uuid",
  "total_equipment": 42,
  "high_risk_count": 3,
  "emerging_risk_count": 5,
  "monitor_count": 8,
  "normal_count": 26,
  "equipment_risks": [...]
}
```

#### `POST /v1/predictive/run`
Manually trigger predictive engine run.

**Request Body:**
```json
{
  "yacht_id": "uuid",
  "equipment_id": "uuid (optional)",
  "force_recalculate": false
}
```

#### `POST /v1/predictive/run-for-yacht`
Run predictive engine for specific yacht (cron endpoint).

**Query Parameters:**
- `yacht_id` (required)
- `force_recalculate` (optional, default: false)

---

### Insights Endpoints

#### `GET /v1/predictive/insights`
Get predictive insights for yacht.

**Query Parameters:**
- `yacht_id` (required)
- `min_severity` (optional): low|medium|high|critical
- `limit` (optional, max 100)

**Response:**
```json
{
  "yacht_id": "uuid",
  "total_insights": 15,
  "critical_count": 2,
  "high_count": 4,
  "medium_count": 6,
  "low_count": 3,
  "insights": [...]
}
```

#### `POST /v1/predictive/generate-insights`
Generate new insights for yacht or equipment.

**Request Body:**
```json
{
  "yacht_id": "uuid",
  "equipment_id": "uuid (optional)",
  "min_severity": "low"
}
```

#### `GET /v1/predictive/anomalies`
Get detected anomalies for yacht.

**Response:**
```json
{
  "yacht_id": "uuid",
  "total_anomalies": 8,
  "critical_anomalies": 2,
  "anomalies": [...]
}
```

#### `GET /v1/predictive/fleet-comparison`
Get fleet comparison data.

**Query Parameters:**
- `yacht_id` (required)
- `equipment_id` (optional)

---

## Worker / Cron Jobs

The predictive worker can be run in multiple modes:

### Run for All Yachts (Scheduled Cron)
```bash
python worker.py run-all
```

### Run for Specific Yacht
```bash
python worker.py run-yacht <yacht-id>
```

### Force Recalculation
```bash
python worker.py run-all --force
```

### Kubernetes CronJob Example

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: celeste-predictive-worker
spec:
  schedule: "0 */6 * * *"  # Every 6 hours
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: worker
            image: celeste-predictive:latest
            command: ["python", "worker.py", "run-all"]
            env:
            - name: SUPABASE_URL
              valueFrom:
                secretKeyRef:
                  name: celeste-secrets
                  key: supabase-url
            - name: SUPABASE_KEY
              valueFrom:
                secretKeyRef:
                  name: celeste-secrets
                  key: supabase-key
          restartPolicy: OnFailure
```

---

## Database Schema

### `predictive_state`

Stores current risk scores for each equipment.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| yacht_id | UUID | Foreign key to yachts |
| equipment_id | UUID | Foreign key to equipment |
| risk_score | NUMERIC(5,4) | Overall risk (0.0-1.0) |
| trend | VARCHAR(1) | ↑, ↓, or → |
| fault_signal | NUMERIC(5,4) | Fault signal score |
| work_order_signal | NUMERIC(5,4) | Work order signal score |
| crew_signal | NUMERIC(5,4) | Crew behavior signal |
| part_signal | NUMERIC(5,4) | Part consumption signal |
| global_signal | NUMERIC(5,4) | Global knowledge signal |
| updated_at | TIMESTAMPTZ | Last update time |

### `predictive_insights`

Stores generated insights and recommendations.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| yacht_id | UUID | Foreign key to yachts |
| equipment_id | UUID | Foreign key to equipment |
| insight_type | VARCHAR(50) | Type of insight |
| severity | VARCHAR(20) | low, medium, high, critical |
| summary | TEXT | Short summary |
| explanation | TEXT | Detailed explanation |
| recommended_action | TEXT | Recommended action |
| contributing_signals | JSONB | Signal data |
| created_at | TIMESTAMPTZ | Creation time |

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_signals.py

# Run with verbose output
pytest -v
```

---

## Monitoring & Logging

### Health Check
```bash
curl http://localhost:8000/health
```

### Logs
Logs are written to stdout in JSON format for easy ingestion by logging services (Loki, Elastic, CloudWatch).

### Metrics
Key metrics to monitor:
- Risk computation time per yacht
- Number of high-risk equipment items
- Insight generation rate
- API response times

---

## Security

### Authentication
All endpoints require:
- `X-Yacht-Signature` header - Yacht authentication
- `Authorization: Bearer <JWT>` header - User authentication

### Row-Level Security
Database uses PostgreSQL RLS to ensure yacht data isolation.

### Data Privacy
- Fleet comparisons are fully anonymized
- No yacht identities exposed in aggregated data
- NAS access is read-only

---

## Performance

### Optimization Tips
1. **Caching**: Risk states are cached for 6 hours
2. **Batch Processing**: Worker processes multiple yachts sequentially
3. **Database Indexes**: All query-heavy columns are indexed
4. **Async Operations**: All I/O operations are asynchronous

### Scaling
- Horizontal: Deploy multiple web server instances behind load balancer
- Vertical: Increase database resources for larger fleets
- Partitioning: Consider table partitioning for yachts with massive data

---

## Future Enhancements (V2+)

### Machine Learning Integration
- LSTM models for time-series fault prediction
- Transformer models for equipment-specific patterns
- Transfer learning from global dataset

### Advanced Features
- Real-time anomaly detection (streaming)
- Automated work order generation
- Predictive part ordering
- Integration with IoT sensor data

---

## Troubleshooting

### Common Issues

**Issue:** Risk scores not updating
- Check worker cron schedule
- Verify Supabase credentials
- Check database connection

**Issue:** No insights generated
- Ensure sufficient historical data exists
- Check signal computation logs
- Verify equipment has required data

**Issue:** Fleet comparisons return null
- Need minimum 10 vessels in fleet for statistics
- Check equipment classification matches

---

## Contributing

This is a production system for CelesteOS. Contact engineering team for contribution guidelines.

---

## License

Proprietary - CelesteOS Engineering

---

## Support

For technical support, contact:
- Engineering Team: engineering@celesteos.com
- Documentation: https://docs.celesteos.com
- Issue Tracker: Internal Jira

---

## Changelog

### Version 1.0.0 (2024)
- Initial production release
- 19+ signal collectors
- Statistical risk scoring
- Anomaly detection
- Insight generation
- Fleet comparisons
- REST API
- Background worker
- PostgreSQL with RLS
- Docker support
