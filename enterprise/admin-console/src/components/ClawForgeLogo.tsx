/**
 * ClawForge Logo — Hexagon shield + forge anvil + spark particles.
 * 
 * States:
 *   - static: no animation (sidebar, favicon)
 *   - idle: spark shimmer (chat, portal header)
 *   - working: hammer strike + glow (loading, processing)
 */

interface Props {
  size?: number;
  animate?: 'static' | 'idle' | 'working';
  variant?: 'dark' | 'light';  // dark = white strokes on dark bg, light = dark strokes on light bg
  className?: string;
}

export default function ClawForgeLogo({ size = 36, animate = 'static', variant, className = '' }: Props) {
  // Auto-detect theme if variant not explicitly set
  const autoVariant = variant || (typeof document !== 'undefined' && document.documentElement.classList.contains('light') ? 'light' : 'dark');
  const stroke = autoVariant === 'dark' ? '#e2e8f0' : '#1a1d27';
  const fill = autoVariant === 'dark' ? '#e2e8f0' : '#1a1d27';
  const spark = '#f97316';
  const fillLight = autoVariant === 'dark' ? '#94a3b8' : '#374151';

  return (
    <div className={`inline-flex items-center justify-center relative ${animate === 'working' ? 'animate-forge-working' : ''} ${className}`}>
      {/* Glow effect */}
      {animate !== 'static' && (
        <div className={`absolute inset-0 rounded-full pointer-events-none ${
          animate === 'working' ? 'animate-forge-glow bg-primary/20' : 'bg-primary/10'
        }`} style={{ width: size * 1.3, height: size * 1.3, top: -(size * 0.15), left: -(size * 0.15) }} />
      )}
      <svg viewBox="0 0 48 48" width={size} height={size} fill="none" className="relative z-10">
        {/* Hexagon shield */}
        <path d="M24 3 L42 13.5 L42 34.5 L24 45 L6 34.5 L6 13.5 Z"
              stroke={stroke} strokeWidth={2} fill="none" opacity={0.85} />
        {/* Anvil */}
        <path d="M15 30 L33 30 L30 26 L18 26 Z" fill={fill} opacity={0.7} />
        {/* Hammer handle */}
        <rect x={22.5} y={14} width={3} height={11} rx={1.5} fill={fillLight}
              className={animate === 'working' ? 'animate-forge-hammer' : ''} />
        {/* Hammer head */}
        <rect x={19} y={12} width={10} height={4} rx={2} fill={fill} opacity={0.9}
              className={animate === 'working' ? 'animate-forge-hammer' : ''} />
        {/* Sparks */}
        <g className={animate === 'idle' ? 'animate-forge-sparkle' : animate === 'working' ? 'animate-forge-spark-burst' : ''}>
          <circle cx={14} cy={22} r={1.2} fill={spark} opacity={animate === 'static' ? 0.6 : 0.9} />
          <circle cx={34} cy={22} r={1.2} fill={spark} opacity={animate === 'static' ? 0.6 : 0.9} />
          {size >= 28 && <>
            <circle cx={11} cy={18} r={0.8} fill={spark} opacity={animate === 'static' ? 0.3 : 0.6} />
            <circle cx={37} cy={18} r={0.8} fill={spark} opacity={animate === 'static' ? 0.3 : 0.6} />
          </>}
          {size >= 48 && <>
            <circle cx={16} cy={17} r={0.6} fill={spark} opacity={0.4} />
            <circle cx={32} cy={17} r={0.6} fill={spark} opacity={0.4} />
          </>}
        </g>
      </svg>
    </div>
  );
}

export function ClawForgeBrand({ size = 'md', animate = 'idle' as Props['animate'], variant = 'dark' as Props['variant'] }) {
  const logoSize = size === 'lg' ? 40 : size === 'md' ? 32 : 24;
  const titleSize = size === 'lg' ? 'text-xl' : size === 'md' ? 'text-base' : 'text-sm';
  const subSize = size === 'lg' ? 'text-xs' : 'text-[10px]';
  const textColor = variant === 'dark' ? 'text-text-primary' : 'text-gray-900';
  const subColor = variant === 'dark' ? 'text-text-muted' : 'text-gray-500';

  return (
    <div className="flex items-center gap-2.5">
      <ClawForgeLogo size={logoSize} animate={animate} variant={variant} />
      <div>
        <div className={`${titleSize} font-extrabold ${textColor} tracking-tight`}>OpenClaw Enterprise</div>
        <div className={`${subSize} ${subColor}`}>on AgentCore · aws-samples</div>
      </div>
    </div>
  );
}
