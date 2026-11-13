import React, { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  Loader2,
  UploadCloud,
  X,
} from 'lucide-react';
import { uploadCertificateApi } from '../api/certificates';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../components/ui/card';
import { Progress } from '../components/ui/progress';

export const UploadPage: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const handleFileChange = (file: File) => {
    setErrorMessage(null);

    // Validate size: 10MB
    const maxBytes = 10 * 1024 * 1024;
    if (file.size > maxBytes) {
      setErrorMessage('File size exceeds the 10MB limit. Please upload a smaller document.');
      return;
    }

    // Validate format
    const allowed = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg'];
    const isExtensionAllowed = /\.(pdf|jpg|jpeg|png)$/i.test(file.name);
    if (!allowed.includes(file.type) && !isExtensionAllowed) {
      setErrorMessage('Unsupported format. Please upload a PDF, JPG, or PNG certificate.');
      return;
    }

    setSelectedFile(file);

    if (file.type.startsWith('image/')) {
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
    } else {
      setPreviewUrl(null);
    }
  };

  const clearSelection = () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setSelectedFile(null);
    setPreviewUrl(null);
    setUploadProgress(0);
    setErrorMessage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setErrorMessage(null);
    setUploadProgress(15);

    // Simulated visual upload progress step
    const interval = setInterval(() => {
      setUploadProgress((prev) => (prev < 85 ? prev + 15 : prev));
    }, 200);

    try {
      const res = await uploadCertificateApi(selectedFile);
      clearInterval(interval);
      setUploadProgress(100);

      // Brief delay to display 100% then navigate to verify page
      setTimeout(() => {
        navigate(`/verify/${res.job_id}`);
      }, 500);
    } catch (err: any) {
      clearInterval(interval);
      setUploadProgress(0);
      const msg = err.response?.data?.detail || 'Document upload failed. Please try again.';
      setErrorMessage(msg);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-6">
      <Card className="shadow-sm border-slate-200">
        <CardHeader className="text-center pb-4">
          <CardTitle className="text-xl font-bold text-slate-900">
            Upload Certificate for Verification
          </CardTitle>
          <CardDescription>
            Submit academic, employment, or government credentials for automated AI forgery analysis
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {errorMessage && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{errorMessage}</AlertDescription>
            </Alert>
          )}

          {!selectedFile ? (
            <div
              onClick={() => fileInputRef.current?.click()}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              className={`h-72 border-2 border-dashed rounded-xl flex flex-col items-center justify-center p-6 text-center cursor-pointer transition-colors ${
                isDragging
                  ? 'border-blue-500 bg-blue-50/60'
                  : 'border-slate-300 hover:border-blue-400 hover:bg-slate-50'
              }`}
            >
              <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                accept=".pdf,.jpg,.jpeg,.png"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    handleFileChange(e.target.files[0]);
                  }
                }}
              />
              <div className="h-16 w-16 rounded-full bg-blue-50 flex items-center justify-center text-blue-600 mb-4 shadow-inner">
                <UploadCloud className="h-8 w-8" />
              </div>
              <p className="text-base font-semibold text-slate-800">
                Drag &amp; drop certificate here
              </p>
              <p className="text-xs text-slate-500 mt-1">
                or <span className="text-blue-600 font-medium underline">browse files</span> from your computer
              </p>
              <span className="inline-block mt-4 text-[11px] font-medium text-slate-400 uppercase tracking-wider bg-slate-100 px-3 py-1 rounded-full border">
                PDF, JPG, PNG &bull; Up to 10MB
              </span>
            </div>
          ) : (
            <div className="border border-slate-200 rounded-xl p-6 bg-slate-50/50">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                  {previewUrl ? (
                    <img
                      src={previewUrl}
                      alt="Certificate Preview"
                      className="h-24 w-24 object-cover rounded-lg border border-slate-200 shadow-sm"
                    />
                  ) : (
                    <div className="h-24 w-24 rounded-lg bg-blue-100/60 border border-blue-200 flex flex-col items-center justify-center text-blue-600">
                      <FileText className="h-10 w-10 mb-1" />
                      <span className="text-[10px] font-bold uppercase tracking-wider">PDF</span>
                    </div>
                  )}
                  <div>
                    <h4 className="text-sm font-semibold text-slate-900 break-all max-w-sm">
                      {selectedFile.name}
                    </h4>
                    <p className="text-xs text-slate-500 mt-1">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB &bull; {selectedFile.type || 'Document'}
                    </p>
                    <div className="flex items-center gap-1 text-xs text-emerald-600 font-medium mt-2">
                      <CheckCircle2 className="h-3.5 w-3.5" /> Ready for verification
                    </div>
                  </div>
                </div>

                {!uploading && (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={clearSelection}
                    className="text-slate-400 hover:text-red-600 hover:bg-red-50"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>

              {uploadProgress > 0 && (
                <div className="mt-6 space-y-2">
                  <div className="flex justify-between text-xs text-slate-600 font-medium">
                    <span>Processing Document &amp; Initializing AI Pipeline</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <Progress value={uploadProgress} />
                </div>
              )}
            </div>
          )}
        </CardContent>

        <CardFooter className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
          <span className="text-xs text-slate-400">
            End-to-end encrypted storage &amp; automatic forensic tamper audit
          </span>
          <Button
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
            className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700 min-w-[160px]"
          >
            {uploading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Analyzing...
              </>
            ) : (
              'Start Verification'
            )}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
};

