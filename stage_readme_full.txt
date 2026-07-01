# Lab Trip Docs

연구실 내부에서 출장 서류를 한곳에 모으고, 사람별/항목별로 자동 취합하는 중앙 PC용 웹앱입니다.

각 구성원은 중앙 PC 주소에 접속해 PDF, 이미지, 영수증 파일을 올립니다. 앱은 원본을 중앙 저장소에 보관하고 PDF/TXT 텍스트, 파일명, 업로더 이름을 함께 분석해 문서 유형과 출장자 후보를 자동으로 붙입니다. 관리자는 `검토필요` 큐만 확인해서 사람/유형을 수정하고 Excel 요약표와 사람별 PDF/원본 ZIP을 내려받습니다.

## 실사용 흐름

1. 관리자가 출장 건을 만듭니다.
2. 출장자 명단 CSV/XLSX를 병합합니다.
   - 헤더 예시: `이름`, `영문명`, `별칭`, `소속`
   - 같은 이름/영문명은 새 정보로 반영하고 새 사람만 추가하므로 기존 문서 매칭을 지우지 않습니다.
3. 각 구성원이 중앙 PC 주소로 접속해 파일을 올립니다.
4. 시스템이 문서 유형, 이름 후보, 날짜, 금액을 자동 추출합니다.
5. 관리자는 `검토필요`, `사람 미지정`, `문서 유형` 필터로 빠르게 확인합니다.
6. `Excel 요약`과 `사람별 PDF + 원본 ZIP`을 내려받습니다.

## 이번 버전에서 강화된 부분

- 여러 사람이 한 문서에 같이 나오는 경우 자동 확정하지 않고 `검토필요`로 분리합니다.
- 한글명, 영문명, 영문 역순, 별칭, 이니셜 기반 매칭을 강화했습니다.
- 파일명 기반 문서 유형 분류를 추가해 이미지 영수증도 후보 분류가 됩니다.
- 자동 분류/매칭 신뢰도와 근거를 UI에 표시합니다.
- 검토 큐, 사람별 현황, 운영 체크리스트 UI를 추가했습니다.
- 명단 재업로드 시 기존 매칭이 사라지지 않도록 병합 방식으로 바꿨습니다.
- Excel에 `Needs Review` 시트를 추가했습니다.
- Python 3.13에서 제거된 `cgi` 의존성을 없앴습니다.

## 빠른 실행

```bash
python -m pip install -r requirements.txt
export TRIPDOC_ADMIN_PASSWORD='strong-password'
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

## Docker 실행

```bash
docker compose up --build
```

## 명단 파일 형식

CSV 또는 XLSX 첫 행에 아래 헤더 중 일부를 넣으면 됩니다.

| 필드 | 허용 헤더 예시 |
|---|---|
| 이름 | `name`, `display_name`, `이름`, `성명`, `출장자` |
| 영문명 | `english_name`, `english`, `영문명`, `영어이름` |
| 별칭 | `aliases`, `alias`, `별칭`, `다른이름` |
| 소속 | `affiliation`, `department`, `소속`, `부서` |

별칭은 세미콜론, 콤마, 슬래시로 여러 개를 넣을 수 있습니다.

## 현재 한계

이 도구는 완전 자동 정산 시스템이 아니라 `자동 초안 + 관리자 검토` 시스템입니다. 스캔 PDF와 사진 영수증 OCR은 아직 기본 탑재하지 않았습니다. 이미지 파일은 파일명과 업로더 이름으로만 후보 분류되므로 검토필요로 남는 것이 정상입니다.

## 테스트

```bash
python -m compileall tripdoc tests
python -m unittest discover -s tests -v
```
