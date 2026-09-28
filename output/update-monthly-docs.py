from pathlib import Path
for name in ['README.md','docs/RENDER-DEPLOYMENT.md','main/templates/overview/index.html']:
    p=Path(name)
    text=p.read_text(encoding='utf-8')
    p.write_text(text.replace('매일 00:00','매월 1일 01:00'),encoding='utf-8')
