import React, { useCallback, useState } from "react";
import { FiUploadCloud, FiFileText, FiEye } from "react-icons/fi";
import { useAuth } from "../auth/AuthContext";

type UploadState = "idle" | "uploading" | "uploaded";

export default function ProgramEvaluationUpload() {
  const { jwt, mergePreferences } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const resetPreviewUrl = () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
  };

  const handleFiles = useCallback((files: FileList | null) => {
    if (!files || files.length === 0) {
      return;
    }
    const candidate = files[0];
    if (!candidate.name.toLowerCase().endsWith(".pdf")) {
      setError("Upload a single PDF file.");
      setFile(null);
      return;
    }
    setError(null);
    setFile(candidate);
    setUploadState("idle");
  }, []);

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(false);
    handleFiles(event.dataTransfer.files);
  };

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    if (!isDragging) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(false);
  };

  const handleFileInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    handleFiles(event.target.files);
  };

  const handleUpload = async () => {
    if (!file || !jwt || uploadState === "uploading") {
      return;
    }
    setUploadState("uploading");
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch("/api/program-evaluations", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${jwt}`,
        },
        body: formData,
      });
      const body = await response.json().catch(() => ({} as { error?: string }));
      if (!response.ok) {
        setError(body.error || "Unable to upload file.");
        setUploadState("idle");
        return;
      }
      mergePreferences({ hasProgramEvaluation: true });
      setUploadState("uploaded");
    } catch {
      setError("Unable to upload file.");
      setUploadState("idle");
    }
  };

  const handleOpenPreview = async () => {
    if (!jwt) {
      return;
    }
    try {
      const response = await fetch("/api/program-evaluations", {
        headers: {
          Authorization: `Bearer ${jwt}`,
        },
      });
      if (!response.ok) {
        return;
      }
      const blob = await response.blob();
      resetPreviewUrl();
      const url = URL.createObjectURL(blob);
      setPreviewUrl(url);
    } catch {
    }
  };

  const hasSelectedFile = !!file;

  return (
    <div className="space-y-6">
      <div
        className={[
          "flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-10 transition-colors duration-200",
          isDragging
            ? "border-blue-500 bg-blue-50/40"
            : "border-blue-200 bg-white hover:border-blue-400 hover:bg-blue-50/30",
        ].join(" ")}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => {
          const input = document.getElementById(
            "program-evaluation-file-input"
          ) as HTMLInputElement | null;
          if (input) {
            input.click();
          }
        }}
      >
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-blue-100 text-blue-600">
          <FiUploadCloud className="text-2xl" />
        </div>
        <div className="text-sm font-medium text-text-primary">
          Drag and drop your program evaluation PDF here
        </div>
        <div className="mt-1 text-xs text-text-secondary">
          Or click to browse files. Only one PDF is stored per account.
        </div>
        {hasSelectedFile ? (
          <div className="mt-4 inline-flex items-center rounded-full bg-blue-50 px-4 py-1.5 text-xs font-medium text-blue-700">
            <FiFileText className="mr-2 text-sm" />
            <span className="truncate max-w-[200px]">{file.name}</span>
          </div>
        ) : null}
      </div>
      <input
        id="program-evaluation-file-input"
        type="file"
        accept=".pdf,application/pdf"
        className="hidden"
        onChange={handleFileInputChange}
      />
      <div className="flex items-center justify-between gap-4">
        <button
          type="button"
          onClick={handleUpload}
          disabled={!hasSelectedFile || uploadState === "uploading"}
          className={[
            "inline-flex items-center justify-center rounded-xl px-4 py-2 text-sm font-medium shadow-sm transition-colors duration-200",
            hasSelectedFile
              ? "bg-blue-600 text-white hover:bg-blue-500"
              : "bg-blue-200 text-blue-50 cursor-not-allowed",
          ].join(" ")}
        >
          {uploadState === "uploading" ? "Uploading..." : "Upload PDF"}
        </button>
        <button
          type="button"
          onClick={handleOpenPreview}
          className="inline-flex items-center rounded-xl bg-white px-3 py-2 text-xs font-medium text-text-secondary shadow-sm ring-1 ring-slate-200 transition-colors duration-200 hover:text-text-primary"
        >
          <FiEye className="mr-2 text-sm" />
          Open program evaluation
        </button>
      </div>
      {error ? (
        <div className="text-xs text-danger">
          {error}
        </div>
      ) : null}
      {previewUrl ? (
        <div className="mt-4 h-[420px] overflow-hidden rounded-2xl border border-slate-200 bg-slate-50">
          <iframe
            title="Program evaluation"
            src={previewUrl}
            className="h-full w-full"
          />
        </div>
      ) : null}
    </div>
  );
}


