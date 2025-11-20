# Predictive Maintenance Engine - Architecture Diagrams

This document contains Mermaid diagrams illustrating the architecture of the CelesteOS Predictive Maintenance Engine.

---

## System Overview

```mermaid
graph TB
    subgraph "Data Sources"
        DB[(Supabase PostgreSQL)]
        Faults[Faults Table]
        WO[Work Orders]
        Parts[Parts & Inventory]
        Searches[Search Queries]
        Notes[Notes Table]
        Graph[Graph Edges/Nodes]
    end

    subgraph "Predictive Engine"
        SC[Signal Collectors]
        Scorer[Risk Scorer]
        AD[Anomaly Detector]
        IG[Insight Generator]
        FC[Fleet Comparator]
    end

    subgraph "Outputs"
        PS[(predictive_state)]
        PI[(predictive_insights)]
    end

    subgraph "Interfaces"
        API[REST API]
        Worker[Background Worker]
    end

    DB --> SC
    Faults --> SC
    WO --> SC
    Parts --> SC
    Searches --> SC
    Notes --> SC
    Graph --> SC

    SC --> Scorer
    Scorer --> AD
    AD --> IG
    SC --> IG
    SC --> FC
    FC --> IG

    Scorer --> PS
    IG --> PI

    API --> Scorer
    API --> IG
    Worker --> Scorer
    Worker --> IG
```

---

## Signal Collection Flow

```mermaid
flowchart LR
    subgraph "19+ Signals"
        F[Fault Signals]
        W[Work Order Signals]
        E[Equipment Behavior]
        P[Part Consumption]
        C[Crew Behavior]
        G[Global Knowledge]
        GR[Graph Signals]
    end

    subgraph "Signal Processing"
        direction TB
        Normalize[Normalize to 0-1]
        Compute[Compute Sub-Scores]
        Aggregate[Aggregate Overall]
    end

    subgraph "Weighted Scoring"
        WS[Weighted Sum]
        RS[Risk Score 0.0-1.0]
    end

    F --> Normalize
    W --> Normalize
    E --> Normalize
    P --> Normalize
    C --> Normalize
    G --> Normalize
    GR --> Normalize

    Normalize --> Compute
    Compute --> Aggregate
    Aggregate --> WS
    WS --> RS
```

---

## Risk Score Calculation

```mermaid
graph TD
    Start[Equipment ID] --> SC[Collect All Signals]

    SC --> FS[Fault Signal<br/>35% weight]
    SC --> WS[Work Order Signal<br/>25% weight]
    SC --> CS[Crew Signal<br/>15% weight]
    SC --> PS[Part Signal<br/>15% weight]
    SC --> GS[Global Signal<br/>10% weight]

    FS --> Calc[Weighted Sum]
    WS --> Calc
    CS --> Calc
    PS --> Calc
    GS --> Calc

    Calc --> Risk[Risk Score<br/>0.0 - 1.0]

    Risk --> Cat{Risk Category}

    Cat -->|0.0-0.4| Normal[Normal<br/>Monitor]
    Cat -->|0.4-0.6| Mon[Monitor<br/>Increased Attention]
    Cat -->|0.6-0.75| Emerg[Emerging Risk<br/>Inspect]
    Cat -->|0.75-1.0| High[High Risk<br/>Immediate Action]

    Risk --> Trend[Calculate Trend]
    Trend --> Save[(Save to<br/>predictive_state)]
```

---

## Anomaly Detection Process

```mermaid
flowchart TD
    Start[Equipment Data] --> Split[Split into<br/>Recent vs Baseline]

    Split --> FF[Fault Frequency<br/>Analysis]
    Split --> SP[Search Pattern<br/>Analysis]
    Split --> NC[Note Creation<br/>Analysis]
    Split --> PC[Part Consumption<br/>Analysis]
    Split --> GP[Graph Propagation<br/>Analysis]

    FF --> FFC{Spike > 2.5x?}
    SP --> SPC{Spike > 2.5x?}
    NC --> NCC{Spike > 2.5x?}
    PC --> PCC{Spike > 2.5x?}
    GP --> GPC{Growth > 50%?}

    FFC -->|Yes| A1[Fault Frequency Anomaly]
    SPC -->|Yes| A2[Search Pattern Anomaly]
    NCC -->|Yes| A3[Note Creation Anomaly]
    PCC -->|Yes| A4[Part Consumption Anomaly]
    GPC -->|Yes| A5[Graph Propagation Anomaly]

    A1 --> Collect[Collect All Anomalies]
    A2 --> Collect
    A3 --> Collect
    A4 --> Collect
    A5 --> Collect

    Collect --> Return[Return Anomaly List<br/>with Severity]
```

---

