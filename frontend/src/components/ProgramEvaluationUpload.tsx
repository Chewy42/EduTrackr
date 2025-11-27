import React, { useCallback, useState } from "react";
import { FiUploadCloud, FiFileText, FiEye, FiArrowRight, FiExternalLink } from "react-icons/fi";
import { useAuth } from "../auth/AuthContext";

type UploadState = "idle" | "uploading" | "uploaded";

type Props = {
  onSuccess?: () => void;
};

export default function ProgramEvaluationUpload({ onSuccess }: Props) {
  const { jwt, mergePreferences, signOut } = useAuth();
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
    if (!candidate) {
      return;
    }
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
      
      if (response.status === 401) {
        signOut();
        return;
      }

      const body = await response.json().catch(() => ({} as { error?: string }));
      if (!response.ok) {
        setError(body.error || "Unable to upload file.");
        setUploadState("idle");
        return;
      }
      mergePreferences({ hasProgramEvaluation: true, onboardingComplete: false });
      setUploadState("uploaded");
      if (onSuccess) {
        onSuccess();
      }
    } catch {
      setError("Unable to upload file.");
      setUploadState("idle");
    }
  };

  const handleOpenPreview = async () => {
    // Only allow preview after a successful upload
    if (!jwt || uploadState !== "uploaded") {
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
    <div className="space-y-8">
      {/* Instructions Section */}
      <div className="rounded-2xl bg-blue-50/50 p-6 sm:p-8 border border-blue-100">
        <div className="text-center mb-6">
          <h3 className="text-lg sm:text-xl font-bold text-text-primary">Where is my Program Evaluation?</h3>
          <a 
            href="https://studentcenter.chapman.edu" 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-base sm:text-lg text-blue-600 hover:text-blue-500 inline-flex items-center gap-2 mt-2 font-medium"
          >
            Chapman Student Center <FiExternalLink />
          </a>
        </div>
        
        <div className="flex flex-col sm:flex-row items-center justify-center gap-8 sm:gap-12 py-4">
          <div className="relative group flex-1 w-full">
            <img 
              src="/onboarding_image_1.png" 
              alt="Step 1" 
              className="aspect-video w-full rounded-xl shadow-md border border-slate-200/60 object-cover transition-transform duration-300 group-hover:scale-[1.02]"
            />
          </div>
          <div className="text-blue-300 rotate-90 sm:rotate-0 flex-shrink-0">
            <FiArrowRight className="w-12 h-12 sm:w-16 sm:h-16" />
          </div>
          <div className="relative group flex-1 w-full">
            <img 
              src="/onboarding_image_2.png" 
              alt="Step 2" 
              className="aspect-video w-full rounded-xl shadow-md border border-slate-200/60 object-cover transition-transform duration-300 group-hover:scale-[1.02]"
            />
          </div>
        </div>
      </div>

      <div
        className={[
          "flex cursor-pointer flex-col items-center justify-center rounded-3xl border-3 border-dashed px-8 py-16 sm:px-12 sm:py-20 transition-colors duration-200",
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
        <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-blue-100 text-blue-600">
          <FiUploadCloud className="text-4xl" />
        </div>
        <div className="text-xl sm:text-2xl font-semibold text-text-primary text-center">
          Drag and drop your program evaluation PDF here
        </div>
        <div className="mt-3 text-base sm:text-lg text-text-secondary text-center">
          Or click to browse files. Only one PDF is stored per account.
        </div>
        {hasSelectedFile ? (
          <div className="mt-6 inline-flex items-center rounded-full bg-blue-50 px-6 py-3 text-base font-medium text-blue-700">
            <FiFileText className="mr-3 text-xl" />
            <span className="truncate max-w-[300px]">{file.name}</span>
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
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 sm:gap-6">
        <button
          type="button"
          onClick={handleUpload}
          disabled={!hasSelectedFile || uploadState === "uploading"}
          className={[
            "inline-flex items-center justify-center rounded-xl px-8 py-4 text-base sm:text-lg font-bold shadow-sm transition-all duration-200 w-full sm:w-auto transform active:scale-95",
            hasSelectedFile
              ? "bg-blue-600 text-white hover:bg-blue-500 hover:shadow-md"
              : "bg-blue-200 text-blue-50 cursor-not-allowed",
          ].join(" ")}
        >
          {uploadState === "uploading" ? "Uploading..." : "Upload PDF"}
        </button>
        <button
          type="button"
          onClick={handleOpenPreview}
          disabled={uploadState !== "uploaded"}
          className={[
            "inline-flex items-center justify-center rounded-xl px-6 py-4 text-base sm:text-lg font-medium shadow-sm ring-1 ring-slate-200 transition-colors duration-200 w-full sm:w-auto",
            uploadState === "uploaded"
              ? "bg-white text-text-secondary hover:text-text-primary hover:bg-slate-50"
              : "bg-slate-100 text-slate-400 cursor-not-allowed",
          ].join(" ")}
        >
          <FiEye className="mr-3 text-xl" />
          Open program evaluation
        </button>
      </div>
      {error ? (
        <div className="text-sm sm:text-base text-danger font-medium text-center bg-red-50 p-3 rounded-lg">
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


