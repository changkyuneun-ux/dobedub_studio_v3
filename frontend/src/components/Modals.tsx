import { useEffect, useRef, useState } from "react";

// 2026-08-11: 구버전 `ConfirmDeleteModal`(.modal-layer 스타일)을 제거했다 - 3a 작업
// 이력 삭제 확인창은 design_handoff_dobedub_v3/3 Review.dc.html 스펙(HISTORY:DELETE
// 라벨·작업/실행/결과물 요약 카드·"되돌릴 수 없습니다" 경고 스트립·하단 안내문)을
// 그대로 구현한 v3 전용 모달이 `reviewScreens.tsx`의 `Create3aScreen` 안에 이미
// 있었는데(213~243번째 줄), StudioShell.tsx가 같은 `deleteTarget` 상태를 보고
// 이 구버전 모달도 함께 띄우고 있어 3a에서 삭제 버튼을 누르면 두 개의 확인창이
// 겹쳐 뜨는 버그였다. deleteTarget을 세팅하는 곳이 Create3aScreen의 삭제 버튼
// 하나뿐임을 확인한 뒤(grep으로 다른 호출부 없음 확인) 이 구버전 모달과
// StudioShell.tsx의 렌더 지점을 제거했다 - Create3aScreen 안의 v3 모달만 남는다.

// 임시 403 화면. design_handoff_dobedub_v3의 정식 화면 `7g`(차단·만료·오류)가
// E-05에서 구현되면 이 컴포넌트는 제거하고 그쪽으로 대체한다. 그 전까지 최소한
// "권한이 없다"는 사실을 사용자에게 알리기 위한 자리다 - 이전에는 이 상황에서
// 아무 안내 없이 빈 화면(history/status/metadata/manual)이거나 조용한 리다이렉트
// (admin)만 있었다.
export function AccessDeniedModal({
  routeLabel,
  onClose
}: {
  routeLabel: string;
  onClose: () => void;
}) {
  return (
    <div className="modal-layer" role="dialog" aria-modal="true" aria-labelledby="accessDeniedTitle">
      <section className="confirm-modal">
        <div className="modal-header">
          <h2 id="accessDeniedTitle">권한이 없습니다</h2>
        </div>
        <p>"{routeLabel}" 화면을 사용할 권한이 없습니다. 필요한 경우 관리자에게 권한을 요청하십시오.</p>
        <div className="confirm-actions">
          <button className="secondary-button" type="button" onClick={onClose}>확인</button>
        </div>
      </section>
    </div>
  );
}

export function ManualModal({
  html,
  loading,
  error,
  onClose
}: {
  html: string;
  loading: boolean;
  error: string;
  onClose: () => void;
}) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const hitsRef = useRef<HTMLElement[]>([]);
  const hitIndexRef = useRef(-1);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchStatus, setSearchStatus] = useState("");

  function clearHighlights() {
    const document = iframeRef.current?.contentDocument;
    if (!document) return;
    document.querySelectorAll<HTMLElement>("mark.manual-hit").forEach((mark) => {
      const text = document.createTextNode(mark.textContent || "");
      mark.replaceWith(text);
      text.parentNode?.normalize();
    });
    hitsRef.current = [];
    hitIndexRef.current = -1;
  }

  function moveToHit(index: number) {
    const hits = hitsRef.current;
    if (!hits.length) {
      setSearchStatus("검색 결과가 없습니다.");
      return;
    }
    hits.forEach((hit) => hit.classList.remove("is-current"));
    hitIndexRef.current = (index + hits.length) % hits.length;
    const current = hits[hitIndexRef.current];
    current.classList.add("is-current");
    current.scrollIntoView({ behavior: "smooth", block: "center" });
    setSearchStatus(`${hitIndexRef.current + 1} / ${hits.length} 검색 결과`);
  }

  function searchManual() {
    const document = iframeRef.current?.contentDocument;
    clearHighlights();
    const query = searchQuery.trim();
    if (!document || !query) {
      setSearchStatus("검색어를 입력하세요.");
      return;
    }

    const needle = query.toLocaleLowerCase();
    const nodes: Text[] = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        if (!node.nodeValue?.trim() || node.parentElement?.closest("style, script, mark")) {
          return NodeFilter.FILTER_REJECT;
        }
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    while (walker.nextNode()) nodes.push(walker.currentNode as Text);

    nodes.forEach((node) => {
      const value = node.nodeValue || "";
      const lower = value.toLocaleLowerCase();
      let cursor = 0;
      let found = false;
      const fragment = document.createDocumentFragment();
      while (true) {
        const index = lower.indexOf(needle, cursor);
        if (index === -1) break;
        found = true;
        if (index > cursor) fragment.appendChild(document.createTextNode(value.slice(cursor, index)));
        const mark = document.createElement("mark");
        mark.className = "manual-hit";
        mark.textContent = value.slice(index, index + query.length);
        fragment.appendChild(mark);
        cursor = index + query.length;
      }
      if (!found) return;
      if (cursor < value.length) fragment.appendChild(document.createTextNode(value.slice(cursor)));
      node.replaceWith(fragment);
    });

    hitsRef.current = Array.from(document.querySelectorAll<HTMLElement>("mark.manual-hit"));
    if (!hitsRef.current.length) {
      setSearchStatus(`"${query}" 검색 결과가 없습니다.`);
      return;
    }
    moveToHit(0);
  }

  function handleManualLoad() {
    clearHighlights();
    setSearchStatus("");
    const document = iframeRef.current?.contentDocument;
    document?.addEventListener("click", (event) => {
      const target = event.target as HTMLElement | null;
      const link = target?.closest?.('a[href^="#"]');
      const anchorId = decodeURIComponent(link?.getAttribute("href")?.slice(1) || "");
      const section = anchorId ? document.getElementById(anchorId) : null;
      if (!section) return;
      event.preventDefault();
      section.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  useEffect(() => {
    hitsRef.current = [];
    hitIndexRef.current = -1;
    setSearchQuery("");
    setSearchStatus("");
  }, [html]);

  return (
    <div className="modal-layer" role="dialog" aria-modal="true" aria-labelledby="manualTitle" onMouseDown={(event) => {
      if (event.target === event.currentTarget) {
        onClose();
      }
    }}>
      <section className="manual-modal">
        <div className="modal-header">
          <h2 id="manualTitle">dobedub studio 사용자 매뉴얼</h2>
          <div className="modal-actions">
            <button className="icon-button" type="button" onClick={onClose}>x</button>
          </div>
        </div>
        <form className="manual-search-toolbar" onSubmit={(event) => {
          event.preventDefault();
          searchManual();
        }}>
          <label>
            매뉴얼 검색
            <input
              type="search"
              value={searchQuery}
              placeholder="검색어 입력 후 Enter"
              onChange={(event) => setSearchQuery(event.target.value)}
            />
          </label>
          <button className="primary-button" type="submit">검색</button>
          <button className="secondary-button" type="button" onClick={() => moveToHit(hitIndexRef.current + 1)}>다음</button>
          <p aria-live="polite">{searchStatus}</p>
        </form>
        <div className="manual-frame">
          {loading ? (
            <p>사용자 매뉴얼을 불러오는 중입니다.</p>
          ) : error ? (
            <div className="manual-error">
              <h3>사용자 매뉴얼을 불러오지 못했습니다.</h3>
              <p>{error}</p>
            </div>
          ) : (
            <iframe
              ref={iframeRef}
              title="dobedub studio 사용자 매뉴얼"
              sandbox="allow-same-origin"
              onLoad={handleManualLoad}
              srcDoc={html}
            />
          )}
        </div>
      </section>
    </div>
  );
}
