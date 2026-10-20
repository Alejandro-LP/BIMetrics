function BrandLogo({ size = 'md', showWordmark = true, className = '' }) {
  const sizes = {
    sm: { mark: 'h-9 w-9', word: 'text-base' },
    md: { mark: 'h-10 w-10', word: 'text-lg' },
    lg: { mark: 'h-12 w-12', word: 'text-2xl' },
  }
  const current = sizes[size] || sizes.md

  return (
    <span className={`inline-flex items-center gap-3 ${className}`}>
      <img className={`${current.mark} shrink-0`} src="/bimetrics-mark.svg" alt="" aria-hidden="true" />
      {showWordmark && (
        <span className={`${current.word} font-bold tracking-tight text-white`}>
          BI<span className="text-cyan-300">Metrics</span>
        </span>
      )}
    </span>
  )
}

export default BrandLogo
