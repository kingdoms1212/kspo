"""기존 서울 배치 실행 경로를 유지하는 호환 모듈이다."""
if __package__:
    from .regional_csv_batch import *
    from .regional_csv_batch import main
else:
    from regional_csv_batch import *
    from regional_csv_batch import main


if __name__ == "__main__":
    raise SystemExit(main())
