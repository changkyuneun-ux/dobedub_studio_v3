# dobedub studio 사용자 매뉴얼

작성일: 2026년 7월  
대상 앱: DOBEDUB STUDIO - Image-to-Video Workflow Runner  
운영 환경: AWS ECS + RunPod Serverless
URL:comfyui.dobedub.org

## 수정 이력

| 일자 | 변경 전 | 변경 후 | 비고 |
| --- | --- | --- | --- |
| 2026-07-29 | 앱 화면에서 사용자 매뉴얼을 바로 확인할 수 없음 | 상단 `Check Status` 옆에 `User Manual` 버튼을 추가하고 별도 모달 HTML 페이지로 매뉴얼 제공 | Markdown 수정 시 모달 매뉴얼에 즉시 반영 |
| 2026-07-29 | 사용자 정보 옆 로그아웃 기능 없음 | 사용자 이름 옆 `로그아웃` 버튼 추가, 클릭 시 세션 삭제 후 로그인 화면으로 복귀 | 브라우저 세션 기준 |
| 2026-07-29 | 작업 이력의 항목 구조가 기존 UI 기준으로 설명됨 | No., Worker, Positive/Negative Prompt 복사, Delete, Output Video 탭 기준으로 설명 수정 | 신규 UI 기준 |
| 2026-07-31 | 1-key~5-key 워크플로우 기준 | 1-images~6-images v2 워크플로우 기준으로 변경 | workflow 내장 SaveVideo 노드 사용 |
| 2026-07-31 | 작업 이력에서 과거 작업을 바로 편집 화면으로 불러올 수 없음 | 작업 리스트에 `재작업` 버튼 추가, 입력 이미지와 프롬프트 및 설정값을 생성 화면에 복원 | 일부 수정 후 빠른 재생성 용도 |
| 2026-07-31 | 컨트롤 패널에서 구간을 `Segment 1` 형식으로 표시 | workflow 서브그래프 노드 이름과 순서를 포함한 `노드이름_1` 형식으로 표시 | 예: `WAN 비디오 생성 (시작-끝 프레임)_1` |
| 2026-07-31 | 최종 출력 `CreateVideo`와 `SaveVideo` 설정을 UI에서 조정할 수 없음 | `Final Output FPS`, `Final Bit Depth`, `Final Format`, `Final Codec` 설정 추가 | `filename_prefix`는 asset/이력 관리를 위해 앱 내부 자동 관리 |
| 2026-07-31 | `Final Format`, `Final Codec`을 직접 입력해야 함 | 리스트 박스로 선택하도록 변경 | 기본 후보: format `auto/mp4`, codec `auto/h264` |
| 2026-07-31 | `Save Configuration`, `View Configs`로 별도 설정 저장/조회 | 두 버튼을 제거하고 `Metadata View` 버튼으로 workflow metadata 조회 제공 | 작업 재실행은 History의 `재작업` 사용 |
| 2026-07-31 | 작업 이력에 대표 Wan Node Config만 저장 | 서브그래프 및 노드 target별 Wan Node Config JSON 전체 저장 | 재작업 시 해당 값도 복원 |

## 목차

1. 시작하기 전에
2. 로그인과 접속 상태 확인
3. 메인 화면 구성
4. 워크플로우 선택
5. 이미지 업로드
6. 프롬프트 입력과 불러오기
7. Wan Node Config 설정
8. 비디오 생성, 진행 상태, 취소
9. 결과 확인, 세그먼트 보기, 다운로드
10. 작업 이력 조회와 관리
11. Metadata View
12. Refresh와 화면 초기화
13. 자주 발생하는 상황과 해결 방법
14. 운영/관리자 참고 사항

## 1. 시작하기 전에

dobedub studio는 이미지를 업로드하고 프롬프트를 입력하면 RunPod Serverless의 ComfyUI 워크플로우를 실행해 영상을 생성하는 웹 앱입니다. 사용자는 ComfyUI 노드를 직접 조작하지 않고, 웹 UI에서 워크플로우 선택, 이미지 업로드, 프롬프트 입력, 세그먼트별 설정, 결과 확인, 작업 이력 관리까지 수행할 수 있습니다.

화면 왼쪽에는 세그먼트 진행률, 가운데에는 입력과 설정, 오른쪽에는 미리보기와 결과가 배치되어 있습니다.

이 앱은 WAN Image-to-Video 계열 워크플로우를 실행합니다. 워크플로우에 따라 필요한 입력 이미지 수와 세그먼트 수가 자동으로 바뀝니다.

## 2. 로그인과 접속 상태 확인

