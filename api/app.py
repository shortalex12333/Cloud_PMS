#!/usr/bin/env python3
"""
CelesteOS Maritime Entity Extraction API - Cloud Version
Flask service optimized for Render.com deployment
"""

from flask import Flask, request, jsonify, Response
import logging
import time
import os
from typing import Dict, Any
from orchestrator import ExtractionOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Parameterized body size limit
MAX_BODY_KB = int(os.getenv('MAX_BODY_KB', '64'))
MAX_BODY_BYTES = MAX_BODY_KB * 1024

# Initialize Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
app.config['MAX_CONTENT_LENGTH'] = MAX_BODY_BYTES

logger.info(f"Body size limit set to {MAX_BODY_KB}KB ({MAX_BODY_BYTES} bytes)")

# Initialize orchestrator
orchestrator = ExtractionOrchestrator()

# Track metrics
startup_time = time.time()
request_count = 0
error_count = 0
p95_latencies = []


@app.route('/extract', methods=['POST'])
def extract():
    """
    Entity extraction endpoint.
    Accepts text/plain or application/json with 'text' field.
    Returns entities grouped by type as arrays of strings.

    MVP Mode (default): Returns only entities
    Debug Mode: Add {"debug": true} to get full metadata
    """
    global request_count, error_count, p95_latencies

    try:
        # Get input text and debug flag
        debug_mode = False
        if request.content_type == 'text/plain':
            text = request.get_data(as_text=True)
        elif request.content_type == 'application/json' or request.is_json:
            data = request.get_json()
            if not data or 'text' not in data:
                error_count += 1
                return jsonify({'error': 'Missing text field'}), 400
            text = data['text']
            debug_mode = data.get('debug', False)
        else:
            # Try to get raw text anyway
            text = request.get_data(as_text=True)

        if not text:
            error_count += 1
            return jsonify({'error': 'No text provided'}), 400

        # Track request
        request_count += 1
        start_time = time.time()

        # Run extraction pipeline
        result = orchestrator.extract(text)

        # Track latency
        latency = (time.time() - start_time) * 1000
        p95_latencies.append(latency)
        if len(p95_latencies) > 100:
            p95_latencies.pop(0)

        # Log extraction
        logger.info(
            f"Extraction completed - "
            f"needs_ai={result['metadata']['needs_ai']}, "
            f"coverage={result['metadata']['coverage']:.2f}, "
            f"latency={latency:.1f}ms"
        )

        # MVP Mode: Return ONLY entities (clean output)
        if not debug_mode:
            return jsonify({
                'entities': result.get('entities', {})
            }), 200
        else:
            # Debug Mode: Return full response with metadata
            return jsonify(result), 200

    except Exception as e:
        error_count += 1
        logger.error(f"Extraction error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint.
    Returns system health and metrics.
    """
    try:
        # Get component health
        health_status = orchestrator.health_check()

        # Calculate metrics
        uptime = time.time() - startup_time
        metrics = orchestrator.get_metrics()

        # Calculate P95 latency
        p95_ms = 0
        if p95_latencies:
            sorted_latencies = sorted(p95_latencies)
            p95_index = int(len(sorted_latencies) * 0.95)
            p95_ms = sorted_latencies[p95_index] if p95_index < len(sorted_latencies) else sorted_latencies[-1]

        response = {
            'ok': health_status['ok'],
            'uptime_s': round(uptime),
            'requests': request_count,
            'errors': error_count,
            'ai_rate': metrics['ai_invocation_rate'],
            'p95_ms': round(p95_ms),
            'components': health_status['components']
        }

        if 'warning' in health_status:
            response['warning'] = health_status['warning']

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500


@app.route('/metrics', methods=['GET'])
def metrics():
    """
    Prometheus-compatible metrics endpoint.
    """
    metrics_data = orchestrator.get_metrics()

    # Calculate P95
    p95_ms = 0
    if p95_latencies:
        sorted_latencies = sorted(p95_latencies)
        p95_index = int(len(sorted_latencies) * 0.95)
        p95_ms = sorted_latencies[p95_index] if p95_index < len(sorted_latencies) else sorted_latencies[-1]

    metrics_text = f"""# HELP extraction_requests_total Total extraction requests
# TYPE extraction_requests_total counter
extraction_requests_total {request_count}

# HELP extraction_errors_total Total extraction errors
# TYPE extraction_errors_total counter
extraction_errors_total {error_count}

# HELP extraction_ai_invocations_total Total AI invocations
# TYPE extraction_ai_invocations_total counter
extraction_ai_invocations_total {metrics_data['ai_invocations']}

# HELP extraction_ai_invocation_rate AI invocation rate
# TYPE extraction_ai_invocation_rate gauge
extraction_ai_invocation_rate {metrics_data['ai_invocation_rate']}

# HELP extraction_p95_latency_ms P95 extraction latency in milliseconds
# TYPE extraction_p95_latency_ms gauge
extraction_p95_latency_ms {p95_ms}

# HELP extraction_uptime_seconds API uptime in seconds
# TYPE extraction_uptime_seconds counter
extraction_uptime_seconds {round(time.time() - startup_time)}
"""
    return Response(metrics_text, mimetype='text/plain')


@app.errorhandler(404)
def not_found(e):
    """404 handler."""
    return jsonify({
        'error': 'Endpoint not found',
        'available_endpoints': [
            'POST /extract',
            'GET /health',
            'GET /metrics'
        ]
    }), 404


@app.errorhandler(413)
def payload_too_large(e):
    """Payload too large handler."""
    return jsonify({'error': f'Payload too large (max {MAX_BODY_KB}KB)'}), 413


@app.errorhandler(415)
def unsupported_media_type(e):
    """Unsupported media type handler."""
    return jsonify({
        'error': 'Unsupported content type',
        'supported': ['text/plain', 'application/json']
    }), 415


@app.errorhandler(500)
def internal_error(e):
    """500 handler."""
    logger.error(f"Internal error: {e}")
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    # Start server
    port = int(os.getenv('PORT', '5400'))

    logger.info("=" * 60)
    logger.info("CelesteOS Maritime Entity Extraction API (Cloud)")
    logger.info("=" * 60)
    logger.info("Configuration:")
    logger.info("  - Cloud service with OpenAI GPT-4 Turbo")
    logger.info("  - 5-stage pipeline: Clean → Regex → Controller → AI → Merge")
    logger.info("  - AI invoked only when coverage < 85%")
    logger.info(f"  - Max body size: {MAX_BODY_KB}KB")
    logger.info("=" * 60)
    logger.info("Endpoints:")
    logger.info("  POST /extract  - Extract entities from text")
    logger.info("  GET  /health   - Service health and metrics")
    logger.info("  GET  /metrics  - Prometheus metrics")
    logger.info("=" * 60)
    logger.info(f"Starting API server on port {port}")

    # Run Flask
    app.run(host='0.0.0.0', port=port, debug=False)
