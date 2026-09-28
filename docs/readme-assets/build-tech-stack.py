from pathlib import Path
from io import BytesIO
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
from reportlab.graphics.shapes import Drawing, Group
from reportlab.graphics.svgpath import SvgPath
from reportlab.graphics import renderPDF
from reportlab.lib.colors import HexColor
import pypdfium2 as pdfium

base=Path(__file__).parent
im=Image.new('RGB',(1800,1160),'#F5F8FC'); d=ImageDraw.Draw(im)
navy='#19324F'; gray='#617792'
def text(x,y,value,size=25,color=navy,bold=False):
    f=ImageFont.truetype('C:/Windows/Fonts/'+('malgunbd.ttf' if bold else 'malgun.ttf'),size)
    d.text((x,y),value,font=f,fill=color)
def logo(name,x,y,color):
    root=ET.parse(base/'logos'/(name+'.svg')).getroot()
    drawing=Drawing(24,24); group=Group(transform=(1,0,0,-1,0,24))
    for p in root.findall('{http://www.w3.org/2000/svg}path'):
        group.add(SvgPath(p.attrib['d'],fillColor=HexColor(color),strokeColor=None))
    drawing.add(group)
    pdf=pdfium.PdfDocument(renderPDF.drawToString(drawing))
    pix=pdf[0].render(scale=3, fill_color=(0,0,0,0))
    icon=pix.to_pil().convert('RGBA').resize((42,42))
    im.paste(icon,(x,y),icon)
def card(x,y,title,color,rows,note):
    d.rounded_rectangle((x,y,x+520,y+382),radius=16,fill='white',outline=color,width=2)
    d.rounded_rectangle((x,y,x+520,y+62),radius=15,fill=color)
    text(x+24,y+12,title,29,'white',True)
    for i,(icon,label,desc) in enumerate(rows):
        ry=y+83+i*78
        if icon: logo(icon,x+24,ry+2,color)
        else:
            d.rounded_rectangle((x+24,ry+4,x+66,ry+44),radius=8,fill='#EEF2F8')
            text(x+34,ry+8,'•',23,color,True)
        text(x+84,ry,label,25,navy,True)
        text(x+84,ry+34,desc,21,gray)
    text(x+24,y+340,note,21,gray)
text(48,28,'스포링 · 분야별 기술 스택',44,navy,True)
text(48,94,'사용자 화면 · Django 서버 · CSV 데이터 · Gemini 분석 · Render 배포',26,gray)
card(48,170,'화면 · 사용자 인터페이스','#148BDD',[
 ('html5','HTML / CSS','화면 구조와 스타일'),('javascript','JavaScript / fetch','입력·요청·분석 상태 제어'),('htmx','HTMX 2.0.4','서버 HTML 부분 갱신')],'CSS 로고는 하단 공통 웹 기술에 표시')
card(640,170,'서버 · 업무 처리','#0FA580',[
 ('python','Python 3.13.15','집계·검증·업무 로직'),('django','Django 6.1.1','요청·템플릿·폼·서명'),(None,'python-dotenv 1.2.3','.env 로딩·환경변수 설정')],'View / Service / CSV Repository 책임 분리')
card(1232,170,'데이터 · 정제와 출력','#8562D9',[
 (None,'APScheduler 3.11.3','매일 00:00 한국 시간 배치'),(None,'BeautifulSoup 4.15.0','외부 정책 HTML 파싱'),(None,'openpyxl 3.1.5','조회 결과 Excel 내보내기')],'CSV 정제·검증 후 서비스 파일과 캐시 갱신')
card(48,590,'시각화 · 보관','#148BDD',[
 ('apacheecharts','ECharts 5.6.0 / GeoJSON','지역 지도와 데이터 시각화'),(None,'CSV / 메모리 / 파일 캐시','업무 조회 데이터·지역 AI 요약'),(None,'localStorage / print','최근 계획서 5건·브라우저 인쇄')],'스포츠 업무 데이터는 CSV 중심으로 관리')
card(640,590,'AI · 분석 연동','#DB8121',[
 ('googlegemini','Google Gemini','지역 현황 해석·프로그램 검토'),(None,'google-genai 2.24.0','서버 SDK·구조화 JSON 응답'),(None,'공통 요청·응답 검증','근거 키·점수·오류 처리')],'기본 모델: gemini-3.1-flash-lite')
card(1232,590,'배포 · 서비스 실행','#0FA580',[
 ('render','Render','웹 서비스 호스팅'),('gunicorn','Gunicorn 23 계열','1워커 / gthread 4스레드'),(None,'WhiteNoise 6.12.0','CSS·JS·이미지 정적 파일 제공')],'설정 기준: timeout 180초')
d.rounded_rectangle((48,1005,1752,1082),radius=14,fill=navy)
text(72,1026,'공통 웹 기술',25,'white',True)
logo('css',300,1022,'#FFFFFF')
text(366,1027,'CSS · 버전은 프로젝트 선언 기준이며 라이브러리별 역할은 아래 상세 표에서 확인합니다.',23,'white')
text(48,1103,'로고: Simple Icons (CC0). 로고 미확보 라이브러리와 표준 API는 이름으로 표시합니다.',20,gray)
im.save(base/'tech-stack.png')