앱에 접속하면 로그인 화면이 나타납니다. 로그인 화면에서는 세 가지 값을 입력합니다.

- ID (Email Address): dobedub
- Password: 관리자로부터 발급받은 접속 비밀번호
- Name: 작업 이력에 기록될 작업자 이름

세 값을 모두 입력한 뒤 `접속하기` 버튼을 클릭하면 작업 화면으로 이동합니다.

화면 오른쪽 위의 `System: ONLINE` 표시는 웹 앱 서버가 정상 응답 중임을 의미합니다. 로그인 후 작업 화면에서는 `API Server: ONLINE`, `DRY-RUN`, `CHECK`, `실패` 등의 상태가 표시될 수 있습니다.

로그인 상태는 브라우저 세션 동안 유지됩니다. 작업 중 새로고침을 해도 바로 작업 화면으로 돌아오지만, 브라우저를 완전히 종료한 뒤 다시 접속하면 로그인 화면부터 시작합니다.

## 3. 메인 화면 구성

작업 화면은 크게 네 영역으로 구성됩니다.

1. 상단 바
   - 앱 제목 `DOBEDUB STUDIO`
   - `History/Saved Videos`
   - `Check Status`
   - Subgraph Manager 전체 진행률
   - API Server 상태
   - 현재 사용자 이름

2. 왼쪽 Control Panel
   - 세그먼트별 카드가 표시됩니다.
   - 각 카드에는 해당 세그먼트의 진행률이 0-100%로 표시됩니다.
   - 세그먼트를 클릭하면 가운데 입력 영역과 오른쪽 Preview 영역이 해당 세그먼트 기준으로 전환됩니다.

3. 가운데 Workflow List / 입력 영역
   - 워크플로우 선택
   - 입력 이미지 업로드
   - Positive Prompt / Negative Prompt 입력
   - Load Past Prompts
   - Wan Node Config
   - Generate Video / Cancel Generation

4. 오른쪽 Preview & Output
   - Metadata View
   - 생성 진행률
   - Log Stream
   - View Subgraph
   - 영상 미리보기
   - Generation Info
   - Download MP4
   - Refresh

## 4. 워크플로우 선택

`Workflow List` 아래의 드롭다운에서 실행할 워크플로우를 선택합니다.

기본 워크플로우는 `Wan 1-images (1 keyframes)`입니다. 워크플로우를 바꾸면 필요한 이미지 업로드 박스 수와 세그먼트 수가 자동으로 바뀌고, 기존 결과 화면은 초기화됩니다.

지원 워크플로우 구조는 다음과 같습니다.

| 워크플로우 | 입력 이미지 수 | 세그먼트 수 | 용도 |
| --- | ---: | ---: | --- |
| 1-images | 1 | 1 | 이미지 1장으로 짧은 영상을 생성 |
| 2-images | 2 | 1 | 시작 이미지와 끝 이미지를 연결 |
| 3-images | 3 | 2 | 이미지 3장을 2개 구간으로 연결 |
| 4-images | 4 | 3 | 이미지 4장을 3개 구간으로 연결 |
| 5-images | 5 | 4 | 이미지 5장을 4개 구간으로 연결 |
| 6-images | 6 | 5 | 이미지 6장을 5개 구간으로 연결 |

워크플로우 변경 시 입력 이미지와 결과 미리보기는 새 워크플로우 기준으로 재구성됩니다.

## 5. 이미지 업로드

`Image Upload` 영역에는 워크플로우가 요구하는 입력 이미지 수만큼 고정 크기의 이미지 박스가 표시됩니다.

이미지 박스를 클릭해 파일을 선택하거나, 여러 이미지를 한 번에 선택할 수 있습니다. 여러 이미지를 선택하면 선택한 슬롯부터 순서대로 자동 배치됩니다.

예를 들어 5-images 워크플로우에서 Image 1 박스를 클릭한 뒤 이미지 5장을 선택하면 Image 1부터 Image 5까지 순차적으로 업로드됩니다.

이미지 크기가 서로 달라도 UI에서는 고정된 이미지 박스 안에 맞춰 미리보기가 표시됩니다. 실제 생성 요청에는 업로드된 원본 이미지 asset이 사용됩니다.

이미지를 제거하려면 이미지 박스 오른쪽 위의 `×` 버튼을 클릭합니다.

주의 사항:

