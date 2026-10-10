import {
  Check,
  TriangleAlert,
  CalendarDays,
  ArrowUpRight,
  Zap,
  ReceiptText,
  CircleHelp,
} from "lucide-react";
import type { Bill } from "@/lib/api";
import { date, money, pretty } from "@/lib/bill-format";
import { Value } from "./shared";
function LineItems({
  title,
  entries,
  total,
  tax = false,
}: {
  title: string;
  entries: Bill["charges"];
  total: number | null;
  tax?: boolean;
}) {
  return (
    <section className="panel line-items">
      <div className="panel-heading">
        <h3>{title}</h3>
        <ReceiptText className={tax ? "text-warning size-4" : "text-primary size-4"} />
      </div>
      {entries.length ? (
        <table>
          <thead>
            <tr>
              <th>Type</th>
              <th className="text-right">Amount</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry, i) => (
              <tr key={`${entry.type}-${i}`}>
                <td>{pretty(entry.type)}</td>
                <td
                  className={`text-right tabular-nums ${entry.amount != null && entry.amount < 0 ? "text-success" : ""}`}
                >
                  <Value value={money(entry.amount)} />
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td>Total {title.toLowerCase()}</td>
              <td className="text-right">
                <Value value={money(total)} />
              </td>
            </tr>
          </tfoot>
        </table>
      ) : (
        <p className="empty-text">
          {tax && total != null
            ? `Single combined tax amount printed: ${money(total)}`
            : "No itemized amounts printed on this bill."}
        </p>
      )}
    </section>
  );
}
export function SummaryTab({ bill, issues }: { bill: Bill; issues: string[] }) {
  const sum =
    bill.total_charges != null && bill.total_taxes != null
      ? bill.total_charges + bill.total_taxes
      : null;
  const showBar =
    sum != null &&
    sum > 0 &&
    bill.total_charges != null &&
    bill.total_taxes != null &&
    bill.total_charges >= 0 &&
    bill.total_taxes >= 0;
  const chargePercent = showBar ? ((bill.total_charges ?? 0) / (sum ?? 1)) * 100 : 0;
  return (
    <div className="tab-body">
      <div className="badge-row">
        <span className="badge provider-badge">
          {bill.provider ? pretty(bill.provider) : "Not on bill"}
        </span>
        <span className="badge">{bill.tariff ?? "Not on bill"}</span>
        <span className="badge">
          <CalendarDays className="size-3.5" />
          {date(bill.bill_month)}
        </span>
        <span className={`badge ${issues.length ? "flag-badge" : "success-badge"}`}>
          {issues.length ? <TriangleAlert className="size-3.5" /> : <Check className="size-3.5" />}
          {issues.length ? `${issues.length} checks flagged` : "All checks passed"}
        </span>
      </div>
      <div className="kpi-grid">
        <section className="panel kpi primary-kpi">
          <span className="kpi-label">
            Payable by due date
            <CalendarDays className="size-4" />
          </span>
          <h3>
            <Value value={money(bill.payable_within_due_date)} />
          </h3>
          <p>Due {date(bill.due_date)}</p>
        </section>
        <section className="panel kpi">
          <span className="kpi-label">
            Payable after due date
            <ArrowUpRight className="text-warning size-4" />
          </span>
          <h3 className="text-warning">
            <Value value={money(bill.payable_after_due_date)} />
          </h3>
          <p>Highest late amount</p>
        </section>
        <section className="panel kpi">
          <span className="kpi-label">
            Units consumed
            <Zap className="text-primary size-4" />
          </span>
          <h3>
            <Value
              value={
                bill.units_consumed == null
                  ? "Not on bill"
                  : `${bill.units_consumed.toLocaleString()} kWh`
              }
            />
          </h3>
          <p>
            {bill.previous_reading ?? "Not on bill"} → {bill.current_reading ?? "Not on bill"}
          </p>
        </section>
      </div>
      <section className="panel breakdown">
        <div className="panel-heading">
          <h3>Where your money goes</h3>
          <span className="text-xs text-muted-foreground">Charges & taxes</span>
        </div>
        {showBar ? (
          <>
            <div
              className="money-bar"
              role="img"
              aria-label={`Charges ${chargePercent.toFixed(1)} percent, taxes ${(100 - chargePercent).toFixed(1)} percent`}
            >
              <span className="charges-segment" style={{ width: `${chargePercent}%` }} />
              <span className="taxes-segment" style={{ width: `${100 - chargePercent}%` }} />
            </div>
            <div className="breakdown-legend">
              <span>
                <i className="charges-dot" />
                Charges <strong>{money(bill.total_charges)}</strong>
                <small>{chargePercent.toFixed(1)}%</small>
              </span>
              <span>
                <i className="taxes-dot" />
                Taxes <strong>{money(bill.total_taxes)}</strong>
                <small>{(100 - chargePercent).toFixed(1)}%</small>
              </span>
            </div>
          </>
        ) : (
          <div className="breakdown-legend">
            <span>
              Charges <Value value={money(bill.total_charges)} />
            </span>
            <span>
              Taxes <Value value={money(bill.total_taxes)} />
            </span>
          </div>
        )}
      </section>
      <div className="detail-grid">
        <LineItems title="Charges" entries={bill.charges} total={bill.total_charges} />
        <LineItems title="Taxes" entries={bill.taxes} total={bill.total_taxes} tax />
      </div>
      <section className="bill-stats">
        {[
          ["Current bill", money(bill.current_bill)],
          ["Arrears", money(bill.arrears)],
          [
            "Sanctioned load",
            bill.sanctioned_load_kw == null ? "Not on bill" : `${bill.sanctioned_load_kw} kW`,
          ],
          ["Issue date", date(bill.issue_date)],
          ["Reading date", date(bill.reading_date)],
        ].map(([label, value]) => (
          <div key={label}>
            <span>
              {label}
              {label === "Arrears" && (
                <span
                  title="Negative arrears are a credit carried forward, reducing your bill."
                  tabIndex={0}
                  className="inline-block"
                >
                  <CircleHelp
                    className="size-3.5 inline ml-1"
                    aria-label="Negative arrears are a credit carried forward, reducing your bill."
                    role="img"
                  />
                </span>
              )}
            </span>
            <strong
              className={
                label === "Arrears" && bill.arrears != null && bill.arrears < 0
                  ? "text-success"
                  : ""
              }
            >
              <Value value={value ?? "Not on bill"} />
            </strong>
          </div>
        ))}
      </section>
    </div>
  );
}
