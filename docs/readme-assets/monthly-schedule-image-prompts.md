# 배치 일정 이미지 수정

방식: 내장 image_gen 편집 도구. 생성 결과의 일정 표기를 확인한 뒤 프로젝트 이미지로 반영했습니다.

## architecture.png

Edit target: attached Korean service architecture diagram. Make only the following text correction, preserve all other content layout text and colors precisely. In right purple CSV batch panel replace 'APScheduler: 매주 일요일 00시' with 'APScheduler: 매월 1일 01:00 (KST)'. Keep readable Korean type and full diagram with no cropping. Save output image.

## exception-handling.png

Edit target: attached Korean exception-handling diagram. Make only this correction, preserve all other content layout text and colors precisely. In purple '원본 CSV → 정제 배치' panel replace '빌드·개발 기동·수동·일요일 00시 예약' with '빌드·개발 기동·수동·매월 1일 01:00 (KST)'. Fit text within card with readable Korean typography. Preserve entire diagram without cropping. Save output image.

기술 스택과 CSV 흐름도는 기존 생성 소스의 일정 문구를 수정해 다시 렌더링했습니다.