- 워크플로우가 요구하는 모든 입력 이미지가 채워져야 생성할 수 있습니다.
- 입력 이미지가 부족한 상태에서 `GENERATE VIDEO`를 누르면 어떤 이미지 슬롯이 비어 있는지 안내됩니다.
- 작업 결과 영상이 생성되면 입력 이미지 박스 옆에 Result 박스가 표시될 수 있습니다.
- Result 박스의 재생 버튼은 Picture-in-Picture 방식으로 영상을 재생합니다.

## 6. 프롬프트 입력과 불러오기

각 세그먼트에는 Positive Prompt와 Negative Prompt가 있습니다.

Positive Prompt는 생성하고 싶은 움직임, 장면, 카메라 움직임, 분위기를 입력하는 영역입니다.

Negative Prompt는 피하고 싶은 표현, 왜곡, 품질 저하 요소를 입력하는 영역입니다.

워크플로우를 선택하면 JSON 워크플로우 또는 param config에 저장된 기본 프롬프트가 표시됩니다. 사용자가 직접 수정하면 수정한 값이 현재 세그먼트에 적용됩니다.

`Load Past Prompts` 버튼을 누르면 과거 작업 이력과 저장된 config에서 Positive/Negative 프롬프트를 불러올 수 있는 모달이 열립니다.

프롬프트 모달 사용 방법:

1. `Load Past Prompts` 클릭
2. `Positive` 또는 `Negative` 탭 선택
3. 목록에서 원하는 프롬프트 클릭
4. 현재 선택된 세그먼트의 프롬프트 입력란에 자동 입력

다중 세그먼트 워크플로우에서는 세그먼트를 선택한 뒤 프롬프트를 입력해야 해당 세그먼트에 저장됩니다.

## 7. Wan Node Config 설정

`Wan Node Config (ComfyUI)` 영역에서는 생성 품질, 움직임, 길이와 관련된 주요 매개변수를 조정합니다.

| 항목 | 의미 | 사용 팁 |
| --- | --- | --- |
| Sampling Steps | 샘플링 반복 수 | 높을수록 시간이 길어질 수 있습니다. |
| CFG Scale | 프롬프트 반영 강도 | 너무 높으면 부자연스러울 수 있습니다. |
| Motion Shift | 움직임 변화량 | 높을수록 움직임이 강해질 수 있습니다. |
| FPS | 초당 프레임 수 | 보통 16을 기본값으로 사용합니다. |
| Final Output FPS | 최종 출력 비디오의 초당 프레임 수 | 3-images 이상에서 최종 결합 영상에 적용됩니다. |
| Frames | 생성 프레임 수 | 2-images 이상 일부 워크플로우에서 사용됩니다. |
| Duration | 영상 길이 | 1-images 등 duration 기반 워크플로우에서 사용됩니다. |
| Seed | 결과 재현값 | 같은 seed와 설정이면 유사한 결과를 기대할 수 있습니다. |
| Final Bit Depth | 최종 출력 비디오의 bit depth | 기본값 8을 권장합니다. |
| Final Format | 최종 출력 SaveVideo format | 리스트에서 `auto` 또는 `mp4`를 선택합니다. 기본값은 `auto`입니다. |
| Final Codec | 최종 출력 SaveVideo codec | 리스트에서 `auto` 또는 `h264`를 선택합니다. 기본값은 `auto`입니다. |

`세그먼트 설정 초기화` 버튼은 현재 워크플로우의 확인된 기본값으로 세그먼트 설정을 되돌립니다.

현재 기본값은 다음 기준으로 관리됩니다.

| 워크플로우 | 세그먼트 수 | 기본값 |
| --- | ---: | --- |
| 1-images | 1 | steps 4, cfg 1, motion 5, duration 5s, fps 16 |
| 2-images | 1 | steps 4, cfg 1, motion 5, frames 25, fps 16 |
| 3-images | 2 | 각 steps 4, cfg 1, motion 5, frames 25, fps 16 |
| 4-images | 3 | 각 steps 4, cfg 1, motion 5, frames 25, fps 16 |
| 5-images | 4 | 각 steps 4, cfg 1, motion 5, frames 25, fps 16 |
| 6-images | 5 | 각 steps 4, cfg 1, motion 5, frames 25, fps 16 |

## 8. 비디오 생성, 진행 상태, 취소

입력 이미지, 프롬프트, Wan Node Config 설정을 완료한 뒤 `GENERATE VIDEO` 버튼을 클릭합니다.

생성이 시작되면 다음 상태가 표시됩니다.

- 상단 Subgraph Manager 진행률
- 왼쪽 세그먼트 카드별 진행률
- Preview & Output의 원형 진행률
- Log Stream의 RunPod 상태
- Generation Time
- API Server 상태

