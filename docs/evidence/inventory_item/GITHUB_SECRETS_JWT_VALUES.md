# GitHub Secrets - Clean JWT Values

**INSTRUCTIONS:** Copy each value EXACTLY as shown below (single line, no spaces before/after)

---

## STAGING_CREW_JWT

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY5NjQyMTM0LCJzdWIiOiI2ZDgwN2E2Ni05NTVjLTQ5YzQtYjc2Ny04YTYxODljMmY0MjIiLCJlbWFpbCI6ImNyZXcudGVuYW50QGFsZXgtc2hvcnQuY29tIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJlbWFpbCIsInByb3ZpZGVycyI6WyJlbWFpbCJdfSwidXNlcl9tZXRhZGF0YSI6e30sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3Njk1NTU3MzR9XSwic2Vzc2lvbl9pZCI6InRlc3Qtc2Vzc2lvbi1jcmV3IiwiaXNfYW5vbnltb3VzIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly92enNvaGF2dHVvdG9jZ3Jma2Z5ZC5zdXBhYmFzZS5jby9hdXRoL3YxIiwiaWF0IjoxNzY5NTU1NzM0fQ.JAzZAdkman1hgCONRs9pBChNx8L0PD92v7ePV8o6guQ
```

---

## STAGING_HOD_JWT

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY5NjQyMTM0LCJzdWIiOiJkNTg3M2IxZi01ZjYyLTRlM2UtYmM3OC1lMDM5NzhhZWM1YmEiLCJlbWFpbCI6ImhvZC50ZW5hbnRAYWxleC1zaG9ydC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7fSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc2OTU1NTczNH1dLCJzZXNzaW9uX2lkIjoidGVzdC1zZXNzaW9uLWhvZCIsImlzX2Fub255bW91cyI6ZmFsc2UsImlzcyI6Imh0dHBzOi8vdnpzb2hhdnR1b3RvY2dyZmtmeWQuc3VwYWJhc2UuY28vYXV0aC92MSIsImlhdCI6MTc2OTU1NTczNH0.oJTnMQeeCTUO1h-mWlOTFGdUtZsmRRvTbLmsSjjiuvo
```

---

## STAGING_CAPTAIN_JWT

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY5NjQyMTM0LCJzdWIiOiI1YWY5ZDYxZC05YjJlLTRkYjQtYTU0Yy1hM2M5NWVlYzcwZTUiLCJlbWFpbCI6ImNhcHRhaW4udGVuYW50QGFsZXgtc2hvcnQuY29tIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJlbWFpbCIsInByb3ZpZGVycyI6WyJlbWFpbCJdfSwidXNlcl9tZXRhZGF0YSI6e30sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3Njk1NTU3MzR9XSwic2Vzc2lvbl9pZCI6InRlc3Qtc2Vzc2lvbi1jYXB0YWluIiwiaXNfYW5vbnltb3VzIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly92enNvaGF2dHVvdG9jZ3Jma2Z5ZC5zdXBhYmFzZS5jby9hdXRoL3YxIiwiaWF0IjoxNzY5NTU1NzM0fQ.TprpkQbG13HyuZVwxNHUANxwKffh7_ufxbiYpbQB0LM
```

---

## How to Add to GitHub Secrets

1. Go to: https://github.com/shortalex12333/Cloud_PMS/settings/secrets/actions

2. For each secret above:
   - Click "New repository secret"
   - Name: Use the heading above (e.g., `STAGING_CREW_JWT`)
   - Value: Copy the JWT from the code block above (select entire line, copy)
   - Click "Add secret"

3. Verify:
   - No extra spaces before or after the JWT
   - No newlines
   - Starts with `eyJ` and ends with the signature

4. After all three are added, trigger the workflow:
   ```bash
   gh workflow run inventory-lens-api-acceptance.yml
   ```

---

**IMPORTANT:** These JWTs expire on 2025-06-01 (timestamp 1769642134). Regenerate before expiration.
