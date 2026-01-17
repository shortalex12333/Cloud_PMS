"""
Email Watcher - Test Email Generation

Phase 10: Send test emails via WRITE app to test link matching.

Usage:
    python send_test_emails.py --scenario wo_match --to x@alex-short.com
    python send_test_emails.py --scenario vendor_quote --to x@alex-short.com
    python send_test_emails.py --all --to x@alex-short.com
"""

import os
import sys
import asyncio
import argparse
import logging
from datetime import datetime

# Add parent for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from supabase import create_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('TestEmails')

# =============================================================================
# Test Scenarios
# =============================================================================

TEST_SCENARIOS = {
    'wo_match': {
        'subject': 'Re: WO-1234 Hydraulic pump replacement - parts shipped',
        'body': '''Hi,

The parts for WO-1234 have shipped and should arrive in 3 days.

Tracking number: ABC123456789

Please let me know if you need anything else.

Best regards,
Test Vendor
''',
        'description': 'Tests L1 work order ID matching',
    },

    'po_match': {
        'subject': 'PO#5678 - Invoice attached',
        'body': '''Dear Team,

Please find the invoice for PO#5678 attached.

Payment terms: Net 30

Thank you for your business.

Best regards,
Accounts
''',
        'attachments': [{'name': 'invoice_5678.pdf', 'contentType': 'application/pdf'}],
        'description': 'Tests L1 purchase order ID matching',
    },

    'vendor_quote': {
        'subject': 'Quote for generator service',
        'body': '''Hi,

Please find attached our quote for the generator annual service.

The quote is valid for 30 days.

Let me know if you have any questions.

Best regards,
Marine Services Ltd
''',
        'attachments': [{'name': 'quote_gen_service.pdf', 'contentType': 'application/pdf'}],
        'description': 'Tests L2 procurement signal matching',
    },

    'serial_match': {
        'subject': 'Parts for S/N ABC123456',
        'body': '''Hello,

We have the replacement parts for your unit with serial number ABC123456.

The following items are in stock:
- Filter element
- O-ring kit
- Gasket set

Please confirm you want to proceed with the order.

Regards,
Parts Department
''',
        'description': 'Tests L3 serial number matching',
    },

    'part_number': {
        'subject': 'Availability check: Part CAT-12345',
        'body': '''Hi Team,

Checking availability of part number CAT-12345 for your vessel.

We have 5 units in stock, lead time 2-3 days.

Price: $245.00 each

Best,
Supplier
''',
        'description': 'Tests L3 part number matching',
    },

    'ambiguous': {
        'subject': 'Follow up on recent order',
        'body': '''Hi,

Just following up on our recent discussion.

Can you confirm the status of the order?

Thanks,
Vendor
''',
        'description': 'Tests L5 ambiguous/no match case',
    },

    'service_report': {
        'subject': 'Service completed - Main engine',
        'body': '''Dear Captain,

Please find attached the service report for the main engine inspection completed today.

All findings are documented in the report.

Please review and sign off.

Best regards,
Marine Tech Services
''',
        'attachments': [{'name': 'service_report_main_engine.pdf', 'contentType': 'application/pdf'}],
        'description': 'Tests L2 service signal matching',
    },
}


# =============================================================================
# Email Sending
# =============================================================================

class TestEmailSender:
    """Send test emails using Microsoft Graph API (WRITE app)."""

    GRAPH_URL = "https://graph.microsoft.com/v1.0"

    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.access_token = None

    async def get_write_token(self, user_id: str, yacht_id: str) -> str:
        """Get WRITE app access token for sending."""
        # Query auth_microsoft_tokens for write token
        result = self.supabase.table('auth_microsoft_tokens').select(
            'microsoft_access_token, token_expires_at'
        ).eq('user_id', user_id).eq('yacht_id', yacht_id).eq(
            'token_purpose', 'write'
        ).single().execute()

        if result.data:
            return result.data['microsoft_access_token']

        raise ValueError("No WRITE token found. User must authorize WRITE app first.")

    async def send_email(
        self,
        to_address: str,
        subject: str,
        body: str,
        attachments: list = None
    ) -> dict:
        """
        Send email via Microsoft Graph API.

        Args:
            to_address: Recipient email
            subject: Email subject
            body: Email body (plain text)
            attachments: Optional list of attachment metadata

        Returns:
            Send result
        """
        if not self.access_token:
            raise ValueError("Access token not set. Call get_write_token first.")

        # Build message
        message = {
            'message': {
                'subject': subject,
                'body': {
                    'contentType': 'Text',
                    'content': body,
                },
                'toRecipients': [
                    {
                        'emailAddress': {
                            'address': to_address,
                        }
                    }
                ],
            },
            'saveToSentItems': True,
        }

        # Note: For real attachments, you'd need to upload file content
        # This just includes metadata for testing the attachment detection

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.GRAPH_URL}/me/sendMail",
                headers={
                    'Authorization': f'Bearer {self.access_token}',
                    'Content-Type': 'application/json',
                },
                json=message,
                timeout=30.0,
            )

            if response.status_code == 202:
                return {'success': True, 'status': 'sent'}
            else:
                return {
                    'success': False,
                    'status_code': response.status_code,
                    'error': response.text[:500],
                }


