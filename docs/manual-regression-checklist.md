# DOBEDUB STUDIO 수동 회귀 확인 체크리스트

이 문서는 자동 smoke test로 확인하기 어려운 UI/사용자 흐름을 단계별로 확인하기 위한 기준이다.

## 로그인/세션

- [ ] 로그인 화면이 표시된다.
- [ ] ID, Password, Name이 비어 있으면 로그인되지 않는다.
- [ ] 로그인 후 Studio 화면으로 이동한다.
- [ ] 새로고침 시 작업 화면이 유지된다.
- [ ] 브라우저 종료 후 재접속 시 로그인 화면부터 시작한다.
- [ ] 로그아웃 버튼으로 로그인 화면에 복귀한다.

## 워크플로우/입력 이미지

- [ ] 기본 워크플로우는 `1-images.json`이다.
- [ ] 워크플로우 변경 시 입력 이미지 슬롯 수가 맞게 바뀐다.
- [ ] 이미지 업로드 후 고정 박스 안에 preview가 표시된다.
- [ ] 다중 이미지 업로드 시 슬롯 순서대로 배치된다.
- [ ] 워크플로우 변경/Refresh/재작업 시 이전 결과 preview가 초기화된다.

## Wan Node Config

- [ ] 세그먼트 설정 초기화가 현재 워크플로우 기본값으로 동작한다.
- [ ] 각 설정 slider/input 값이 화면과 Generation Info에 일관되게 표시된다.
- [ ] Final Output FPS, Bit Depth, Format, Codec 값이 workflow patch에 반영된다.
- [ ] 서브그래프 표시 이름이 중앙 정렬 및 줄바꿈된다.

## 작업 실행

- [ ] Generate Video 클릭 시 RUNPOD STATUS가 단순 상태값으로 표시된다.
- [ ] 생성 중 Cancel Generation 버튼이 표시된다.
- [ ] Cancel Generation 클릭 시 RunPod cancel endpoint가 호출되고 취소 작업은 history에 저장되지 않는다.
- [ ] 완료 후 최종 영상이 preview된다.
- [ ] View Segment는 세그먼트별 출력과 최종 출력을 구분해 표시한다.

## 작업 이력

- [ ] History/Saved Videos 리스트가 10개 단위로 페이지네이션된다.
- [ ] View 버튼으로 상세 Output Video preview가 표시된다.
- [ ] Download MP4가 실제 파일에 접근 가능하다.
- [ ] 재작업 버튼이 입력 이미지, 프롬프트, Wan config를 복원한다.
- [ ] Delete 버튼은 확인 메시지 후 asset과 history 데이터를 삭제한다.

## 문서/메타데이터

- [ ] User Manual 버튼으로 매뉴얼이 표시된다.
- [ ] Metadata View에서 workflow별 metadata를 조회할 수 있다.
- [ ] `/api/segment-defaults/{workflow}`가 ECS와 로컬에서 모두 정상 응답한다.
