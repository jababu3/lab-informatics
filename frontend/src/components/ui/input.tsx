// ============================================================================
// FILE: frontend/src/components/ui/input.tsx
// Shared Input component — avoids repeating the Tailwind class string across
// every form in the app. Forwards refs so it works with form libraries.
// ============================================================================

import { InputHTMLAttributes, forwardRef } from 'react'

export type InputProps = InputHTMLAttributes<HTMLInputElement>

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className = '', ...props }, ref) => (
    <input
      className={`flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      ref={ref}
      {...props}
    />
  )
)

Input.displayName = 'Input'

export { Input }
