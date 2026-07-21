export type ImportResult = {
  fileName: string;
  message: string;
  importId: string;
};

export class ImportApiError extends Error {
  constructor(
    message: string,
    readonly details: string[],
  ) {
    super(message);
    this.name = "ImportApiError";
  }
}

const supportedExtensions = [".xlsx", ".json", ".aasx"];

/**
 * Mock import boundary. The live implementation should POST FormData to
 * /api/admin/import with the selected file under the field name `file`.
 */
export async function importProductFile(file: File): Promise<ImportResult> {
  const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  if (!supportedExtensions.includes(extension)) {
    throw new ImportApiError("Unsupported file type", [
      "Choose an .xlsx, .json, or .aasx file.",
    ]);
  }
  if (file.size === 0) {
    throw new ImportApiError("The selected file is empty", [
      "Export the source file again and retry the import.",
    ]);
  }

  await new Promise((resolve) => window.setTimeout(resolve, 900));
  return {
    fileName: file.name,
    message: "File validated and queued for the demo import.",
    importId: `mock-${Date.now()}`,
  };
}

export async function importProductFileLive(file: File): Promise<ImportResult> {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch("/api/admin/import", { method: "POST", body });
  const payload = (await response.json()) as ImportResult & {
    message?: string;
    details?: string[];
  };
  if (!response.ok) {
    throw new ImportApiError(
      payload.message ?? "The import service rejected the file.",
      payload.details ?? [],
    );
  }
  return payload;
}