## Insight Generation Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant IG as Insight Generator
    participant SC as Signal Collector
    participant Scorer
    participant AD as Anomaly Detector
    participant FC as Fleet Comparator
    participant DB

    Client->>API: GET /v1/predictive/insights?yacht_id=X
    API->>IG: generate_insights_for_yacht(X)

    loop For each equipment
        IG->>Scorer: get_risk_state(equipment_id)
        Scorer->>DB: fetch risk_state
        DB-->>Scorer: risk_data
        Scorer-->>IG: risk_score

        alt Risk >= 0.40
            IG->>SC: compute_all_signals()
            SC-->>IG: detailed_signals
            IG->>IG: generate_fault_prediction_insight()

            IG->>IG: generate_crew_pain_insight()

            IG->>FC: compare_to_fleet()
            FC-->>IG: fleet_comparison
            IG->>IG: generate_fleet_deviation_insight()
        end

        IG->>AD: detect_all_anomalies()
        AD-->>IG: anomaly_list

        loop For each anomaly
            IG->>IG: generate_anomaly_insight()
        end

        IG->>DB: save_insight()
    end

    IG-->>API: insights_response
    API-->>Client: JSON response
```

---

## Worker / Cron Architecture

```mermaid
graph TB
    subgraph "Trigger Mechanisms"
        Cron[Cron Schedule<br/>Every 6 hours]
        Manual[Manual Trigger<br/>API Call]
        PostIndex[Post-Indexing<br/>Webhook]
    end

    subgraph "Worker Process"
        Start[Start Worker]
        GetYachts[Get All Active Yachts]
        Loop{For Each Yacht}
        Process[Process Yacht]
        Delay[Sleep 2s]
        Summary[Generate Summary]
    end

    subgraph "Per-Yacht Processing"
        Risk[Compute Risk Scores<br/>All Equipment]
        Insights[Generate Insights<br/>All Equipment]
        Save[Save to Database]
    end

    Cron --> Start
    Manual --> Start
    PostIndex --> Start

    Start --> GetYachts
    GetYachts --> Loop
    Loop -->|Next| Process
    Process --> Risk
    Risk --> Insights
    Insights --> Save
    Save --> Delay
    Delay --> Loop
    Loop -->|Done| Summary
```

---

## API Request Flow

```mermaid
sequenceDiagram
    participant Client
    participant API as API Gateway
    participant Auth as Authentication
    participant Router as Risk Router
    participant Scorer
    participant DB as Supabase

    Client->>API: POST /v1/predictive/run<br/>Headers: X-Yacht-Signature, JWT
    API->>Auth: Validate Headers

    alt Invalid Auth
        Auth-->>Client: 401 Unauthorized
    else Valid Auth
        Auth->>Router: Forward Request
        Router->>Scorer: compute_risk_for_yacht()

        Scorer->>DB: get_equipment_by_yacht()
        DB-->>Scorer: equipment_list[]

        loop For each equipment
            Scorer->>Scorer: compute_all_signals()
            Scorer->>Scorer: calculate_risk_score()
            Scorer->>DB: save_risk_state()
        end

        Scorer-->>Router: {total: 42, high_risk: 3, ...}
        Router-->>API: Success Response
        API-->>Client: 200 OK + Risk Summary
    end
