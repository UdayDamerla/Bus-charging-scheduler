# Deployment Guide: Streamlit Community Cloud

## Quick Deployment Steps

### 1. Push Code to GitHub

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: Electric Bus Charging Scheduler"

# Add remote (replace with your GitHub repo URL)
git remote add origin https://github.com/YOUR-USERNAME/bus-charging-scheduler.git

# Push to main branch
git push -u origin main
```

### 2. Deploy on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io/)

2. Click **"New app"**

3. Fill in:
   - **GitHub repo**: `YOUR-USERNAME/bus-charging-scheduler`
   - **Branch**: `main`
   - **Main file path**: `app.py`
   - **App URL** (custom subdomain): Choose something like `bus-scheduler-yourname`

4. Click **"Deploy"**

5. Wait 2-3 minutes for deployment

6. Your app will be live at: `https://bus-scheduler-yourname.streamlit.app`

### 3. Update README with Live URL

Once deployed, update [README.md](README.md):

```markdown
## 🚀 Live Demo

**Hosted App**: https://bus-scheduler-yourname.streamlit.app
```

## Troubleshooting

### Issue: App crashes on startup

**Solution**: Check that `requirements.txt` has the correct dependencies:
```
streamlit>=1.31.0
pandas>=2.0.0
```

### Issue: "Module not found" error

**Solution**: Make sure the file structure matches:
```
├── app.py              # Entry point
├── src/
│   └── scheduler.py    # Core logic
├── scenarios/          # Data files
├── data/
└── requirements.txt
```

### Issue: Slow loading

**Solution**: This is normal for the first load (cold start). Subsequent loads will be faster due to caching.

## Local Testing Before Deployment

Always test locally first:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run locally
streamlit run app.py
```

Visit `http://localhost:8501` to test.

## Redeployment

Streamlit Community Cloud auto-deploys on every push to main:

```bash
# Make changes to code
git add .
git commit -m "Update: [describe changes]"
git push origin main
```

Wait 1-2 minutes and refresh your app URL — changes will be live.

## Logs & Monitoring

- View app logs: Click "Manage app" → "Logs" in Streamlit Cloud dashboard
- Check app status: Green dot = running, Red = crashed

## Cost

**Streamlit Community Cloud is FREE** for public repositories with reasonable usage limits:
- 1 GB RAM per app
- Shared CPU
- Public apps only (private apps require paid tier)
