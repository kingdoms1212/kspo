"""현재 정책 크롤링 구현을 PNG·SVG 아키텍처로 출력한다. README는 변경하지 않는다."""
from pathlib import Path
from html import escape
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).parent
NAVY, BLUE, GREEN, PURPLE, GRAY = '#19324F', '#148BDD', '#0FA580', '#8562D9', '#617792'


class Diagram:
    def __init__(self, title, subtitle):
        self.im = Image.new('RGB', (1800, 1180), '#F5F8FC')
        self.d = ImageDraw.Draw(self.im)
        self.svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1180" viewBox="0 0 1800 1180">', '<rect width="1800" height="1180" fill="#F5F8FC"/>']
        self.text(48, 32, title, 42, NAVY, True)
        self.text(48, 96, subtitle, 24, GRAY)

    def text(self, x, y, value, size=24, color=NAVY, bold=False):
        font = ImageFont.truetype('C:/Windows/Fonts/' + ('malgunbd.ttf' if bold else 'malgun.ttf'), size)
        self.d.text((x, y), value, font=font, fill=color, anchor='lt')
        self.svg.append(f'<text x="{x}" y="{y + size}" font-family="Malgun Gothic,sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{escape(value)}</text>')

    def rect(self, x, y, w, h, fill, stroke=None):
        self.d.rounded_rectangle((x, y, x+w, y+h), radius=16, fill=fill, outline=stroke, width=2)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{fill}" stroke="{stroke or fill}" stroke-width="2"/>')

    def card(self, x, y, w, title, rows, color=BLUE, h=220):
        self.rect(x, y, w, h, 'white', color)
        self.rect(x, y, w, 60, color)
        self.text(x+20, y+15, title, 27, 'white', True)
        for i, row in enumerate(rows):
            self.text(x+20, y+85+i*39, row, 23)

    def arrow(self, pts, color=GRAY):
        self.d.line(pts, fill=color, width=3)
        x,y = pts[-1]; px,py = pts[-2]
        if x == px:
            tri = [(x,y),(x-8,y-14 if y>py else y+14),(x+8,y-14 if y>py else y+14)]
        else:
            tri = [(x,y),(x-14 if x>px else x+14,y-8),(x-14 if x>px else x+14,y+8)]
        self.d.polygon(tri, fill=color)
        self.svg.append(f'<polyline points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="none" stroke="{color}" stroke-width="3"/>')
        self.svg.append(f'<polygon points="{" ".join(f"{x},{y}" for x,y in tri)}" fill="{color}"/>')

    def save(self, name):
        self.im.save(BASE / f'{name}.png')
        (BASE / f'{name}.svg').write_text(''.join(self.svg)+'</svg>', encoding='utf-8')


d = Diagram('Hi스포링 · 주요 정책 크롤링 아키텍처', '현재 코드 기준 · 2026.09.29  |  요청 시 목록 수집 · 메모리 캐시 재사용 · 다이얼로그 부분 갱신')
d.card(48,180,520,'01  브라우저 · 주요 정책 보기',[
    '클릭 즉시 다이얼로그 · 로딩 안내 표시',
    'HTMX GET /policies → Django 요청',
    '외부 사이트 조회는 서버에서 수행'], BLUE,240)
d.card(640,180,520,'02  Django · 정책 캐시 확인',[
    'View → Service → policies.models',
    '프로세스 메모리의 결과 · 경과시간 확인',
    '성공 900초 / 실패 60초 동안 재사용'],GREEN,240)
d.card(1232,180,520,'03  캐시 없음·만료 → HTML 수집',[
    '문화체육관광부 체육정책 목록',
    'urllib.request · User-Agent 지정',
    '타임아웃 6초 / 읽기 최대 2,000,000B'],PURPLE,240)
d.arrow([(568,280),(632,280)],BLUE)
d.arrow([(1160,280),(1224,280)],PURPLE)
d.text(1168,246,'수집',20,PURPLE)
d.card(1232,560,520,'04  BeautifulSoup · 링크 추출',[
    'table.board → td.tit_wrap → a',
    'title · href 추출 / 상대경로를 URL로 변환',
    '동일 호스트의 HTTP(S) 링크만 최대 10건'],PURPLE,240)
d.card(640,560,520,'05  결과 · 오류 캐시 저장',[
    '목록 · 오류 · 출처 · 조회시각 저장',
    '통신 실패 / 목록 구조·추출 실패 안내',
    '만료 후 다음 요청에서 다시 수집'],GREEN,240)
d.card(48,560,520,'06  HTML 응답 · 화면 갱신',[
    '정책 목록 또는 오류 안내로 로딩 교체',
    'HTMX: _list.html / 일반 접속: 전체 화면',
    '정책 클릭 → 원문을 새 창으로 열기'],BLUE,240)
d.arrow([(1492,420),(1492,552)],PURPLE)
d.arrow([(1232,676),(1168,676)],GREEN)
d.arrow([(640,676),(576,676)],BLUE)
# 캐시 재사용은 외부 수집·파싱·저장 경로를 우회한다.
d.arrow([(850,420),(850,474),(308,474),(308,552)],GREEN)
d.text(345,442,'유효 캐시 → 외부 요청 없이 응답',23,GREEN,True)
d.rect(48,866,1704,258,NAVY)
d.text(72,891,'수집 범위',26,'white',True)
d.text(332,891,'목록 순서대로 제목·원문 링크를 추출합니다. 정책 본문·첨부파일은 수집하지 않습니다.',24,'white')
d.text(72,949,'오류 대응',26,'white',True)
d.text(332,949,'통신·추출 실패는 안내 문구로 반환하고, 브라우저 요청 실패도 다이얼로그 안에 표시합니다.',24,'white')
d.text(72,1007,'운영 특성',26,'white',True)
d.text(332,1007,'CSV 월간 배치와 독립적입니다. 서버 크롤링은 동기 처리이며 예약·백그라운드 수집이 아닙니다.',23,'white')
d.text(332,1055,'60초는 실패 캐시 유지시간입니다. 타이머 자동 재시도나 기존 성공 목록 유지 기능은 없습니다.',23,'#CDDCEF')
d.save('policy-crawling-architecture')


