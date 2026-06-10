export default function AuthLayout({ children }) {
  return (
    <div className="min-h-screen md:grid md:grid-cols-2">
      {/* Brand panel */}
      <div className="relative hidden flex-col justify-between overflow-hidden bg-ink p-12 text-paper md:flex">
        <div
          aria-hidden
          className="absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage:
              "radial-gradient(circle at 18% 22%, #fff 0, transparent 38%), radial-gradient(circle at 82% 72%, #fff 0, transparent 34%)",
          }}
        />
        <div className="relative flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-paper font-display text-ink">
            S
          </span>
          <span className="font-display text-xl tracking-tight">Support Desk</span>
        </div>

        <div className="relative">
          <h2 className="font-display text-[2.6rem] leading-[1.08] tracking-tight">
            Support,
            <br />
            handled with care.
          </h2>
          <p className="mt-5 max-w-sm leading-relaxed text-paper/65">
            Create, triage, and resolve tickets in one calm workspace — with AI that classifies
            each request and drafts a reply the moment it arrives.
          </p>
        </div>

        <p className="relative text-sm tracking-tight text-paper/40">
          AI-assisted triage · Built for support teams
        </p>
      </div>

      {/* Form panel */}
      <div className="flex min-h-screen items-center justify-center px-5 py-12 md:min-h-0">
        <div className="w-full max-w-sm animate-rise">{children}</div>
      </div>
    </div>
  );
}
