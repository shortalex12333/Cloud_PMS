/**
 * Quick test of /search endpoint to understand response structure
 */

const https = require('https');
const fs = require('fs');

const authToken = fs.readFileSync('.auth/access_token.txt', 'utf8').trim();

const queries = [
  "create a work order",
  "generator is overheating",
  "show me work orders"
];

async function testSearch(query) {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({
      query: query
    });

    const options = {
      hostname: 'pipeline-core.int.celeste7.ai',
      port: 443,
      path: '/search',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData),
        'Authorization': `Bearer ${authToken}`
      }
    };

    const req = https.request(options, (res) => {
      let data = '';

      res.on('data', (chunk) => {
        data += chunk;
      });

      res.on('end', () => {
        resolve({
          status: res.statusCode,
          headers: res.headers,
          body: data ? JSON.parse(data) : null
        });
      });
    });

    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

async function main() {
  console.log('\n🔍 TESTING /search ENDPOINT\n');
  console.log('='.repeat(80));

  for (const query of queries) {
    console.log(`\n📝 Query: "${query}"`);
    console.log('-'.repeat(80));

    try {
      const result = await testSearch(query);
      console.log(`Status: ${result.status}`);
      console.log('\nResponse:');
      console.log(JSON.stringify(result.body, null, 2));
      console.log('\n' + '='.repeat(80));
    } catch (error) {
      console.error('Error:', error);
    }

    // Wait a bit between requests
    await new Promise(resolve => setTimeout(resolve, 500));
  }
}

main().catch(console.error);
