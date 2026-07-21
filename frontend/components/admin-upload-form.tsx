"use client";

import { ChangeEvent, FormEvent, useRef, useState } from "react";
import { Icon } from "./icons";
import { ImportApiError, importProductFile, type ImportResult } from "@/lib/import/import-api";

type UploadState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; result: ImportResult }
  | { status: "error"; message: string; details: string[] };

export function AdminUploadForm() {
  const [file, setFile] = useState<File | null>(null);
  const [state, setState] = useState<UploadState>({ status: "idle" });
  const inputRef = useRef<HTMLInputElement>(null);

  function selectFile(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
    setState({ status: "idle" });
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setState({ status: "error", message: "No file selected", details: ["Choose a product source file before starting the import."] });
      return;
    }
    setState({ status: "loading" });
    try {
      const result = await importProductFile(file);
      setState({ status: "success", result });
    } catch (error) {
      if (error instanceof ImportApiError) {
        setState({ status: "error", message: error.message, details: error.details });
      } else {
        setState({ status: "error", message: "Import failed", details: ["An unexpected error occurred. Please retry."] });
      }
    }
  }

  return (
    <form className="upload-card" onSubmit={submit}>
      <div className="upload-heading"><div className="icon-tile"><Icon name="upload" /></div><div><h2>Import product data</h2><p>Upload a workbook, AAS environment, or packaged shell.</p></div></div>
      <button className="file-drop" type="button" onClick={() => inputRef.current?.click()}>
        <input ref={inputRef} type="file" accept=".xlsx,.json,.aasx" onChange={selectFile} hidden />
        <span className="file-icon"><Icon name="documents" /></span>
        {file ? <><strong>{file.name}</strong><span>{formatFileSize(file.size)} · Click to replace</span></> : <><strong>Choose a file</strong><span>.xlsx, .json, or .aasx</span></>}
      </button>
      <div className="upload-actions">
        <p>Future endpoint: <code>POST /api/admin/import</code></p>
        <button className="primary-button" type="submit" disabled={state.status === "loading"}>
          {state.status === "loading" ? <><span className="spinner" /> Importing…</> : <>Start import <Icon name="arrow" /></>}
        </button>
      </div>
      {state.status === "success" && <div className="notice success" role="status"><Icon name="check" /><div><strong>Import ready</strong><p>{state.result.message}</p><small>Reference: {state.result.importId}</small></div></div>}
      {state.status === "error" && <div className="notice error" role="alert"><span className="notice-symbol">!</span><div><strong>{state.message}</strong><ul>{state.details.map((detail) => <li key={detail}>{detail}</li>)}</ul></div></div>}
    </form>
  );
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}
