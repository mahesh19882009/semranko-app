# DataForSEO Integration Guide

## Why DataForSEO? (Best Option for Rank Tracking)

We've chosen **DataForSEO** as the primary SERP API provider because:

### ✅ Advantages over competitors:
1. **Cost-Effective**: Pay-per-use model starting at $0.0012 per result
2. **Comprehensive Data**: Returns detailed SERP features (featured snippets, local packs, people also ask, etc.)
3. **Global Coverage**: 83+ million keywords across 200+ countries
4. **Accurate Position Tracking**: Exact ranking positions with URL-level data
5. **Historical Data**: Store and compare historical rankings
6. **API Flexibility**: Both synchronous and asynchronous endpoints
7. **No Credit Card Required**: Start with free $1 credit for testing

### Comparison:
| Feature | DataForSEO | SerpAPI | ValueSERP |
|---------|-----------|---------|-----------|
| Price per 100 results | ~$0.12 | ~$0.50 | ~$0.25 |
| SERP Features | ✅ Full | ✅ Full | ⚠️ Limited |
| Free Credits | $1 | None | None |
| Async Processing | ✅ Yes | ⚠️ Limited | ❌ No |
| Documentation | ✅ Excellent | ✅ Good | ⚠️ Average |

---

## Setup Instructions

### Step 1: Create DataForSEO Account

1. Go to [https://dataforseo.com/](https://dataforseo.com/)
2. Click "Sign Up" (top right)
3. Register with your email
4. Verify your email address
5. You'll receive **$1 free credit** instantly

### Step 2: Get API Credentials

1. Log in to your DataForSEO dashboard
2. Navigate to **Account Settings** → **API Credentials**
3. You'll see:
   - **Login**: Your registered email address
   - **Password**: Your API key (click "Generate" if not visible)

### Step 3: Configure Environment Variables

Edit `/workspace/api/.env`:

```bash
# Add these lines with your actual credentials
SERP_API_LOGIN=your_email@example.com
SERP_API_KEY=your_api_password_from_dashboard
```

### Step 4: Test the Integration

Run a test rank check:

```bash
cd /workspace/api/fastapi_app

# Make sure dependencies are installed
pip install requests

# The integration will automatically use DataForSEO when both 
# SERP_API_LOGIN and SERP_API_KEY are set
```

### Step 5: Monitor Usage

1. Check your usage in the DataForSEO dashboard
2. Set up budget alerts to avoid unexpected charges
3. Typical usage: 100 keywords = ~$0.12 per check

---

## How It Works

### Rank Check Flow:

```
User adds keyword
    ↓
Scheduler triggers rank check (daily/hourly)
    ↓
Worker calls DataForSEO API
    ↓
API returns SERP data (top 100 results)
    ↓
System finds your domain in results
    ↓
Stores position, URL, and SERP features
    ↓
Updates dashboard with new ranking
```

### What Gets Tracked:

- **Position**: Exact ranking (1-100) or `null` if not ranking
- **URL**: The specific page URL that ranks
- **Featured Snippet**: Boolean flag if you own position 0
- **Local Pack**: Boolean flag if you appear in local 3-pack
- **Location**: Geographic targeting (India, US, UK, etc.)
- **Device**: Desktop or Mobile rankings

---

## Fallback Behavior

The system has intelligent fallback:

1. **Primary**: DataForSEO (if `SERP_API_LOGIN` + `SERP_API_KEY` set)
2. **Secondary**: SerpAPI (if only `SERP_API_KEY` set)
3. **Fallback**: Mock data (for development/testing)

This ensures the app always works, even without API keys.

---

## Cost Estimation

### Example Scenario:
- **10 Projects** with **50 keywords each** = 500 keywords total
- **Daily rank checks** = 500 × 30 = 15,000 checks/month
- **Cost**: 15,000 × $0.0012 = **~$18/month**

### Tips to Reduce Costs:
1. Check rankings less frequently (weekly instead of daily)
2. Only track high-priority keywords daily
3. Use mock data during development
4. Batch multiple keywords in single API calls (future optimization)

---

## API Documentation

- **Official Docs**: https://docs.dataforseo.com/
- **Google Organic SERP**: https://docs.dataforseo.com/v3/serp/google/organic/
- **Location Codes**: https://docs.dataforseo.com/v3/appendix/geo/locations/
- **PHP Code Examples**: Available in dashboard
- **Python Examples**: See `/workspace/api/fastapi_app/app/workers/tasks.py`

---

## Troubleshooting

### Common Issues:

**Issue**: "API authentication failed"
- **Solution**: Verify `SERP_API_LOGIN` is your email and `SERP_API_KEY` is correct

**Issue**: "No results returned"
- **Solution**: Domain might not rank in top 100 for that keyword (this is normal)

**Issue**: "Rate limit exceeded"
- **Solution**: DataForSEO has generous limits, but add delays between bulk requests

**Issue**: "Incorrect location results"
- **Solution**: Check location mapping in `tasks.py` and update location codes

---

## Next Steps

After setting up DataForSEO:

1. ✅ Test with a few keywords
2. ✅ Verify rankings appear in dashboard
3. ✅ Set up scheduler for automatic daily checks
4. ✅ Configure notifications for rank changes
5. 📊 Analyze ranking trends over time

---

## Support

- DataForSEO Support: support@dataforseo.com
- Live Chat: Available on their website
- Documentation: https://docs.dataforseo.com/
