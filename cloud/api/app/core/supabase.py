"""
Supabase client wrapper for CelesteOS Cloud API
Provides database and storage access
"""

from supabase import create_client, Client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Wrapper for Supabase client with connection management"""

    def __init__(self):
        """Initialize Supabase client"""
        self._client: Client = None
        self._service_client: Client = None
        self._initialize()

    def _initialize(self):
        """Create Supabase clients"""
        try:
            # Client with anon key (for user-scoped operations)
            self._client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_ANON_KEY
            )

            # Client with service role key (for admin operations)
            self._service_client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY
            )

            logger.info("Supabase clients initialized")

        except Exception as e:
            logger.error(f"Failed to initialize Supabase clients: {e}")
            raise

    @property
    def client(self) -> Client:
        """Get standard client"""
        return self._client

    @property
    def admin(self) -> Client:
        """Get admin client (service role)"""
        return self._service_client

    def health_check(self):
        """Check Supabase connection"""
        try:
            # Simple query to test connection
            response = self._service_client.table('yachts').select('id').limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"Supabase health check failed: {e}")
            raise

    # Database helpers

    def get_yacht_by_signature(self, signature: str):
        """Get yacht by signature"""
        response = self._service_client.table('yachts') \
            .select('*') \
            .eq('signature', signature) \
            .eq('status', 'active') \
            .single() \
            .execute()

        if not response.data:
            return None

        return response.data

    def verify_token(self, access_token: str):
        """Verify user access token"""
        response = self._service_client.table('user_tokens') \
            .select('*') \
            .eq('access_token', access_token) \
            .gt('expires_at', 'now()') \
            .single() \
            .execute()

        if not response.data:
            return None

        return response.data

    def get_user(self, user_id: str):
        """Get user by ID"""
        response = self._service_client.table('users') \
            .select('*') \
            .eq('id', user_id) \
            .single() \
            .execute()

        if not response.data:
            return None

        return response.data

    def create_user_token(self, user_id: str, yacht_id: str, access_token: str,
                          refresh_token: str, expires_at: str):
        """Create user token record"""
        response = self._service_client.table('user_tokens').insert({
            'user_id': user_id,
            'yacht_id': yacht_id,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_at': expires_at
        }).execute()

        return response.data[0] if response.data else None

    def revoke_token(self, access_token: str):
        """Revoke user token"""
        response = self._service_client.table('user_tokens') \
            .delete() \
            .eq('access_token', access_token) \
            .execute()

        return response.data

    # Storage helpers

    def upload_file(self, bucket: str, path: str, file_data: bytes,
                    content_type: str = 'application/octet-stream'):
        """Upload file to storage"""
        response = self._service_client.storage \
            .from_(bucket) \
            .upload(path, file_data, {'content-type': content_type})

        return response

    def download_file(self, bucket: str, path: str):
        """Download file from storage"""
        response = self._service_client.storage \
            .from_(bucket) \
            .download(path)

        return response

    def delete_file(self, bucket: str, path: str):
        """Delete file from storage"""
        response = self._service_client.storage \
            .from_(bucket) \
            .remove([path])

        return response

    def list_files(self, bucket: str, path: str = ''):
        """List files in storage"""
        response = self._service_client.storage \
            .from_(bucket) \
            .list(path)

        return response


# Global Supabase client instance
supabase_client = SupabaseClient()
