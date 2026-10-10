import { AlertCircle, RotateCw, LoaderCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
export function ErrorNotice({
  message,
  retry,
  busy = false,
}: {
  message: string;
  retry: () => void;
  busy?: boolean;
}) {
  return (
    <div role="alert" className="error-notice">
      <AlertCircle className="size-4 shrink-0" />
      <p>{message}</p>
      <Button variant="ghost" size="sm" onClick={retry} disabled={busy}>
        <RotateCw />
        Retry
      </Button>
    </div>
  );
}
export function Busy({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <LoaderCircle className="size-4 animate-spin" />
      {label}
    </span>
  );
}
export function Value({ value }: { value: string }) {
  return (
    <span className={value === "Not on bill" ? "text-muted-foreground font-normal text-sm" : ""}>
      {value}
    </span>
  );
}
