# 행사 자료 갱신 절차

이 작업은 Codex가 Spotts 연결 도구로 자료를 수집한 뒤 이 저장소의 `events.json`만 갱신하고 Render 자동 배포를 확인한다. 연결 도구를 사용할 수 없거나 조회가 실패하면 이전 자료를 보존하고 실패를 알린다. 비공개 API 호출이나 사이트 무단 스크래핑을 대체 수단으로 사용하지 않는다.

1. 저장소가 `main`이며 작업 트리에 다른 변경사항이 없는지 확인하고 `git pull --ff-only`로 원격과 동기화한다. 다른 작업이 있거나 충돌하면 중단한다. Git 인증정보를 출력하거나 파일에 기록하지 않는다.
2. `work-refresh` 디렉터리를 만들고 기존 `part-*.json`과 `audit.json`만 제거한다. 실행마다 새 자료만 사용한다.
3. 연결된 `mcp__codex_apps__spotts_for_chatgpt_search_events`를 사용한다. 지역은 부산, 울산, 대구, 경북, 경남, 인천, 경기, 강원, 충북, 충남, 대전, 세종, 제주, 전남, 전북, 광주이고 각 지역에 festival, concert, exhibition, popup, expo를 각각 조건으로 넣어 검색한다. 서울은 전체 지역 조회가 실패했으므로 종로구, 용산구, 성동구, 광진구, 동대문구, 중랑구, 성북구, 강북구, 도봉구, 노원구, 은평구, 서대문구, 마포구, 양천구, 구로구, 금천구, 영등포구, 동작구, 관악구, 서초구, 강남구, 송파구, 강동구를 각각 검색한다. 각 호출의 limit은 30이다. 총 103회. 기본 날짜 조건은 조회일 이후이다.
4. `isError`가 참이거나 호출 예외인 항목을 `fail`에, 결과가 정확히 30건인 검색 조건을 `cap`에 기록한다. 결과를 이벤트 id 기준으로 중복 제거한다. 날짜가 모두 있고 상태가 upcoming 또는 ongoing이며 category가 destination, seasonal-spot이 아닌 것만 남긴다. 이벤트마다 다음 이름으로 기록한다: `name`, `start`(start_date), `end`(end_date), `status`, `venue`(venue_name), `latitude`, `longitude`, `url`(spotts_url), `category`. 원본 문자열·날짜를 추측해 채우지 않는다.
5. 결과 배열을 `work-refresh/part-0.json` 등 여러 UTF-8 JSON 파일에 나누어 쓰고, `work-refresh/audit.json`에 `{"jobs":103,"fail":[],"cap":[...]}` 형식으로 저장한다. 임시 자료는 `.gitignore` 대상이다. functions.exec에서는 ASCII 이스케이프한 JSON을 10건 단위로 `tools.exec_command`에 전달해 쓸 수 있다. 모든 결과를 확인하고 유실이나 실패를 기록한다.
6. `python tools/refresh_events.py`를 실행한다. 이 스크립트는 출처 URL·날짜·좌표를 검증하고 지도 경계에 매칭한 뒤 기존 데이터보다 지나치게 적거나 조회 실패가 있으면 갱신을 거부한다. 실패 시 강제로 덮어쓰지 않는다.
7. `events.json`만 `git add`, 커밋하고 main에 push한다. 그 외 파일은 수정·커밋하지 않는다. Render 서비스 `srv-dbq2obk9v7es73cc12a0`의 새 배포가 live인지 확인하고 https://dongne-hannune-map.onrender.com/events.json 의 checked_at과 건수를 확인한다. 자동 배포가 시작되지 않으면 Render 연결과 배포 설정을 확인하고 원인을 보고한다. 토큰·개인정보를 출력하지 않는다.

같은 날짜에 이미 성공적으로 갱신됐다면 중복 갱신을 피한다. 결과는 상한과 좌표 누락으로 완전하지 않으며, Spotts의 행사 기간이 매일 실제 운영을 뜻하지 않는다.
