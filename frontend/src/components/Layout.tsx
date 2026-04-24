// ============================================================================
// FILE: frontend/src/components/Layout.tsx
// Shared page layout — sticky nav, auth-aware user menu, footer.
// Import this in every page to avoid repeating header/nav/footer markup.
// ============================================================================

import Link from 'next/link'
import { useRouter } from 'next/router'
import { useAuth } from '../pages/_app'
import { Button } from './ui/button'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Central list of nav links. The Admin link is appended conditionally below.
const NAV_LINKS = [
  { href: '/',            label: 'Home' },
  { href: '/compounds',   label: 'Compounds' },
  { href: '/experiments', label: 'Experiments' },
  { href: '/eln',         label: 'ELN' },
  { href: '/analytics',   label: 'Analytics' },
  { href: '/agent',       label: 'AI Scientist' },
]

type LayoutProps = {
  children: React.ReactNode
  /** Pass true to hide the nav bar (e.g., for print views in eln/[id]). */
  hideHeader?: boolean
}

export default function Layout({ children, hideHeader = false }: LayoutProps) {
  const { user, logout } = useAuth()
  const router = useRouter()

  const navLinks = [
    ...NAV_LINKS,
    ...(user?.role === 'admin' ? [{ href: '/admin/users', label: 'Admin' }] : []),
  ]

  // Returns true when the current route matches a nav link's href.
  const isActive = (href: string) =>
    href === '/'
      ? router.pathname === '/'
      : router.pathname === href || router.pathname.startsWith(href + '/')

  return (
    <div className="min-h-screen bg-background text-foreground font-sans selection:bg-primary selection:text-primary-foreground">
      {!hideHeader && (
        <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="container mx-auto flex h-14 items-center justify-between px-6">

            {/* Left: brand + nav links */}
            <div className="flex items-center gap-6">
              <span className="font-bold text-sm tracking-tight">Lab Informatics</span>
              <nav className="hidden md:flex items-center gap-4 text-sm font-medium text-muted-foreground">
                {navLinks.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`transition-colors hover:text-foreground ${
                      isActive(link.href) ? 'text-foreground font-semibold' : ''
                    }`}
                  >
                    {link.label}
                  </Link>
                ))}
                <a
                  href={`${API_BASE}/docs`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="transition-colors hover:text-foreground"
                >
                  API Docs
                </a>
              </nav>
            </div>

            {/* Right: user badge or sign-in button */}
            <div className="flex items-center gap-4">
              {user ? (
                <div className="flex items-center gap-4 text-sm">
                  <Link
                    href="/profile"
                    className="text-muted-foreground hover:text-foreground hidden sm:inline-block transition-colors font-medium"
                  >
                    {user.full_name || user.username}
                  </Link>
                  <span className="inline-flex items-center rounded border px-2.5 py-0.5 text-xs font-semibold">
                    {user.role}
                  </span>
                  <Button onClick={logout} variant="outline" size="sm" className="h-8">
                    Sign Out
                  </Button>
                </div>
              ) : (
                <Link href="/login" passHref>
                  <Button variant="outline" size="sm" className="h-8">
                    Sign In
                  </Button>
                </Link>
              )}
            </div>

          </div>
        </header>
      )}

      {children}

      <footer className="border-t py-6 md:py-0 text-center">
        <div className="container mx-auto flex h-16 items-center justify-center">
          <p className="text-sm text-muted-foreground">
            Built with Next.js, Tailwind CSS, and shadcn/ui.
          </p>
        </div>
      </footer>
    </div>
  )
}