RunPod 상태는 단순한 형식으로 표시됩니다.

예:

```text
RUNPOD STATUS : IN_PROGRESS
```

생성 중에는 `Cancel Generation` 버튼이 표시됩니다. 이 버튼을 누르면 RunPod Serverless cancel endpoint로 취소 요청이 전송됩니다.

취소된 작업은 작업 이력에 저장되지 않습니다. 이미 완료된 작업은 취소할 수 없습니다.

## 9. 결과 확인, 세그먼트 보기, 다운로드

생성이 완료되면 Preview & Output 영역에 결과 영상이 표시됩니다.

`View Subgraph` 드롭다운을 사용하면 서브그래프별 결과를 확인할 수 있습니다. 서브그래프별 영상이 저장된 워크플로우에서는 각 서브그래프 영상이 구분되어 표시됩니다. 서브그래프 영상이 별도로 저장되지 않은 경우에는 최종 결과 영상만 표시될 수 있습니다.

`Generation Info`에는 다음 정보가 표시됩니다.

- Seed
- FPS
- Prompt 요약
- Workflow
- View Subgraph
- Frames 또는 Duration
- Steps / CFG
- Motion
- Segment Output
- Final Output

결과 파일을 내려받으려면 `Download MP4` 버튼을 클릭합니다.

결과가 아직 생성되지 않았거나 작업이 실패한 경우 다운로드할 파일이 없다는 안내가 표시됩니다.

## 10. 작업 이력 조회와 관리

상단의 `History/Saved Videos` 버튼을 누르면 `Task History & Result List` 모달이 열립니다.

작업 이력 표는 10개 단위로 페이지네이션됩니다. 표 아래의 `Prev`, 페이지 번호, `Next` 버튼으로 페이지를 이동합니다.

작업 이력 표의 컬럼은 다음과 같습니다.

| 컬럼 | 설명 |
| --- | --- |
| No. | 작업 순번 |
| Timestamp | 작업 생성 시각 |
| Worker | 로그인 시 입력한 작업자 이름 |
| Positive Prompt | 작업에 사용된 Positive Prompt |
| Negative Prompt | 작업에 사용된 Negative Prompt |
| Status | Completed, Failed 등 작업 상태 |
| View | 해당 작업의 결과 상세 보기 |
| Download | 최종 MP4 다운로드 |
| Rework | 해당 작업의 이미지, 프롬프트, 설정값을 생성 화면으로 불러오기 |
| Delete | 작업 이력과 연결 asset 삭제 |

Positive Prompt와 Negative Prompt는 여러 개일 경우 `1.`, `2.` 형식으로 구분됩니다. `Copy` 버튼을 누르면 해당 프롬프트 목록을 클립보드에 복사합니다.

오른쪽 상세 패널에는 다음 탭이 있습니다.

- Task Overview
- Input Images
- Node Config
- Output Video

Input Images 탭에서는 업로드 파일명이 asset id와 함께 표시됩니다.

Output Video 탭에서는 최종 영상과 세그먼트 영상이 분리되어 표시됩니다. 저장된 output asset이 없는 과거 작업은 파일명만 보이거나 미리보기가 제한될 수 있습니다.

작업 재작업:

`재작업` 버튼을 누르면 해당 작업의 workflow, 입력 이미지 asset, Positive/Negative Prompt, 세그먼트별 Wan Node Config 값이 생성 화면에 복원됩니다. 복원 후 사용자는 프롬프트나 설정값을 일부 수정한 뒤 `GENERATE VIDEO`를 눌러 새 작업으로 다시 생성할 수 있습니다.

작업 삭제:

`Delete` 버튼을 누르면 다음 확인 메시지가 표시됩니다.

```text
삭제한 모든 자료(이미지, 영상 등)가 모두 삭제 됩니다. 삭제후 복구되지 않습니다. 삭제하시겠습니까?
```

`삭제`를 누르면 해당 작업 이력, 입력 이미지 asset, 출력 영상 asset, 연결된 파일이 삭제됩니다. `취소`를 누르면 아무 것도 삭제되지 않습니다.

## 11. Metadata View

Preview & Output 상단의 `Metadata View` 버튼을 누르면 현재 워크플로우의 metadata를 조회할 수 있습니다.

Metadata View에서는 다음 정보를 확인합니다.

- Summary: workflow id, node 수, 서브그래프 수, metadata 생성 시각, object_info snapshot 여부
- Subgraphs: 서브그래프별 노드 ID, class type, positive/negative prompt 노드, 입력 이미지 노드
- Parameters: Wan Node Config 항목별 기본값, 현재 연결 대상 노드와 field
- Models: workflow JSON에서 확인된 모델 파일 목록
- Nodes: 전체 노드의 입력값과 링크 정보

