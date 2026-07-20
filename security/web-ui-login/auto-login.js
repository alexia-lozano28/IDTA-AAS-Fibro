(() => {
  "use strict";

  const authorizationEndpoint =
    "https://localhost:8443/auth/realms/basyx/protocol/openid-connect/auth";
  const clientId = "basyx-web-ui";
  const scope = "openid profile email";

  const isCallback = new URLSearchParams(window.location.search).has("code");

  function isClientToken(token) {
    try {
      const payload = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
      const claims = JSON.parse(atob(payload));
      return claims.realm_access?.roles?.includes("client");
    } catch {
      return false;
    }
  }

  function hideClientUploadControls() {
    const token = JSON.parse(localStorage.getItem("basyxInfrastructures") || "null")
      ?.infrastructures?.find((item) => item.token?.accessToken)?.token?.accessToken;
    if (!token || !isClientToken(token)) return;
    for (const element of document.querySelectorAll("button, [role=button]")) {
      const label = `${element.textContent} ${element.getAttribute("aria-label") || ""}`.toLowerCase();
      if (label.includes("upload")) element.style.display = "none";
    }
  }

  const observer = new MutationObserver(hideClientUploadControls);
  observer.observe(document.documentElement, { childList: true, subtree: true });
  window.setInterval(hideClientUploadControls, 250);

  if (isCallback) return;

  function base64Url(bytes) {
    let text = "";
    for (const byte of bytes) text += String.fromCharCode(byte);
    return btoa(text).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  function randomVerifier() {
    const bytes = new Uint8Array(32);
    crypto.getRandomValues(bytes);
    return base64Url(bytes);
  }

  async function startLogin(infrastructureId) {
    const verifier = randomVerifier();
    const digest = await crypto.subtle.digest(
      "SHA-256",
      new TextEncoder().encode(verifier)
    );
    const parameters = new URLSearchParams({
      response_type: "code",
      client_id: clientId,
      redirect_uri: `${window.location.origin}${window.location.pathname}`,
      scope,
      state: infrastructureId,
      code_challenge: base64Url(new Uint8Array(digest)),
      code_challenge_method: "S256",
    });
    localStorage.setItem(`oauth2_code_verifier_${infrastructureId}`, verifier);
    localStorage.setItem("oauth2_state", infrastructureId);
    window.location.replace(`${authorizationEndpoint}?${parameters}`);
  }

  const timer = window.setInterval(() => {
    let stored;
    try {
      stored = JSON.parse(localStorage.getItem("basyxInfrastructures") || "null");
    } catch {
      return;
    }
    const infrastructure = stored?.infrastructures?.find(
      (item) => item.id === stored.selectedInfrastructureId
    );
    if (!infrastructure?.auth?.oauth2 || infrastructure.token?.accessToken) {
      return;
    }
    window.clearInterval(timer);
    startLogin(infrastructure.id).catch(console.error);
  }, 50);

  window.setTimeout(() => window.clearInterval(timer), 5000);
})();
