import { useState } from "react";
import { Copy, Download, Check, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Bill } from "@/lib/api";
import { errorMessage } from "@/lib/bill-format";
import { ErrorNotice } from "./shared";
function HighlightedJson({ value }: { value: Bill }) {
  const tokens = JSON.stringify(value, null, 2).split(
    /("(?:\\.|[^"\\])*"\s*:|"(?:\\.|[^"\\])*"|\bnull\b|\btrue\b|\bfalse\b|-?\d+(?:\.\d+)?)/g,
  );
  return (
    <pre className="json-code">
      <code>
        {tokens.map((token, i) => (
          <span
            key={i}
            className={
              token.startsWith('"')
                ? token.trim().endsWith(":")
                  ? "json-key"
                  : "json-string"
                : /^-?\d/.test(token)
                  ? "json-number"
                  : token === "null"
                    ? "json-null"
                    : ""
            }
          >
            {token}
          </span>
        ))}
      </code>
    </pre>
  );
}
export function JsonTab({ bill, billId }: { bill: Bill; billId: string }) {
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  const [failedAction, setFailedAction] = useState<"copy" | "download">("copy");
  async function copy() {
    setError("");
    try {
      await navigator.clipboard.writeText(JSON.stringify(bill, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch (err) {
      setFailedAction("copy");
      setError(`Could not copy the JSON. ${errorMessage(err)}`);
    }
  }
  function download() {
    setError("");
    try {
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(bill, null, 2)], { type: "application/json" }),
      );
      const link = document.createElement("a");
      link.href = url;
      link.download = `${billId.replace(/[^a-zA-Z0-9_-]/g, "_")}.json`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      setFailedAction("download");
      setError("Could not download this file. Please try again.");
    }
  }
  return (
    <div className="tab-body">
      <section className="panel">
        <div className="panel-heading">
          <h3>Extracted bill JSON</h3>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={copy}>
              {copied ? <Check /> : <Copy />}
              {copied ? "Copied" : "Copy"}
            </Button>
            <Button size="sm" variant="outline" onClick={download}>
              <Download />
              Download .json
            </Button>
          </div>
        </div>
        {error && <ErrorNotice message={error} retry={failedAction === "copy" ? copy : download} />}
        <details open className="json-details">
          <summary>
            {billId}.json
            <ChevronDown className="size-4" />
          </summary>
          <HighlightedJson value={bill} />
        </details>
      </section>
    </div>
  );
}
