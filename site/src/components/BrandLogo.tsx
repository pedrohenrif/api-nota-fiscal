export function BrandLogo({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`brand-logo${compact ? " brand-logo--compact" : ""}`}>
      <div className="brand-mark" aria-hidden="true" />
      <div className="brand-text">
        <span className="brand-instituto">Instituto</span>
        <span className="brand-nome">Mais Saúde</span>
        {!compact ? <span className="brand-app">Integração NF</span> : null}
      </div>
    </div>
  );
}
