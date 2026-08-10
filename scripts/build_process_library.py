#!/usr/bin/env python3
"""Sync mission-control/process-library.html embedded data from data/process-register.json.
The page reads an inline <script id="data"> JSON block; run this after editing the register."""
import json, re, os
WS="/Users/exomac/.openclaw/workspace"
reg=open(os.path.join(WS,'mission-control/data/process-register.json')).read().rstrip()
html_path=os.path.join(WS,'mission-control/process-library.html')
html=open(html_path).read()
new=re.sub(r'(<script id="data" type="application/json">\n).*?(\n</script>)',
           lambda m: m.group(1)+reg+m.group(2), html, count=1, flags=re.S)
open(html_path,'w').write(new)
print('synced process-library.html data block (' + str(len(json.loads(reg)['register'])) + ' entries)')
