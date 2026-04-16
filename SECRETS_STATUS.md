# GitHub Secrets Status Report
Generated: 2026-04-16

## Required Secrets for Workflows

### Backend Deployment (deploy-backend.yml)
- ✅ GCP_SA_KEY
- ✅ SUPABASE_URL
- ✅ SUPABASE_KEY
- ✅ SUPABASE_SERVICE_ROLE_KEY
- ✅ SUPABASE_JWT_SECRET
- ✅ GOOGLE_CLIENT_ID
- ⚠️ GOOGLE_CLIENT_SECRET (network timeout - needs manual retry)
- ✅ AZURE_DOC_INTELLIGENCE_KEY
- ✅ AZURE_DOC_INTELLIGENCE_ENDPOINT
- ✅ GOOGLE_CLOUD_VISION_KEY

### Frontend Deployment (deploy-frontend.yml)
- ✅ VERCEL_TOKEN
- ✅ VERCEL_ORG_ID (team_364mQ4Ff9C37VgacDjzpN6WL)
- ✅ VERCEL_PROJECT_ID (prj_DpZF3Grcc5A3ghsA6TlpWIUAg7Wj)

### Additional Secrets
- ✅ OCR_SPACE_API_KEY

## Secrets Successfully Set (13/14)
1. ✅ AZURE_DOC_INTELLIGENCE_ENDPOINT
2. ✅ AZURE_DOC_INTELLIGENCE_KEY
3. ✅ GCP_SA_KEY
4. ✅ GOOGLE_CLIENT_ID
5. ⚠️ GOOGLE_CLIENT_SECRET (PENDING - network issue)
6. ✅ GOOGLE_CLOUD_VISION_KEY
7. ✅ OCR_SPACE_API_KEY
8. ✅ SUPABASE_JWT_SECRET
9. ✅ SUPABASE_KEY
10. ✅ SUPABASE_SERVICE_ROLE_KEY
11. ✅ SUPABASE_URL
12. ✅ VERCEL_ORG_ID
13. ✅ VERCEL_PROJECT_ID
14. ✅ VERCEL_TOKEN

## Action Required

### GOOGLE_CLIENT_SECRET
**Status:** Failed to set due to network connectivity issue with GitHub API (20.205.243.168:443)

**Value:** `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`

**To set manually when network is stable:**
```bash
echo "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" | gh secret set GOOGLE_CLIENT_SECRET
```

Or via GitHub web interface:
1. Go to: https://github.com/CodeCraftsmaniac/CSE226-Project-2/settings/secrets/actions
2. Click "New repository secret"
3. Name: `GOOGLE_CLIENT_SECRET`
4. Value: `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`
5. Click "Add secret"

## All Values Stored in .env File
All secret values are safely stored in the root `.env` file for local development.
The `.env` file is in `.gitignore` and will not be committed.
