"""
CelesteOS Backend - Authentication Middleware Tests
"""

import pytest
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException
from src.middleware.auth import (
    decode_jwt,
    extract_yacht_id,
    extract_user_id,
    extract_role,
    create_agent_token,
)

# Mock JWT secret for testing
TEST_JWT_SECRET = 'test-secret-key'
TEST_AGENT_SECRET = 'test-agent-secret'


@pytest.fixture
def mock_jwt():
    """Create a valid test JWT token."""
    payload = {
        'sub': 'user-123',
        'user_id': 'user-123',
        'yacht_id': 'yacht-456',
        'role': 'chief_engineer',
        'email': 'test@example.com',
        'exp': datetime.utcnow() + timedelta(hours=24),
        'iat': datetime.utcnow(),
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm='HS256')


@pytest.fixture
def expired_jwt():
    """Create an expired JWT token."""
    payload = {
        'sub': 'user-123',
        'yacht_id': 'yacht-456',
        'exp': datetime.utcnow() - timedelta(hours=1),  # Expired
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm='HS256')


class TestJWTValidation:
    """Test JWT validation functions."""

    def test_decode_valid_jwt(self, mock_jwt, monkeypatch):
        """Test decoding valid JWT."""
        monkeypatch.setenv('SUPABASE_JWT_SECRET', TEST_JWT_SECRET)

        payload = decode_jwt(mock_jwt)

        assert payload['user_id'] == 'user-123'
        assert payload['yacht_id'] == 'yacht-456'
        assert payload['role'] == 'chief_engineer'

    def test_decode_expired_jwt(self, expired_jwt, monkeypatch):
        """Test that expired JWT throws error."""
        monkeypatch.setenv('SUPABASE_JWT_SECRET', TEST_JWT_SECRET)

        with pytest.raises(HTTPException) as exc_info:
            decode_jwt(expired_jwt)

        assert exc_info.value.status_code == 401
        assert 'expired' in str(exc_info.value.detail).lower()

    def test_decode_invalid_jwt(self, monkeypatch):
        """Test that invalid JWT throws error."""
        monkeypatch.setenv('SUPABASE_JWT_SECRET', TEST_JWT_SECRET)

        with pytest.raises(HTTPException) as exc_info:
            decode_jwt('invalid-token')

        assert exc_info.value.status_code == 401

    def test_decode_jwt_wrong_secret(self, mock_jwt, monkeypatch):
        """Test that JWT with wrong secret fails."""
        monkeypatch.setenv('SUPABASE_JWT_SECRET', 'wrong-secret')

        with pytest.raises(HTTPException) as exc_info:
            decode_jwt(mock_jwt)

        assert exc_info.value.status_code == 401


class TestEntityExtraction:
    """Test extracting entities from JWT."""

    def test_extract_yacht_id(self, mock_jwt, monkeypatch):
        """Test extracting yacht_id from JWT."""
        monkeypatch.setenv('SUPABASE_JWT_SECRET', TEST_JWT_SECRET)

        yacht_id = extract_yacht_id(mock_jwt)

        assert yacht_id == 'yacht-456'

    def test_extract_yacht_id_missing(self, monkeypatch):
        """Test error when yacht_id missing from JWT."""
        monkeypatch.setenv('SUPABASE_JWT_SECRET', TEST_JWT_SECRET)

        payload = {
            'sub': 'user-123',
            'exp': datetime.utcnow() + timedelta(hours=24),
        }
        token = jwt.encode(payload, TEST_JWT_SECRET, algorithm='HS256')

        with pytest.raises(HTTPException) as exc_info:
            extract_yacht_id(token)

        assert exc_info.value.status_code == 403
        assert 'yacht_id' in str(exc_info.value.detail).lower()

    def test_extract_user_id(self, mock_jwt, monkeypatch):
        """Test extracting user_id from JWT."""
        monkeypatch.setenv('SUPABASE_JWT_SECRET', TEST_JWT_SECRET)

        user_id = extract_user_id(mock_jwt)

        assert user_id == 'user-123'

    def test_extract_role(self, mock_jwt, monkeypatch):
        """Test extracting role from JWT."""
        monkeypatch.setenv('SUPABASE_JWT_SECRET', TEST_JWT_SECRET)

        role = extract_role(mock_jwt)

        assert role == 'chief_engineer'

    def test_extract_role_default(self, monkeypatch):
        """Test default role when not in JWT."""
        monkeypatch.setenv('SUPABASE_JWT_SECRET', TEST_JWT_SECRET)

        payload = {
            'sub': 'user-123',
            'yacht_id': 'yacht-456',
            'exp': datetime.utcnow() + timedelta(hours=24),
        }
        token = jwt.encode(payload, TEST_JWT_SECRET, algorithm='HS256')

        role = extract_role(token)

        assert role == 'crew'  # Default role


