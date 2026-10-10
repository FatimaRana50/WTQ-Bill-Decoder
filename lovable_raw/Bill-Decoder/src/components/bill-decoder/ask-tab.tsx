import { useState, useRef, useEffect } from "react";
import { ArrowUp, ChevronDown, MessageCircle, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api, type Bill, type Answer } from "@/lib/api";
import { errorMessage } from "@/lib/bill-format";
import { ErrorNotice } from "./shared";
const questions = [
  "How much of my bill is taxes?",
  "How many months in my history went above 200 units?",
  "What is my average monthly consumption?",
  "How much extra would I pay if I pay after the due date?",
  "What is the average price I paid per unit this month?",
  "If I use 20% more units next month, roughly what would my bill be?",
  "What does the fuel price adjustment mean?",
];
type Message = { question: string; answer?: Answer; error?: string };
export function AskTab({ bill, image }: { bill: Bill; image: File }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (messages.length) end.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [messages, busy]);
  async function send(question: string, retryIndex?: number) {
    if (!question.trim() || busy) return;
    setBusy(true);
    setInput("");
    const index = retryIndex ?? messages.length;
    setMessages((old) =>
      retryIndex == null
        ? [...old, { question }]
        : old.map((item, i) => (i === index ? { question } : item)),
    );
    try {
      const answer = await api.ask(image, bill, question.trim());
      setMessages((old) => old.map((item, i) => (i === index ? { question, answer } : item)));
    } catch (error) {
      setMessages((old) =>
        old.map((item, i) => (i === index ? { question, error: errorMessage(error) } : item)),
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="tab-body">
      <div className="ask-heading">
        <span className="mini-icon">
          <MessageCircle />
        </span>
        <h2>Let’s make sense of your bill.</h2>
      </div>
      <div className="suggested-questions">
        {questions.map((question) => (
          <Button variant="outline" key={question} disabled={busy} onClick={() => send(question)}>
            {question}
            <ArrowUp className="size-3.5 rotate-45 shrink-0" />
          </Button>
        ))}
      </div>
      <div className="conversation" aria-live="polite">
        {messages.map((message, i) => (
          <div key={i} className="message-pair">
            <div className="question-bubble">{message.question}</div>
            {message.answer && (
              <div className="answer-bubble">
                <Sparkles className="size-4 text-primary mb-3" />
                <p>{message.answer.answer}</p>
                {message.answer.calculations.length > 0 && (
                  <details className="calculation-details">
                    <summary>
                      How this was calculated ({message.answer.calculations.length} steps)
                      <ChevronDown className="size-4" />
                    </summary>
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>What</th>
                            <th>Expression</th>
                            <th>Result</th>
                          </tr>
                        </thead>
                        <tbody>
                          {message.answer.calculations.map((calc, j) => (
                            <tr key={j}>
                              <td>{calc.name}</td>
                              <td>
                                <code>{calc.expression}</code>
                              </td>
                              <td>{calc.result == null ? "Not on bill" : String(calc.result)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </details>
                )}
              </div>
            )}
            {message.error && (
              <ErrorNotice
                message={message.error}
                retry={() => send(message.question, i)}
                busy={busy}
              />
            )}
          </div>
        ))}
        {busy && (
          <div className="answer-bubble typing-indicator" aria-label="Reading your bill to answer">
            <span />
            <span />
            <span />
          </div>
        )}
        <div ref={end} />
      </div>
      <form
        className="ask-form"
        onSubmit={(event) => {
          event.preventDefault();
          send(input);
        }}
      >
        <input
          className="form-input"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Ask a question about your bill…"
          aria-label="Question about your bill"
          disabled={busy}
        />
        <Button
          size="icon"
          type="submit"
          aria-label="Send question"
          title="Send question"
          disabled={busy || !input.trim()}
        >
          <ArrowUp />
        </Button>
      </form>
    </div>
  );
}