`Rebuild Metadata`는 workflow JSON 또는 paramconfig 변경 후 metadata를 강제로 다시 생성할 때 사용합니다. 일반적으로는 workflow 파일 변경 시 앱이 자동으로 metadata를 갱신합니다.

이전 `Save Configuration`, `View Configs`, `Save Current Config to DB` 기능은 제거되었습니다. 기존 작업을 다시 불러오려면 History/Saved Videos의 `재작업` 버튼을 사용합니다.

`Generate Report`는 선택된 작업의 리포트 파일을 생성해 다운로드합니다.

## 12. Refresh와 화면 초기화

Preview & Output 하단의 `Refresh` 버튼은 결과 화면을 초기화합니다.

초기화되는 항목:

- 생성 진행률
- Log Stream
- 결과 영상 프리뷰
- Result 박스
- 세그먼트 진행률

유지되는 항목:

- 현재 워크플로우 선택
- 업로드된 입력 이미지
- 프롬프트
- Wan Node Config 설정

새로 작업을 준비하면서 입력값은 유지하고 이전 결과 표시만 지우고 싶을 때 사용합니다.

## 13. 자주 발생하는 상황과 해결 방법

| 상황 | 예상 원인 | 해결 방법 |
| --- | --- | --- |
| API Server가 CHECK로 표시됨 | 서버 상태 확인 중이거나 일시 응답 지연 | `Check Status`를 눌러 상태를 다시 확인합니다. |
| API Server가 실패로 표시됨 | RunPod 또는 앱 서버 연결 실패 | RunPod endpoint, API key, ECS 로그를 확인합니다. |
| GENERATE VIDEO가 실행되지 않음 | 입력 이미지 누락 | Image Upload 영역에서 필요한 모든 이미지를 채웁니다. |
| 첫 생성이 오래 걸림 | RunPod Serverless cold start | 몇 분 정도 대기합니다. 이후 작업은 빨라질 수 있습니다. |
| RUNPOD STATUS가 IN_QUEUE로 유지됨 | GPU worker 대기열 | 잠시 기다리거나 나중에 다시 시도합니다. |
| 작업이 CANCELLED로 종료됨 | 사용자가 취소했거나 RunPod 취소 요청 처리됨 | 필요한 경우 새로 생성합니다. 취소 작업은 이력에 저장되지 않습니다. |
| 결과 영상 미리보기가 안 보임 | output asset이 없거나 파일 접근 불가 | 작업 이력의 Output Video 탭과 Download 버튼을 확인합니다. |
| 다운로드 시 파일 없음 오류 | 오래된 이력의 파일이 삭제되었거나 경로가 바뀜 | 새 작업으로 다시 생성합니다. |
| 새로고침 후 로그인 화면으로 감 | 브라우저 세션 종료 또는 새 세션 | 다시 로그인합니다. |
| View Subgraph가 모두 같은 영상으로 보임 | 해당 워크플로우가 서브그래프별 파일을 저장하지 않은 과거 작업 | 새 버전에서 생성한 작업은 서브그래프 output 저장 여부를 확인합니다. |

## 14. 운영/관리자 참고 사항

이 앱은 AWS ECS에서 웹 UI/API 서버로 실행되고, 영상 생성은 RunPod Serverless endpoint를 호출합니다.

운영 구성:

- AWS ECS service: DOBEDUB STUDIO 웹 앱 실행
- ECR: 앱 Docker image 저장
- EFS: 작업 이력, 업로드 이미지, 결과 영상 저장 영역
- AWS Secrets Manager: RunPod API Key 등 secret 저장
- RunPod Serverless: ComfyUI workflow 실행

운영 환경에서는 `RUNPOD_DRY_RUN=0`으로 설정되어 실제 RunPod endpoint에 작업이 제출됩니다.

운영 시 주의 사항:

- RunPod API Key는 환경변수 plaintext가 아니라 Secrets Manager 또는 SSM Parameter Store를 사용합니다.
- `/data` 계열 저장소를 컨테이너 내부 ephemeral storage에만 두면 task 재시작 시 이력이 사라질 수 있습니다.
- 장기 운영에서는 작업 이력은 DB, 결과 파일은 S3로 이전하는 것을 권장합니다.
- ECS 배포는 canary 방식이면 완료까지 시간이 걸릴 수 있습니다.
- 배포 중 새 task와 기존 task가 잠시 공존하는 것은 정상입니다.
