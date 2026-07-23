(() => {
  "use strict";

  const authorizationEndpoint =
    "https://localhost:8443/auth/realms/basyx/protocol/openid-connect/auth";
  const clientId = "basyx-web-ui";
  const scope = "openid profile email";

  const isCallback = new URLSearchParams(window.location.search).has("code");

  function tokenClaims(token) {
    try {
      const payload = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
      const paddedPayload = payload.padEnd(Math.ceil(payload.length / 4) * 4, "=");
      return JSON.parse(atob(paddedPayload));
    } catch {
      return {};
    }
  }

  function hasRole(token, role) {
    return tokenClaims(token).realm_access?.roles?.includes(role) === true;
  }

  function selectedInfrastructure() {
    try {
      const stored = JSON.parse(localStorage.getItem("basyxInfrastructures") || "null");
      return stored?.infrastructures?.find(
        (item) => item.id === stored.selectedInfrastructureId
      );
    } catch {
      return undefined;
    }
  }

  function accessToken() {
    return selectedInfrastructure()?.token?.accessToken;
  }

  function hideClientUploadControls() {
    const token = accessToken();
    if (!token || !hasRole(token, "client")) return;
    for (const element of document.querySelectorAll("button, [role=button]")) {
      const label = `${element.textContent} ${element.getAttribute("aria-label") || ""}`.toLowerCase();
      if (label.includes("upload")) element.style.display = "none";
    }
  }

  const observer = new MutationObserver(hideClientUploadControls);
  observer.observe(document.documentElement, { childList: true, subtree: true });
  window.setInterval(hideClientUploadControls, 250);

  function gatewayOrigin() {
    const issuer = selectedInfrastructure()?.auth?.oauth2?.host;
    try {
      return issuer ? new URL(issuer).origin : "https://localhost:8443";
    } catch {
      return "https://localhost:8443";
    }
  }

  function addImportMenuItem() {
    const token = accessToken();
    const existing = document.querySelector('[data-fibro-xlsx-import="menu-item"]');
    if (!token || !hasRole(token, "admin")) {
      existing?.remove();
      return;
    }
    if (existing) return;

    const titles = [...document.querySelectorAll(".v-list-item-title")];
    const targetTitle = titles.find((element) => {
      const label = element.textContent?.trim().toLowerCase() || "";
      return /aas\s*sm\s*visuali[sz]ations/.test(label);
    });
    const targetItem = targetTitle?.closest(".v-list-item");
    if (!targetItem?.parentElement) return;

    const menuItem = targetItem.cloneNode(true);
    menuItem.dataset.fibroXlsxImport = "menu-item";
    menuItem.removeAttribute("href");
    menuItem.removeAttribute("to");
    menuItem.querySelector(".v-list-item-title").textContent = "Upload XLSX as AAS";
    const icon = menuItem.querySelector(".mdi");
    if (icon) {
      for (const className of [...icon.classList]) {
        if (className.startsWith("mdi-") && className !== "mdi") {
          icon.classList.remove(className);
        }
      }
      icon.classList.add("mdi-file-excel-outline");
    }
    menuItem.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      openImportDialog();
    });
    targetItem.after(menuItem);
  }

  function dialogElement(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text) element.textContent = text;
    return element;
  }

  function openImportDialog() {
    if (document.getElementById("fibro-xlsx-import-dialog")) return;
    const token = accessToken();
    if (!token || !hasRole(token, "admin")) return;

    const overlay = dialogElement("div", "fibro-import-overlay");
    overlay.id = "fibro-xlsx-import-dialog";
    const dialog = dialogElement("section", "fibro-import-dialog");
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    dialog.setAttribute("aria-labelledby", "fibro-import-title");

    const header = dialogElement("div", "fibro-import-header");
    const heading = dialogElement("div");
    const title = dialogElement("h2", "", "Upload XLSX as AAS");
    title.id = "fibro-import-title";
    heading.append(title, dialogElement("p", "", "Generate a complete AASX and upload it to BaSyx."));
    const close = dialogElement("button", "fibro-import-close", "×");
    close.type = "button";
    close.setAttribute("aria-label", "Close upload dialog");
    header.append(heading, close);

    const form = document.createElement("form");
    const fileLabel = dialogElement("label", "fibro-import-file");
    const filePrompt = dialogElement("strong", "", "Choose the completed product workbook");
    const fileHint = dialogElement("span", "", ".xlsx only · maximum 20 MB");
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
    input.required = true;
    fileLabel.append(filePrompt, fileHint, input);

    const status = dialogElement("div", "fibro-import-status");
    status.setAttribute("aria-live", "polite");
    const actions = dialogElement("div", "fibro-import-actions");
    const cancel = dialogElement("button", "fibro-import-secondary", "Cancel");
    cancel.type = "button";
    const submit = dialogElement("button", "fibro-import-primary", "Generate and upload AAS");
    submit.type = "submit";
    actions.append(cancel, submit);
    form.append(fileLabel, status, actions);
    dialog.append(header, form);
    overlay.append(dialog);
    document.body.append(overlay);
    input.focus();

    const dismiss = () => overlay.remove();
    close.addEventListener("click", dismiss);
    cancel.addEventListener("click", dismiss);
    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) dismiss();
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const file = input.files?.[0];
      if (!file) return;
      if (!file.name.toLowerCase().endsWith(".xlsx")) {
        renderImportStatus(status, "error", "Only .xlsx workbooks are supported.");
        return;
      }
      submit.disabled = true;
      input.disabled = true;
      renderImportStatus(status, "loading", "Generating the AAS and uploading it to BaSyx…");
      try {
        const body = new FormData();
        body.append("file", file, file.name);
        const response = await fetch(`${gatewayOrigin()}/api/admin/import`, {
          method: "POST",
          headers: { Authorization: `Bearer ${accessToken()}` },
          body,
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(payload.detail || payload.message || `Import failed with HTTP ${response.status}`);
        }
        renderImportSuccess(status, payload);
        cancel.textContent = "Close and refresh AAS list";
        cancel.onclick = () => window.location.reload();
        submit.remove();
      } catch (error) {
        renderImportStatus(status, "error", error instanceof Error ? error.message : "Import failed");
        submit.disabled = false;
        input.disabled = false;
      }
    });
  }

  function renderImportStatus(container, kind, message) {
    container.className = `fibro-import-status ${kind}`;
    container.replaceChildren(dialogElement("p", "", message));
  }

  function renderImportSuccess(container, payload) {
    container.className = "fibro-import-status success";
    const title = dialogElement("strong", "", "AAS uploaded successfully");
    const summary = dialogElement("p", "", payload.aasId || payload.message);
    container.replaceChildren(title, summary);
    const warnings = [...(payload.warnings || []), ...(payload.missingMandatory || [])];
    if (warnings.length) {
      const details = document.createElement("details");
      details.append(dialogElement("summary", "", `${warnings.length} warning(s)`));
      const list = document.createElement("ul");
      for (const warning of warnings) list.append(dialogElement("li", "", String(warning)));
      details.append(list);
      container.append(details);
    }
  }

  const importObserver = new MutationObserver(addImportMenuItem);
  importObserver.observe(document.documentElement, { childList: true, subtree: true });
  window.setInterval(addImportMenuItem, 400);

  const style = document.createElement("style");
  style.textContent = `
    .fibro-import-overlay { position: fixed; inset: 0; z-index: 10000; display: grid; place-items: center; padding: 20px; background: rgba(15, 23, 42, .58); }
    .fibro-import-dialog { width: min(620px, 100%); max-height: 90vh; overflow: auto; border-radius: 14px; padding: 24px; color: #172033; background: #fff; box-shadow: 0 24px 80px rgba(0,0,0,.3); }
    .fibro-import-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; margin-bottom: 22px; }
    .fibro-import-header h2 { margin: 0 0 5px; font-size: 1.45rem; }
    .fibro-import-header p { margin: 0; color: #667085; }
    .fibro-import-close { border: 0; padding: 0 5px; color: #667085; background: transparent; font-size: 2rem; line-height: 1; cursor: pointer; }
    .fibro-import-file { display: grid; gap: 6px; padding: 24px; border: 2px dashed #d0d5dd; border-radius: 10px; background: #fafafa; cursor: pointer; }
    .fibro-import-file span { color: #667085; font-size: .9rem; }
    .fibro-import-file input { margin-top: 12px; }
    .fibro-import-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 22px; }
    .fibro-import-actions button { border-radius: 8px; padding: 10px 16px; font-weight: 600; cursor: pointer; }
    .fibro-import-primary { border: 1px solid #d86600; color: #fff; background: #e86f00; }
    .fibro-import-primary:disabled { cursor: wait; opacity: .65; }
    .fibro-import-secondary { border: 1px solid #d0d5dd; color: #344054; background: #fff; }
    .fibro-import-status { margin-top: 16px; }
    .fibro-import-status p { margin: 0; }
    .fibro-import-status.loading { color: #475467; }
    .fibro-import-status.error { padding: 12px; border-radius: 8px; color: #912018; background: #fef3f2; }
    .fibro-import-status.success { padding: 12px; border-radius: 8px; color: #05603a; background: #ecfdf3; }
    .fibro-import-status details { margin-top: 10px; color: #475467; }
    .fibro-import-status ul { max-height: 180px; overflow: auto; padding-left: 20px; }
    @media (max-width: 600px) { .fibro-import-dialog { padding: 18px; } .fibro-import-actions { flex-direction: column-reverse; } }
  `;
  document.head.append(style);

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
