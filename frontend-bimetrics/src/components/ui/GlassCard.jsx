import { motion } from 'framer-motion'

function GlassCard({ children, className = '', ...props }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: 'easeOut' }}
      className={`glass-surface rounded-2xl transition-all duration-300 hover:-translate-y-0.5 hover:border-white/20 hover:bg-white/[0.07] ${className}`}
      {...props}
    >
      {children}
    </motion.div>
  )
}

export default GlassCard
