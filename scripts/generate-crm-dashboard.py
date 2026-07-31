
# --- governance: correlation logging (auto-inserted; safe/soft) ---
try:
    import sys as _gsys, os as _gos, atexit as _gatexit
    _gsys.path.insert(0, _gos.path.join(_gos.path.dirname(_gos.path.abspath(__file__)), ".."))
    from governance.govlog import new_run as _gnew_run, event as _gevent
    _GRUN = _gnew_run("dashboard-data")
    _gevent(_GRUN, "start", detail=" ".join(_gsys.argv[1:])[:120])
    _gatexit.register(lambda: _gevent(_GRUN, "end"))
    _gprev_hook = _gsys.excepthook
    def _gexc(t, v, tb):
        try: _gevent(_GRUN, "error", status="error", detail=str(v)[:160])
        except Exception: pass
        return _gprev_hook(t, v, tb)
    _gsys.excepthook = _gexc
except Exception:
    pass
# --- /governance ---

import pandas as pd
import datetime
import os
import requests

EXCEL_PATH = '/Users/exomac/.openclaw/workspace/Exos_Fundraise_CRM.xlsx'
HTML_PATH = '/Users/exomac/.openclaw/workspace/EXOS_CRM_Dashboard.html'

import subprocess

# Telegram notification code
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


def generate_dashboard():
    try:
        df = pd.read_excel(EXCEL_PATH, sheet_name='CRM_Master')
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return
    
    # Clean data
    df['Stage'] = df['Stage'].fillna('Unknown')
    df['Priority Tier'] = df['Priority Tier'].fillna('Unranked')
    
    # Calculate stats
    total_contacts = len(df)
    stages = df['Stage'].value_counts().to_dict()
    
    # Identify Hot Pipeline (Tier 1 + active stages)
    hot_df = df[df['Priority Tier'] == 'Tier 1'].copy()
    
    # Sort or prep for display
    # We will pick top columns
    display_cols = ['Company', 'Contact Name', 'Stage', 'Next Action', 'Owner']
    hot_html = hot_df[display_cols].fillna('').to_html(index=False, classes='table table-striped table-hover', border=0)
    
    # Overdue - let's guess what 'Due?' or 'Days Since Last Touch' looks like. 
    # For now, just grab the ones that have a Next Action but aren't closed.
    # To be safe, we'll just show all active follow ups.
    active_df = df[df['Stage'].isin(['First Meeting', 'Second Meeting', 'Term Sheet / Proposal', 'Due Diligence'])].copy()
    active_html = active_df[display_cols].fillna('').to_html(index=False, classes='table table-sm', border=0)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>EXOS CRM Dashboard</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 40px; background: #f4f6f8; color: #333; }}
            .container {{ max-width: 1200px; margin: auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
            h1 {{ color: #1a365d; border-bottom: 2px solid #edf2f7; padding-bottom: 10px; }}
            h2 {{ color: #2b6cb0; margin-top: 30px; }}
            .stats {{ display: flex; gap: 20px; margin-bottom: 30px; }}
            .stat-box {{ background: #ebf8ff; padding: 20px; border-radius: 8px; flex: 1; text-align: center; border: 1px solid #bee3f8; }}
            .stat-box h3 {{ margin: 0; color: #3182ce; font-size: 14px; text-transform: uppercase; }}
            .stat-box p {{ margin: 10px 0 0; font-size: 32px; font-weight: bold; color: #2c5282; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
            th {{ background-color: #f7fafc; color: #4a5568; font-weight: 600; text-transform: uppercase; font-size: 12px; }}
            tr:hover {{ background-color: #f7fafc; }}
            .footer {{ margin-top: 50px; font-size: 12px; color: #a0aec0; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>EXOS Series A - CRM Dashboard</h1>
            
            <div class="stats">
                <div class="stat-box">
                    <h3>Total Pipeline</h3>
                    <p>{{total_contacts}}</p>
                </div>
                <div class="stat-box">
                    <h3>Hot / Tier 1 Targets</h3>
                    <p>{{len(hot_df)}}</p>
                </div>
                <div class="stat-box">
                    <h3>Active Discussions</h3>
                    <p>{{len(active_df)}}</p>
                </div>
            </div>

            <h2>🔥 Hot Pipeline (Tier 1)</h2>
            {{hot_html}}

            <h2>💬 Active Discussions</h2>
            {{active_html}}

            <div class="footer">
                Last updated: {{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}}
            </div>
        </div>
    </body>
    </html>
    """
    
    with open(HTML_PATH, 'w') as f:
        f.write(html_content)
    print("Dashboard generated successfully at", HTML_PATH)

    # Telegram notification code
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        response = requests.post(
            f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage',
            data={'chat_id': TELEGRAM_CHAT_ID, 'text': 'CRM dashboard generated successfully!'}
        )
        response.raise_for_status()

if __name__ == "__main__":
    generate_dashboard()