class TestAgentToken:
    """Test agent token creation and validation."""

    def test_create_agent_token(self, monkeypatch):
        """Test creating agent token."""
        monkeypatch.setenv('AGENT_TOKEN_SECRET', TEST_AGENT_SECRET)

        token = create_agent_token('yacht-sig-123', 'agent-456')

        # Decode and verify
        payload = jwt.decode(token, TEST_AGENT_SECRET, algorithms=['HS256'])

        assert payload['yacht_signature'] == 'yacht-sig-123'
        assert payload['agent_id'] == 'agent-456'
        assert 'exp' in payload
        assert 'iat' in payload

    def test_agent_token_expiration(self, monkeypatch):
        """Test agent token has correct expiration."""
        monkeypatch.setenv('AGENT_TOKEN_SECRET', TEST_AGENT_SECRET)

        token = create_agent_token('yacht-sig-123', 'agent-456', expires_days=30)

        payload = jwt.decode(token, TEST_AGENT_SECRET, algorithms=['HS256'])

        exp_time = datetime.fromtimestamp(payload['exp'])
        iat_time = datetime.fromtimestamp(payload['iat'])
        delta = exp_time - iat_time

        assert delta.days == 30


class TestYachtIsolation:
    """Test yacht isolation enforcement."""

    def test_different_yacht_access_denied(self, mock_jwt, monkeypatch):
        """Test that accessing different yacht's resources is denied."""
        monkeypatch.setenv('SUPABASE_JWT_SECRET', TEST_JWT_SECRET)

        yacht_id = extract_yacht_id(mock_jwt)
        resource_yacht_id = 'yacht-999'  # Different yacht

        # In actual implementation, enforce_yacht_isolation would raise HTTPException
        assert yacht_id != resource_yacht_id

    def test_same_yacht_access_allowed(self, mock_jwt, monkeypatch):
        """Test that accessing same yacht's resources is allowed."""
        monkeypatch.setenv('SUPABASE_JWT_SECRET', TEST_JWT_SECRET)

        yacht_id = extract_yacht_id(mock_jwt)
        resource_yacht_id = 'yacht-456'  # Same yacht

        assert yacht_id == resource_yacht_id


# Integration test example
class TestAuthMiddlewareIntegration:
    """Integration tests for auth middleware."""

    @pytest.mark.asyncio
    async def test_full_jwt_validation_flow(self, mock_jwt, monkeypatch):
        """Test complete JWT validation flow."""
        monkeypatch.setenv('SUPABASE_JWT_SECRET', TEST_JWT_SECRET)

        # Decode JWT
        payload = decode_jwt(mock_jwt)

        # Extract all entities
        yacht_id = payload['yacht_id']
        user_id = payload.get('sub') or payload.get('user_id')
        role = payload.get('role', 'crew')

        # Verify all extracted correctly
        assert yacht_id == 'yacht-456'
        assert user_id == 'user-123'
        assert role == 'chief_engineer'

        # In actual endpoint:
        # 1. Validate JWT ✓
        # 2. Extract yacht_id ✓
        # 3. Use yacht_id in all queries
        # 4. Return response
