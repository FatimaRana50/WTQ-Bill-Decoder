<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

- Keep Bill Decoder on the existing TanStack Start routing with its usable workspace at `/`; the project runtime requires this router.
- Put stateless external REST requests in a typed browser API client and keep image/bill/conversation in React state; the external service owns all decoding and calculations.
- Keep one component per workspace tab with shared formatting and error controls; this isolates each bill-review workflow.