# =============================================================================
# Main
# =============================================================================

async def run_scenario(
    sender: TestEmailSender,
    scenario_name: str,
    to_address: str
) -> dict:
    """Run a single test scenario."""
    if scenario_name not in TEST_SCENARIOS:
        return {'error': f'Unknown scenario: {scenario_name}'}

    scenario = TEST_SCENARIOS[scenario_name]

    logger.info(f"Sending scenario: {scenario_name}")
    logger.info(f"  Description: {scenario['description']}")
    logger.info(f"  Subject: {scenario['subject']}")

    result = await sender.send_email(
        to_address=to_address,
        subject=scenario['subject'],
        body=scenario['body'],
        attachments=scenario.get('attachments'),
    )

    if result.get('success'):
        logger.info(f"  ✓ Email sent successfully")
    else:
        logger.error(f"  ✗ Failed: {result.get('error', 'Unknown error')}")

    return result


async def main():
    parser = argparse.ArgumentParser(description='Send test emails for link matching')
    parser.add_argument('--scenario', help='Scenario to run', choices=TEST_SCENARIOS.keys())
    parser.add_argument('--all', action='store_true', help='Run all scenarios')
    parser.add_argument('--to', required=True, help='Recipient email address')
    parser.add_argument('--user-id', help='User ID for token lookup')
    parser.add_argument('--yacht-id', help='Yacht ID for token lookup')
    parser.add_argument('--list', action='store_true', help='List available scenarios')

    args = parser.parse_args()

    if args.list:
        print("\nAvailable test scenarios:\n")
        for name, scenario in TEST_SCENARIOS.items():
            print(f"  {name}:")
            print(f"    {scenario['description']}")
            print(f"    Subject: {scenario['subject'][:50]}...")
            print()
        return

    if not args.scenario and not args.all:
        parser.error("Either --scenario or --all is required")

    # Initialize
    supabase_url = os.getenv('SUPABASE_URL', 'https://vzsohavtuotocgrfkfyd.supabase.co')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')

    if not supabase_key:
        logger.error("SUPABASE_SERVICE_KEY environment variable required")
        return

    supabase = create_client(supabase_url, supabase_key)
    sender = TestEmailSender(supabase)

    # Get token
    user_id = args.user_id or os.getenv('TEST_USER_ID', '85fe1119-b04c-41ac-80f1-829d23322598')
    yacht_id = args.yacht_id or os.getenv('TEST_YACHT_ID', '85fe1119-b04c-41ac-80f1-829d23322598')

    try:
        sender.access_token = await sender.get_write_token(user_id, yacht_id)
        logger.info(f"Got WRITE token for user {user_id[:8]}...")
    except Exception as e:
        logger.error(f"Failed to get token: {e}")
        logger.info("Make sure the user has authorized the WRITE app")
        return

    # Run scenarios
    results = {}

    if args.all:
        for name in TEST_SCENARIOS:
            results[name] = await run_scenario(sender, name, args.to)
            await asyncio.sleep(2)  # Delay between sends
    else:
        results[args.scenario] = await run_scenario(sender, args.scenario, args.to)

    # Summary
    print("\n" + "=" * 60)
    print("Test Email Summary")
    print("=" * 60)
    for name, result in results.items():
        status = "✓ Sent" if result.get('success') else "✗ Failed"
        print(f"  {name}: {status}")


if __name__ == '__main__':
    asyncio.run(main())
