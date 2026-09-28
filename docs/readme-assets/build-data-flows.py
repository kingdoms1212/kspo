"""README 데이터 흐름도 생성: PNG와 편집 가능한 SVG를 함께 저장한다."""
from pathlib import Path
from html import escape
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).parent
NAVY, BLUE, GREEN, PURPLE, GRAY = '#19324F', '#148BDD', '#0FA580', '#8562D9', '#617792'


class Diagram:
    def __init__(self, title, subtitle):
        self.im = Image.new('RGB', (1800, 1000), '#F5F8FC')
        self.d = ImageDraw.Draw(self.im)
        self.svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1000" viewBox="0 0 1800 1000">', '<rect width="1800" height="1000" fill="#F5F8FC"/>']
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


d = Diagram('Hi스포링 · 데이터 갱신 및 정제 흐름', '현재 구현  |  원본 확보는 수동, 서비스 반영은 월간 변경 확인을 거쳐 수행합니다.')
d.card(48,180,520,'01  원본 CSV 확보 · 반영', ['운영자가 새 원본을 확보해 data/에 반영', '프로그램 · 이용현황 · 시설 · 교통 4종', '최신 원본 자동 다운로드는 미구현'])
d.card(640,180,520,'02  월간 변경 확인', ['매월 1일 01:00 · Asia/Seoul', '원본 버전과 서비스 파일 상태 비교', '변경 없음 → 재정제 생략 · 기존 세대 유지'], PURPLE)
d.card(1232,180,520,'03  서울 추출 · 검증', ['전국 원본에서 서울 행만 추출', '지역 코드 · 빈 결과 등 검증', '임시 .part 파일로 생성'], PURPLE)
d.arrow([(568,290),(632,290)]); d.arrow([(1160,290),(1224,290)])
d.card(1232,490,520,'04  서비스 파일 발행', ['검증 후 서비스 CSV를 파일별 교체', 'data/Batch/에 서울 데이터 반영', '마지막에 manifest · 세대 정보 발행'], PURPLE)
d.card(640,490,520,'05  메모리 재적재', ['서비스 CSV 세대 변경 감지', '새 데이터 적재 · 파일 상태 검증', '재적재 실패 시 기존 정상 캐시 유지'], GREEN)
d.card(48,490,520,'06  조회 · AI 분석 근거', ['서울 데이터로 목록 조회 · 통계 집계', '지역 현황 · 프로그램 검토 근거 구성', '전국 데이터 상시 적재 부담 감소'], BLUE)
d.arrow([(1492,400),(1492,482)]); d.arrow([(1232,600),(1168,600)]); d.arrow([(640,600),(576,600)])
d.rect(48,770,1704,166,NAVY)
d.text(72,793,'누락·실패 대응',26,'white',True)
d.text(330,793,'원본 누락 → 실행 실패 · 다이얼로그에 누락 파일과 복구 안내',24,'white')
d.text(330,838,'추출·검증 실패 → 임시 파일 정리 · 오류 기록 · 교체 전 기존 서비스 파일 유지',24,'white')
d.text(72,887,'운영 한계: 서버 중지 중 예약 실행 및 여러 CSV 전체의 일괄 롤백은 보장하지 않습니다.',22,'#CDDCEF')
d.save('data-refresh-flow')

d = Diagram('Hi스포링 · 향후 데이터 구조 확장', '서울 CSV 기반 운영에서 전국 DB 기반 조회로 확장합니다. 아래의 향후 구성은 개발 계획입니다.')
d.text(48,166,'현재  ·  서울 중심 / CSV + 메모리 캐시',29,BLUE,True)
xs = [48,488,928,1368]
current = [
    ('원본 CSV', ['운영자가 확보 · 반영', '외부 자동 수집 없음']),
    ('서울 정제 · 검증', ['지역 추출 · 품질 검증', '서비스 CSV 발행']),
    ('메모리 캐시', ['서울 데이터 사전 적재', '세대 변경 시 재적재']),
    ('Django · AI', ['조회 · 집계 · 기획', '근거 기반 AI 분석']),
]
future = [
    ('API / 원본 파일', ['API 제공 시 수집기 추가', '기관 갱신 주기와 연계']),
    ('전국 정제 · 검증', ['지역별 데이터 표준화', '기존 정제 규칙 확장']),
    ('DB · 색인 · 조회', ['DB 스키마 · 저장기 구현', '지역·종목 조회 계층 전환']),
    ('Django · AI', ['전국 프로그램 기획', 'DB 집계 기반 분석']),
]
for x,(title,rows) in zip(xs,current): d.card(x,220,384,title,rows,BLUE,195)
for i in range(3): d.arrow([(xs[i]+384,318),(xs[i+1]-8,318)],BLUE)
d.text(48,477,'향후  ·  전국 확대 / 자동 수집 + DB',29,GREEN,True)
for x,(title,rows) in zip(xs,future): d.card(x,532,384,title,rows,GREEN,195)
for i in range(3): d.arrow([(xs[i]+384,630),(xs[i+1]-8,630)],GREEN)
d.rect(48,790,1704,146,NAVY)
d.text(72,813,'현재 확보한 확장 지점',26,'white',True)
d.text(490,813,'정제·반영 단계 분리 / data_refresh.py의 CSV·DB 저장기 선택 지점',24,'white')
d.text(72,869,'추가 구현 필요',26,'white',True)
d.text(490,869,'API 수집기 · DB 모델 및 저장기 · DB 조회 계층 · 독립 배치 운영',24,'white')
d.save('data-expansion-flow')
