import { useEffect, useState } from "react";
import { Check, CheckCheck, X, ScanEye, Sparkles, ClipboardCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api, type Bill, type Comparison, type SecondOpinion } from "@/lib/api";
import { errorMessage, fieldValue, pretty } from "@/lib/bill-format";
import { Busy, ErrorNotice, Value } from "./shared";
export function VerifyTab({
  bill,
  image,
  billId,
  issues,
}: {
  bill: Bill;
  image: File;
  billId: string;
  issues: string[];
}) {
  const [opinion, setOpinion] = useState<SecondOpinion | null>(null);
  const [opinionBusy, setOpinionBusy] = useState(false);
  const [opinionError, setOpinionError] = useState("");
  const [expected, setExpected] = useState("");
  const [expectedStatus, setExpectedStatus] = useState("loading");
  const [expectedError, setExpectedError] = useState("");
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [compareBusy, setCompareBusy] = useState(false);
  const [compareError, setCompareError] = useState("");
  const [expectedAttempt, setExpectedAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setExpectedStatus("loading");
    setExpectedError("");
    api
      .expected(billId)
      .then((result) => {
        if (active) {
          setExpectedStatus(result ? "loaded" : "missing");
          if (result) setExpected(JSON.stringify(result, null, 2));
        }
      })
      .catch((error) => {
        if (active) {
          setExpectedStatus("error");
          setExpectedError(errorMessage(error));
        }
      });
    return () => {
      active = false;
    };
  }, [billId, expectedAttempt]);
  async function secondOpinion() {
    setOpinionBusy(true);
    setOpinionError("");
    try {
      setOpinion(await api.secondOpinion(image, bill));
    } catch (error) {
      setOpinionError(errorMessage(error));
    } finally {
      setOpinionBusy(false);
    }
  }
  async function compare() {
    setCompareError("");
    let parsed: Record<string, unknown>;
    try {
      const value: unknown = JSON.parse(expected);
      if (typeof value !== "object" || value === null || Array.isArray(value)) throw new Error();
      parsed = value as Record<string, unknown>;
    } catch {
      setCompareError("Paste a valid JSON object containing your expected bill values.");
      return;
    }
    setCompareBusy(true);
    try {
      setComparison(await api.compare(bill, parsed));
    } catch (error) {
      setCompareError(errorMessage(error));
    } finally {
      setCompareBusy(false);
    }
  }
  return (
    <div className="tab-body">
      <section className="panel">
        <div className="panel-heading">
          <h3 className="flex items-center gap-2">
            <ClipboardCheck className="size-4 text-primary" />
            Consistency checks
          </h3>
        </div>
        {issues.length === 0 ? (
          <div className="check-notice">
            <CheckCheck className="size-5 shrink-0" />
            <div>
              <strong>Everything adds up</strong>
              <p>Charges and taxes add up, readings match units, dates are valid.</p>
            </div>
          </div>
        ) : (
          issues.map((issue, i) => (
            <div className="flag-notice" key={i}>
              <X className="size-4 shrink-0" />
              {issue}
            </div>
          ))
        )}
      </section>
      <section className="panel">
        <div className="panel-heading">
          <h3 className="flex items-center gap-2">
            <ScanEye className="size-4 text-primary" />
            Compare to image
          </h3>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Field</th>
                <th>Extracted value</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(bill).map(([field, value]) => (
                <tr key={field}>
                  <td>{pretty(field)}</td>
                  <td>
                    <Value value={fieldValue(field, value)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="panel">
        <div className="panel-heading">
          <h3 className="flex items-center gap-2">
            <Sparkles className="size-4 text-primary" />
            Second opinion
          </h3>
          <Button size="sm" variant="outline" onClick={secondOpinion} disabled={opinionBusy}>
            {opinionBusy ? (
              <Busy label="Reading again…" />
            ) : (
              <>
                <Sparkles />
                Get second opinion
              </>
            )}
          </Button>
        </div>
        {opinionError && (
          <ErrorNotice message={opinionError} retry={secondOpinion} busy={opinionBusy} />
        )}{" "}
        {opinion ? (
          opinion.agrees ? (
            <div className="check-notice">
              <Check className="size-5" />
              The second model read exactly the same values.
            </div>
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Field</th>
                    <th>Primary</th>
                    <th>Second</th>
                  </tr>
                </thead>
                <tbody>
                  {opinion.differences.map((diff, i) => (
                    <tr className="text-warning" key={`${diff.field}-${i}`}>
                      <td>{pretty(diff.field)}</td>
                      <td>{fieldValue(diff.field, diff.primary)}</td>
                      <td>{fieldValue(diff.field, diff.second)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        ) : (
          !opinionError && (
            <p className="empty-text">
              {opinionBusy
                ? "Checking the original image with a second model."
                : "No second opinion requested yet."}
            </p>
          )
        )}
      </section>
      <section className="panel">
        <div className="panel-heading">
          <h3>Compare with expected values</h3>
        </div>
        {expectedStatus === "loading" && (
          <p className="empty-text">
            <Busy label="Looking for an answer key…" />
          </p>
        )}
        {expectedStatus === "missing" && (
          <p className="empty-text">
            No answer key is available for this bill. You can add expected values below.
          </p>
        )}
        {expectedStatus === "loaded" && (
          <p className="text-success text-sm mb-3">Answer key loaded for {billId}.</p>
        )}
        {expectedError && (
          <ErrorNotice message={expectedError} retry={() => setExpectedAttempt((n) => n + 1)} />
        )}
        <label className="field-label" htmlFor="expected-json">
          Expected bill JSON
        </label>
        <textarea
          id="expected-json"
          className="form-input json-input"
          rows={6}
          value={expected}
          placeholder="Paste expected JSON"
          onChange={(event) => {
            setExpected(event.target.value);
            setComparison(null);
          }}
        />
        <Button className="mt-3" disabled={compareBusy || !expected.trim()} onClick={compare}>
          {compareBusy ? (
            <Busy label="Comparing…" />
          ) : (
            <>
              <ClipboardCheck />
              Compare values
            </>
          )}
        </Button>
        {compareError && (
          <ErrorNotice message={compareError} retry={compare} busy={compareBusy} />
        )}{" "}
        {comparison && (
          <div className="mt-6">
            <div className="accuracy-summary">
              <svg
                viewBox="0 0 100 100"
                className="accuracy-ring"
                role="img"
                aria-label={`${(comparison.accuracy * 100).toFixed(1)} percent accuracy`}
              >
                <circle cx="50" cy="50" r="42" className="ring-track" />
                <circle
                  cx="50"
                  cy="50"
                  r="42"
                  className="ring-value"
                  strokeDasharray={`${Math.max(0, Math.min(1, comparison.accuracy)) * 264} 264`}
                />
                <text x="50" y="55" textAnchor="middle">
                  {Math.round(comparison.accuracy * 100)}%
                </text>
              </svg>
              <div>
                <h3>
                  {comparison.correct} of {comparison.total} fields match
                </h3>
                <p className="text-muted-foreground text-sm">
                  Accuracy against your expected values
                </p>
              </div>
            </div>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Field</th>
                    <th>Extracted</th>
                    <th>Expected</th>
                    <th>
                      <span className="sr-only">Match</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {comparison.fields.map((field, i) => (
                    <tr key={`${field.field}-${i}`}>
                      <td>{pretty(field.field)}</td>
                      <td>
                        <Value value={fieldValue(field.field, field.predicted)} />
                      </td>
                      <td>
                        <Value value={fieldValue(field.field, field.expected)} />
                      </td>
                      <td>
                        {field.ok ? (
                          <Check className="text-success size-4" aria-label="Matches" />
                        ) : (
                          <X className="text-destructive size-4" aria-label="Does not match" />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