```

---

## Database Schema Relationships

```mermaid
erDiagram
    yachts ||--o{ equipment : has
    yachts ||--o{ predictive_state : has
    yachts ||--o{ predictive_insights : has

    equipment ||--o{ predictive_state : "risk tracked for"
    equipment ||--o{ predictive_insights : "insights for"
    equipment ||--o{ faults : has
    equipment ||--o{ work_orders : has
    equipment ||--o{ graph_nodes : represented_as

    predictive_state {
        uuid id PK
        uuid yacht_id FK
        uuid equipment_id FK
        numeric risk_score
        varchar trend
        numeric fault_signal
        numeric work_order_signal
        numeric crew_signal
        numeric part_signal
        numeric global_signal
        timestamptz updated_at
    }

    predictive_insights {
        uuid id PK
        uuid yacht_id FK
        uuid equipment_id FK
        varchar insight_type
        varchar severity
        text summary
        text explanation
        text recommended_action
        jsonb contributing_signals
        timestamptz created_at
    }

    graph_nodes ||--o{ graph_edges : from
    graph_nodes ||--o{ graph_edges : to
```

---

## Data Flow: NAS to Predictions

```mermaid
flowchart TD
    NAS[Yacht NAS] --> Agent[Local Agent]
    Agent --> Upload[Upload Documents]
    Upload --> S3[Object Storage]
    S3 --> Index[Indexing Pipeline]
    Index --> Chunks[(document_chunks)]

    Crew[Crew Actions] --> WO[(work_orders)]
    Crew --> Faults[(faults)]
    Crew --> Notes[(notes)]
    Crew --> Searches[(search_queries)]

    Chunks --> Signals[Signal Collectors]
    WO --> Signals
    Faults --> Signals
    Notes --> Signals
    Searches --> Signals

    Signals --> Scorer[Risk Scorer]
    Scorer --> Risk[(predictive_state)]

    Risk --> Insights[Insight Generator]
    Signals --> Insights
    Insights --> PI[(predictive_insights)]

    PI --> Search[Search Engine]
    PI --> Handover[Handover System]
    PI --> Mobile[Mobile App]
    PI --> Web[Web Dashboard]
```

---

## Deployment Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        Mobile[Mobile Apps]
        Web[Web Dashboard]
    end

    subgraph "Load Balancer"
        LB[Traefik/Nginx]
    end

    subgraph "Application Layer"
        API1[Predictive API<br/>Instance 1]
        API2[Predictive API<br/>Instance 2]
        API3[Predictive API<br/>Instance 3]
    end

    subgraph "Worker Layer"
        Worker1[Worker<br/>Cron Job]
        Worker2[Worker<br/>On-Demand]
    end

    subgraph "Data Layer"
        Supabase[(Supabase<br/>PostgreSQL + pgvector)]
        S3[Object Storage]
    end

    subgraph "Monitoring"
        Prom[Prometheus]
        Graf[Grafana]
        Loki[Loki Logs]
    end

    Mobile --> LB
    Web --> LB
    LB --> API1
    LB --> API2
    LB --> API3

    API1 --> Supabase
    API2 --> Supabase
    API3 --> Supabase

    Worker1 --> Supabase
    Worker2 --> Supabase

    Supabase --> S3

    API1 --> Prom
    API2 --> Prom
    API3 --> Prom
    Worker1 --> Loki
    Worker2 --> Loki
    Prom --> Graf
```

---

## Signal Weight Distribution

```mermaid
pie title Risk Score Signal Weights
    "Fault Signal" : 35
    "Work Order Signal" : 25
    "Crew Behavior Signal" : 15
    "Part Consumption Signal" : 15
    "Global Knowledge Signal" : 10
```

---

## Insight Type Distribution

```mermaid
graph TD
    Insights[Predictive Insights]

    Insights --> FP[Fault Prediction]
    Insights --> AD[Anomaly Detected]
    Insights --> PS[Part Shortage]
    Insights --> CP[Crew Pain Index]
    Insights --> MO[Maintenance Overdue]
    Insights --> CR[Cascade Risk]
    Insights --> FD[Fleet Deviation]

    FP --> Sev1{Severity}
    AD --> Sev2{Severity}
    PS --> Sev3{Severity}
    CP --> Sev4{Severity}
    MO --> Sev5{Severity}
    CR --> Sev6{Severity}
    FD --> Sev7{Severity}

    Sev1 --> Action[Recommended Actions]
    Sev2 --> Action
    Sev3 --> Action
    Sev4 --> Action
    Sev5 --> Action
    Sev6 --> Action
    Sev7 --> Action

    Action --> WO[Create Work Order]
    Action --> Hand[Add to Handover]
    Action --> Order[Order Parts]
    Action --> Inspect[Inspect Equipment]
```

---

## State Machine: Risk Progression

```mermaid
stateDiagram-v2
    [*] --> Normal: Initial State
    Normal --> Monitor: Risk increases to 0.40+
    Monitor --> Normal: Risk decreases
    Monitor --> Emerging: Risk increases to 0.60+
    Emerging --> Monitor: Risk decreases
    Emerging --> High: Risk increases to 0.75+
    High --> Emerging: Risk decreases
    High --> Critical: Equipment failure
    Critical --> [*]: Equipment replaced/repaired

    Normal: Risk < 0.40<br/>Status: OK
    Monitor: Risk 0.40-0.60<br/>Status: Watch
    Emerging: Risk 0.60-0.75<br/>Status: Inspect Soon
    High: Risk 0.75+<br/>Status: Urgent Action
    Critical: Risk 1.0<br/>Status: Failed
```

---

## End-to-End: From Data to Action

```mermaid
journey
    title Equipment Failure Prevention Journey
    section Data Collection
      Crew reports issue: 3: Crew
      Fault logged: 5: System
      Work order created: 4: Crew
      Notes added: 3: Crew
      Parts replaced: 4: Crew
    section Signal Processing
      Signals collected: 5: Worker
      Risk computed: 5: Worker
      Anomaly detected: 5: Worker
    section Insight Generation
      Insight created: 5: Worker
      Severity assigned: 4: Worker
      Recommendation made: 5: Worker
    section Crew Response
      Alert received: 5: Crew
      Equipment inspected: 4: Crew
      Preventive action taken: 5: Crew
      Failure prevented: 5: Crew
```

---

These diagrams provide a comprehensive visual representation of the Predictive Maintenance Engine's architecture, data flows, and operational processes.
