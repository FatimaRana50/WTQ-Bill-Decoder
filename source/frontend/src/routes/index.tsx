import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import {
  Zap,
  Moon,
  Sun,
  Upload,
  ArrowUpRight,
  ShieldCheck,
  FileImage,
  RefreshCw,
  ZoomIn,
  FileText,
  ScanLine,
  MessageCircle,
  Braces,
  Check,
  LoaderCircle,
  LockKeyhole,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { api, type DecodedBill } from "@/lib/api";
import { errorMessage, validateImage } from "@/lib/bill-format";
import { ErrorNotice } from "@/components/bill-decoder/shared";
import { SummaryTab } from "@/components/bill-decoder/summary-tab";
import { VerifyTab } from "@/components/bill-decoder/verify-tab";
import { AskTab } from "@/components/bill-decoder/ask-tab";
import { JsonTab } from "@/components/bill-decoder/json-tab";
export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Bill Decoder — Understand your electricity bill" },
      {
        name: "description",
        content:
          "Read, verify, and understand your K-Electric, LESCO, or IESCO electricity bill. Every amount, every tax, explained.",
      },
      { property: "og:title", content: "Bill Decoder — Understand your electricity bill" },
      {
        property: "og:description",
        content:
          "Upload your Pakistani electricity bill to review its charges, verify extracted details, and ask questions.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Index,
});
function BillIllustration() {
  return (
    <svg className="bill-illustration" viewBox="0 0 122 118" aria-hidden="true">
      <rect
        className="illustration-back"
        x="32"
        y="16"
        width="61"
        height="86"
        rx="7"
        transform="rotate(12 62 58)"
      />
      <rect
        className="illustration-paper"
        x="25"
        y="9"
        width="64"
        height="88"
        rx="7"
        transform="rotate(-7 57 53)"
      />
      <g transform="rotate(-7 57 53)">
        <path d="M53 24l-9 14h9l-3 12 12-16h-10z" fill="currentColor" />
        <path className="illustration-line" d="M39 58h37M39 67h22M39 79h11M64 79h12" />
      </g>
      <circle className="illustration-circle" cx="90" cy="86" r="18" />
      <path
        className="illustration-light"
        d="m82 86 5 5 10-11"
        fill="none"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
function Index() {
  const [dark, setDark] = useState(false);
  const [health, setHealth] = useState<"checking" | "connected" | "offline">("checking");
  const [healthError, setHealthError] = useState("");
  const [samples, setSamples] = useState<string[]>([]);
  const [samplesBusy, setSamplesBusy] = useState(true);
  const [samplesError, setSamplesError] = useState("");
  const [sampleBusy, setSampleBusy] = useState("");
  const [failedSample, setFailedSample] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [imageError, setImageError] = useState(false);
  const [decoded, setDecoded] = useState<DecodedBill | null>(null);
  const [loading, setLoading] = useState(false);
  const [decodeError, setDecodeError] = useState("");
  const [uploadError, setUploadError] = useState("");
  const [progress, setProgress] = useState(0);
  const [dragging, setDragging] = useState(false);
  const [lightbox, setLightbox] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const requestId = useRef(0);
  async function checkHealth() {
    setHealth("checking");
    setHealthError("");
    try {
      const result = await api.health();
      if (result.status !== "ok")
        throw new Error("The bill service is not ready yet. Please try again.");
      setHealth("connected");
    } catch (error) {
      setHealth("offline");
      setHealthError(errorMessage(error));
    }
  }
  async function loadSamples() {
    setSamplesBusy(true);
    setSamplesError("");
    setFailedSample("");
    try {
      setSamples(await api.samples());
    } catch (error) {
      setSamplesError(errorMessage(error));
    } finally {
      setSamplesBusy(false);
    }
  }
  useEffect(() => {
    void checkHealth();
    void loadSamples();
  }, []);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);
  useEffect(() => {
    if (!file) {
      setPreview("");
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    setImageError(false);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  useEffect(() => {
    if (!loading) return;
    setProgress(0);
    const timer = setTimeout(() => setProgress(1), 9000);
    return () => clearTimeout(timer);
  }, [loading]);
  async function decode(image: File) {
    const id = ++requestId.current;
    setLoading(true);
    setDecodeError("");
    setDecoded(null);
    try {
      const result = await api.decode(image);
      if (id === requestId.current) {
        setDecoded(result);
        setProgress(2);
      }
    } catch (error) {
      if (id === requestId.current) setDecodeError(errorMessage(error));
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }
  function chooseFile(image: File) {
    const error = validateImage(image);
    if (error) {
      setUploadError(error);
      return;
    }
    setUploadError("");
    setFile(image);
    void decode(image);
  }
  async function chooseSample(name: string) {
    if (sampleBusy) return;
    setSampleBusy(name);
    setSamplesError("");
    setFailedSample("");
    try {
      chooseFile(await api.sample(name));
    } catch (error) {
      setFailedSample(name);
      setSamplesError(errorMessage(error));
    } finally {
      setSampleBusy("");
    }
  }
  function reset() {
    ++requestId.current;
    setFile(null);
    setDecoded(null);
    setLoading(false);
    setDecodeError("");
    setUploadError("");
    setLightbox(false);
    if (input.current) input.current.value = "";
  }
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="header-inner">
          <a href="/" className="brand">
            <span className="brand-icon">
              <Zap />
            </span>
            Bill Decoder
          </a>
          <div className="header-actions">
            <span className={`api-pill ${health === "connected" ? "connected" : ""}`} role="status">
              <span className="status-dot" />
              {health === "checking"
                ? "Connecting to API"
                : health === "connected"
                  ? "API connected"
                  : "API offline"}
            </span>
            <span className="header-divider" />
            <Button
              variant="ghost"
              size="icon"
              aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
              title={dark ? "Light mode" : "Dark mode"}
              onClick={() => setDark((value) => !value)}
            >
              {dark ? <Sun /> : <Moon />}
            </Button>
          </div>
        </div>
      </header>
      <main className="main-content">
        <input
          ref={input}
          type="file"
          className="sr-only"
          tabIndex={-1}
          accept="image/png,image/jpeg,.png,.jpg,.jpeg"
          aria-label="Upload electricity bill"
          onChange={(event) => {
            const image = event.target.files?.[0];
            if (image) chooseFile(image);
            event.target.value = "";
          }}
        />
        {!file ? (
          <>
            <section className="intro">
              <span className="eyebrow">
                <Sparkles className="size-3" />A little clarity. A lot less confusion.
              </span>
              <h1>
                Your electricity bill.
                <br />
                <span>Decoded.</span>
              </h1>
              <p>
                Every charge, every tax, every number — made clear. <br />
                Upload your bill and understand exactly what you’re paying for.
              </p>
            </section>
            <section className="upload-section">
              <div
                className={`upload-area ${dragging ? "dragging" : ""}`}
                onDragOver={(event) => {
                  event.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={(event) => {
                  if (!event.currentTarget.contains(event.relatedTarget as Node | null))
                    setDragging(false);
                }}
                onDrop={(event) => {
                  event.preventDefault();
                  setDragging(false);
                  const image = event.dataTransfer.files[0];
                  if (image) chooseFile(image);
                }}
              >
                <BillIllustration />
                <h2>{dragging ? "Drop your bill here" : "Drop your electricity bill here"}</h2>
                <p>Drag & drop a photo or scan, or choose a file below.</p>
                <Button className="upload-button" onClick={() => input.current?.click()}>
                  <Upload />
                  Choose a bill
                  <ArrowUpRight className="ml-3" />
                </Button>
                <div className="file-note">PNG or JPG · Up to 15 MB</div>
              </div>
              <p className="privacy-note">
                <LockKeyhole className="size-3" />
                No account needed. Your bill stays in this session.
              </p>
              {uploadError && (
                <ErrorNotice message={uploadError} retry={() => input.current?.click()} />
              )}
              <div className="samples-section">
                <div className="sample-label">Or try a sample bill</div>
                {samplesBusy ? (
                  <div className="samples-row" aria-label="Loading sample bills">
                    <span className="sample-loading" />
                    <span className="sample-loading" />
                    <span className="sample-loading" />
                  </div>
                ) : samples.length > 0 ? (
                  <div className="samples-row">
                    {samples.map((name) => (
                      <Button
                        variant="outline"
                        size="sm"
                        key={name}
                        disabled={!!sampleBusy}
                        onClick={() => chooseSample(name)}
                      >
                        {sampleBusy === name ? (
                          <LoaderCircle className="animate-spin" />
                        ) : (
                          <FileText />
                        )}
                        {name}
                        <ArrowUpRight />
                      </Button>
                    ))}
                  </div>
                ) : (
                  !samplesError && (
                    <p className="samples-empty">No sample bills are currently available.</p>
                  )
                )}
                {samplesError && (
                  <ErrorNotice
                    message={samplesError}
                    retry={() => (failedSample ? chooseSample(failedSample) : loadSamples())}
                    busy={!!sampleBusy}
                  />
                )}
              </div>
              <div className="supported">
                <p>Made for your electricity provider</p>
                <div className="provider-row">
                  <span className="provider-logo">
                    <Zap />
                    K-Electric
                  </span>
                  <span className="provider-separator" />
                  <span className="provider-logo">
                    <ShieldCheck />
                    LESCO
                  </span>
                  <span className="provider-separator" />
                  <span className="provider-logo">
                    <Zap />
                    IESCO
                  </span>
                </div>
              </div>
              {healthError && (
                <ErrorNotice
                  message={healthError}
                  retry={checkHealth}
                  busy={health === "checking"}
                />
              )}
            </section>
          </>
        ) : (
          <>
            <div className="workspace-heading">
              <div>
                <h1>Your bill, decoded.</h1>
                <p>Read the details. Check the numbers. Get clear answers.</p>
              </div>
              <span className="eyebrow">
                <ShieldCheck className="size-3" />
                Your bill. Your clarity.
              </span>
            </div>
            <div className="workspace">
              <aside className="image-panel">
                <div className="image-title">
                  <span>Original bill</span>
                  <FileImage className="size-4 text-muted-foreground" />
                </div>
                {imageError ? (
                  <ErrorNotice
                    message="This image could not be displayed. Choose a different bill."
                    retry={() => input.current?.click()}
                  />
                ) : (
                  <Button
                    variant="ghost"
                    className="bill-preview"
                    onClick={() => setLightbox(true)}
                    aria-label="Zoom bill image"
                    title="Zoom bill image"
                  >
                    {preview && (
                      <img
                        src={preview}
                        alt="Your original electricity bill"
                        onError={() => setImageError(true)}
                      />
                    )}
                    <span className="preview-zoom">
                      <ZoomIn className="size-4" />
                    </span>
                  </Button>
                )}
                <div className="file-info">
                  <FileImage className="size-5 text-primary" />
                  <div>
                    <p>{file.name}</p>
                    <small>{(file.size / 1024 / 1024).toFixed(2)} MB · Original image</small>
                  </div>
                </div>
                <Button variant="outline" className="w-full" onClick={reset}>
                  <RefreshCw />
                  Use a different bill
                </Button>
              </aside>
              <div className="workspace-right">
                {loading ? (
                  <section className="panel decode-loading" aria-live="polite">
                    <h2 className="progress-title">Making sense of your bill…</h2>
                    <p className="progress-note">
                      This can take up to 40 seconds. We’re reading the details carefully.
                    </p>
                    <div className="progress-steps">
                      {["Reading the bill", "Checking the numbers", "Done"].map((step, index) => (
                        <span className={progress === index ? "active" : ""} key={step}>
                          <span className="step-number">
                            {index < progress ? (
                              <Check className="size-3" />
                            ) : index === progress ? (
                              <LoaderCircle className="size-3 animate-spin" />
                            ) : (
                              index + 1
                            )}
                          </span>
                          {step}
                          {index < 2 && <span className="text-muted-foreground ml-1">→</span>}
                        </span>
                      ))}
                    </div>
                    <div className="skeleton-grid">
                      <div className="skeleton-block" />
                      <div className="skeleton-block" />
                      <div className="skeleton-block" />
                    </div>
                    <div className="skeleton-block skeleton-wide" />
                    <div className="skeleton-block skeleton-wide" />
                  </section>
                ) : decodeError ? (
                  <section className="panel">
                    <h2 className="progress-title">We couldn’t read this bill yet.</h2>
                    <p className="progress-note">
                      Your original image is ready. Try decoding it again.
                    </p>
                    <ErrorNotice message={decodeError} retry={() => decode(file)} />
                  </section>
                ) : (
                  decoded && (
                    <Tabs defaultValue="summary" key={decoded.bill_id}>
                      <TabsList className="workspace-tabs">
                        {[
                          { id: "summary", label: "Summary", Icon: FileText },
                          { id: "verify", label: "Verify", Icon: ScanLine },
                          { id: "ask", label: "Ask", Icon: MessageCircle },
                          { id: "json", label: "JSON", Icon: Braces },
                        ].map(({ id, label, Icon }) => (
                          <TabsTrigger key={id} value={id} className="workspace-tab">
                            <Icon className="size-4" />
                            {label}
                          </TabsTrigger>
                        ))}
                      </TabsList>
                      <TabsContent
                        value="summary"
                        forceMount
                        className="data-[state=inactive]:hidden"
                      >
                        <SummaryTab bill={decoded.bill} issues={decoded.issues} />
                      </TabsContent>
                      <TabsContent
                        value="verify"
                        forceMount
                        className="data-[state=inactive]:hidden"
                      >
                        <VerifyTab
                          bill={decoded.bill}
                          image={file}
                          billId={decoded.bill_id}
                          issues={decoded.issues}
                        />
                      </TabsContent>
                      <TabsContent value="ask" forceMount className="data-[state=inactive]:hidden">
                        <AskTab bill={decoded.bill} image={file} />
                      </TabsContent>
                      <TabsContent value="json" forceMount className="data-[state=inactive]:hidden">
                        <JsonTab bill={decoded.bill} billId={decoded.bill_id} />
                      </TabsContent>
                    </Tabs>
                  )
                )}
              </div>
            </div>
            <Dialog open={lightbox} onOpenChange={setLightbox}>
              <DialogContent className="lightbox-content">
                <DialogTitle>Original electricity bill</DialogTitle>
                <DialogDescription>{file.name}</DialogDescription>
                <img
                  src={preview}
                  className="lightbox-image"
                  alt="Enlarged original electricity bill"
                />
              </DialogContent>
            </Dialog>
          </>
        )}
      </main>
      <footer className="app-footer">
        <p className="footer-note">
          <ShieldCheck className="size-3.5" />
          Answers use only the information printed on your bill.
        </p>
        <p className="footer-secondary">A clearer bill. A more confident you.</p>
      </footer>
    </div>
  );
}
