export function BrandLogo({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`brand-logo${compact ? " brand-logo--compact" : ""}`}>
      <img
        className="brand-mark"
        src="/logo_isms.png"
        alt="Instituto Mais Saúde"
        width={36}
        height={36}
      />
      <div className="brand-text">
        <span className="brand-instituto">Instituto</span>
        <span className="brand-nome">Mais Saúde</span>
        {!compact ? <span className="brand-app">Integração NF</span> : null}
      </div>
    </div>
  );
}
