# Lab Trip Docs

연구실 내부에서 출장 서류를 한곳에 모으고, 사람별/항목별로 자동 취합하는 경량 웹앱입니다.

각 구성원은 중앙 PC 주소에 접속해 PDF, 이미지, 영수증 파일을 올립니다. 중앙 PC는 원본을 보관하고 문서 텍스트를 추출한 뒤 이름, 문서 종류, 날짜, 금액 힌트를 찾아 관리자 검토 화면에 보여줍니다. 관리자는 틀린 매칭만 수정하고 Excel 요약표와 사람별 PDF 패키지를 내려받습니다.

## 왜 내부 웹앱인가

- 각자 PC에는 설치할 것이 거의 없습니다.
- 파일은 연구실 중앙 PC에 모입니다.
- 외부 공개 웹서비스보다 개인정보 노출 위험이 낮습니다.
- 브라우저에서 업로드, 검토, 출력까지 처리할 수 있습니다.

## 빠른 실행

```bash
cd lab-trip-docs
python -m pip install -r requirements.txt
python -m tripdoc
```

브라우저에서 접속합니다.

```text
http://localhost:8501
```

연구실 구성원은 중앙 PC의 내부 IP로 접속합니다.

```text
http://중앙PC_IP:8501
```

기본 로그인은 `.env.example` 기준입니다.

```text
ID: admin
PW: change-me
```

실사용 전에는 반드시 비밀번호를 바꾸세요.

## 환경 변수

```bash
export TRIPDOC_HOST=0.0.0.0
export TRIPDOC_PORT=8501
export TRIPDOC_DATA_DIR=data
export TRIPDOC_ADMIN_USER=admin
export TRIPDOC_ADMIN_PASSWORD='strong-password'
python -m tripdoc
```

## 주요 기능

- 출장 건 생성
- 출장자 명단 CSV/XLSX 업로드
- PDF/JPG/PNG/TXT 업로드
- 원본 파일 중앙 저장
- PDF/TXT 텍스트 추출
- 항공권, 탑승권, 숙박, 학회 등록, 명찰, 식비, 교통비 자동 분류
- 한글명, 영문명, 별칭 기반 사람 자동 매칭
- 관리자 검토 및 수동 수정
- 전체 Excel 요약 생성
- 사람별 PDF 요약과 원본 파일을 포함한 ZIP 생성

## 명단 파일 형식

CSV 또는 XLSX 첫 행에 아래 헤더 중 일부를 넣으면 됩니다.

| 필드 | 허용 헤더 예시 |
|---|---|
| 이름 | `name`, `display_name`, `이름`, `성명` |
| 영문명 | `english_name`, `english`, `영문명`, `영어이름` |
| 별칭 | `aliases`, `alias`, `별칭`, `다른이름` |
| 소속 | `affiliation`, `department`, `소속`, `부서` |

별칭은 세미콜론 또는 콤마로 여러 개를 넣을 수 있습니다.

## 한계

이 MVP는 자동 초안을 만드는 도구입니다. 스캔 PDF와 사진 영수증 OCR, 기관별 정산 양식 자동 기입, 로그인 권한 세분화는 다음 단계로 확장하는 것이 좋습니다.

## 테스트

```bash
python -m unittest discover -s tests
```

## Docker 실행

```bash
docker compose up --build
```
