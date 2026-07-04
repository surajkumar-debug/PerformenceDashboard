# 📊 Invoice Performance Dashboard

Live performance dashboard for invoice data with user-wise, month-wise, and week-wise analysis.

## 🚀 Features

- ✅ **Live Data** - Auto-fetches from Google Sheets every 5 minutes
- ✅ **Auto Column Detection** - Detects dates, amounts, users, categories automatically
- ✅ **User-wise Analysis** - Performance breakdown per user
- ✅ **Time Analysis** - Monthly, Weekly, Quarterly, Daily trends
- ✅ **Period Comparison** - Current vs Last Month, Current vs Last Week
- ✅ **Dark Theme** - Professional enterprise UI
- ✅ **Indian Formatting** - ₹ Crore / Lakh / K notation
- ✅ **Raw Data Explorer** - Search and download filtered data

## 📁 Folder Structure

```
invoice-dashboard/
├── app.py                    # Main Streamlit app
├── requirements.txt          # Python dependencies
├── README.md                 # This file
└── .streamlit/
    └── config.toml           # Theme configuration
```

## ⚙️ Setup Instructions

### Step 1: Clone / Create Repo

```bash
# Create new folder
mkdir invoice-dashboard
cd invoice-dashboard

# Initialize git
git init
```

### Step 2: Create Files

Create all files as listed above.

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Run Locally

```bash
streamlit run app.py
```

Open browser at: `http://localhost:8501`

### Step 5: Deploy to Streamlit Cloud

1. Push code to GitHub:
```bash
git add .
git commit -m "Initial dashboard"
git push origin main
```

2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **"New App"**
4. Select your GitHub repo
5. Set **Main file path**: `app.py`
6. Click **"Deploy"**

## 🔧 Configuration

To change the Google Sheet, update these lines in `app.py`:

```python
SHEET_ID = "your_sheet_id_here"
TAB_NAME = "Data"  # Your tab name
```

### Getting Sheet ID from URL:
```
https://docs.google.com/spreadsheets/d/THIS_IS_THE_ID/edit
```

## ⚠️ Google Sheet Requirements

Make sure your sheet is:
1. **Shared**: "Anyone with the link" → Viewer
2. **Has Headers**: First row should be column names
3. **Tab Name**: Matches `TAB_NAME` in config

## 📊 Auto-Detected Column Types

| Column Type | Detection Keywords |
|-------------|-------------------|
| 📅 Date | date, dt, time, submission |
| 💰 Amount | amount, value, total, invoice, gst, tds |
| 👤 User | user, by, name, submitted_by |
| 🏷️ Category | category, type, status, vertical, zone |

## 🐛 Troubleshooting

**Error: Could not load data**
- Check sheet is publicly shared
- Verify Sheet ID is correct
- Check Tab Name matches exactly

**Columns not detected correctly**
- Rename columns to include keywords (e.g., "Invoice_Amount", "Submitted_By")

## 📝 License

MIT License - Free to use and modify
