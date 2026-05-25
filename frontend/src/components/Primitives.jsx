import React from "react";

export function Eyebrow({ children, className = "", testid }) {
  return (
    <div
      data-testid={testid}
      className={`label-eyebrow ${className}`}
    >
      {children}
    </div>
  );
}

export function Panel({ children, title, eyebrow, action, className = "", testid }) {
  return (
    <section
      data-testid={testid}
      className={`bg-ferret-surface border border-ferret-border ${className}`}
    >
      {(title || eyebrow || action) && (
        <header className="flex items-center justify-between px-5 py-3 border-b border-ferret-border">
          <div>
            {eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
            {title && (
              <h3 className="text-base font-medium tracking-tight text-ferret-textPrimary mt-0.5">
                {title}
              </h3>
            )}
          </div>
          {action}
        </header>
      )}
      <div>{children}</div>
    </section>
  );
}

export function Stat({ label, value, hint, accent = false, testid }) {
  return (
    <div
      data-testid={testid}
      className="px-5 py-4 border-r border-ferret-border last:border-r-0 flex-1 min-w-[140px]"
    >
      <div className="label-eyebrow">{label}</div>
      <div
        className={`mono mt-1 text-2xl tracking-tight ${
          accent ? "text-ferret-accent" : "text-ferret-textPrimary"
        }`}
      >
        {value}
      </div>
      {hint && (
        <div className="mono text-[10px] text-ferret-textTertiary mt-1">{hint}</div>
      )}
    </div>
  );
}

const STATUS_META = {
  completed: { color: "#00FF41", label: "DONE" },
  running: { color: "#FFBF00", label: "RUN" },
  pending: { color: "#007AFF", label: "QUEUE" },
  failed: { color: "#FF3B30", label: "FAIL" },
  cancelled: { color: "#5A5A5A", label: "CANC" },
};

export function StatusPill({ status, testid }) {
  const m = STATUS_META[status] || { color: "#8A8A8A", label: (status || "?").toUpperCase() };
  return (
    <span
      data-testid={testid}
      className="mono inline-flex items-center gap-1.5 text-[10px] uppercase tracking-[0.18em]"
      style={{ color: m.color }}
    >
      <span
        className={`w-1.5 h-1.5 ${status === "running" ? "animate-pulse-accent" : ""}`}
        style={{ background: m.color }}
      />
      {m.label}
    </span>
  );
}

const CATEGORY_COLORS = {
  market_signal: "#FFBF00",
  technical_dependency: "#007AFF",
  competitor_analysis: "#FF4F00",
  infrastructure: "#00FF41",
};

export function CategoryTag({ category, testid }) {
  const color = CATEGORY_COLORS[category] || "#8A8A8A";
  return (
    <span
      data-testid={testid}
      className="mono text-[10px] uppercase tracking-[0.18em] inline-flex items-center gap-1.5"
      style={{ color }}
    >
      <span className="w-2 h-2" style={{ background: color }} />
      {category?.replace(/_/g, " ")}
    </span>
  );
}

export function Button({
  children,
  onClick,
  disabled,
  variant = "primary",
  type = "button",
  className = "",
  testid,
}) {
  const base =
    "mono uppercase tracking-[0.18em] text-xs px-4 py-2.5 transition-colors duration-150 inline-flex items-center gap-2 border";
  const styles = {
    primary:
      "bg-ferret-accent border-ferret-accent text-white hover:bg-ferret-accentHover hover:border-ferret-accentHover disabled:bg-ferret-border disabled:border-ferret-border disabled:text-ferret-textTertiary disabled:cursor-not-allowed",
    secondary:
      "bg-transparent border-ferret-border text-ferret-textPrimary hover:border-ferret-borderBright hover:bg-ferret-surfaceHover disabled:opacity-50 disabled:cursor-not-allowed",
    ghost:
      "bg-transparent border-transparent text-ferret-textSecondary hover:text-ferret-textPrimary disabled:opacity-50",
  };
  return (
    <button
      data-testid={testid}
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${styles[variant]} ${className}`}
    >
      {children}
    </button>
  );
}

export function Input({ value, onChange, placeholder, testid, type = "text", className = "" }) {
  return (
    <input
      data-testid={testid}
      type={type}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      className={`w-full bg-ferret-bg border border-ferret-border text-ferret-textPrimary mono text-sm px-3 py-2.5 placeholder:text-ferret-textTertiary focus:outline-none focus:border-ferret-accent transition-colors ${className}`}
    />
  );
}

export function Spinner({ size = 16, label, testid }) {
  return (
    <span
      data-testid={testid}
      className="inline-flex items-center gap-2 text-ferret-textSecondary mono text-[10px] uppercase tracking-[0.18em]"
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        className="animate-spin"
        style={{ color: "#FF4F00" }}
      >
        <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="14 56" />
      </svg>
      {label}
    </span>
  );
}

export function EmptyState({ icon: Icon, title, hint, testid }) {
  return (
    <div
      data-testid={testid}
      className="px-6 py-12 flex flex-col items-center text-center gap-2"
    >
      {Icon && <Icon size={28} className="text-ferret-textTertiary mb-2" strokeWidth={1.5} />}
      <div className="mono text-xs uppercase tracking-[0.2em] text-ferret-textSecondary">{title}</div>
      {hint && <div className="text-sm text-ferret-textTertiary max-w-md">{hint}</div>}
    </div>
  );
}
