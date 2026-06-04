'use client'

import { Search, Bell, Settings, User, Calendar, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { cn } from '@/lib/utils'
import { useAuth } from '@/components/auth/auth-provider'

interface TopbarProps {
  className?: string
}

function getInitials(username: string | null): string {
  if (!username) return 'AD'
  const parts = username.trim().split(/[\s._-]+/).filter(Boolean)
  if (parts.length === 0) return 'AD'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[1][0]).toUpperCase()
}

export function Topbar({ className }: TopbarProps) {
  const { username, email, logout } = useAuth()
  const initials = getInitials(username)
  const displayName = username ?? 'Usuario'
  const displayEmail = email ?? '—'

  return (
    <header
      className={cn(
        'flex h-16 items-center justify-end border-b border-border bg-card px-6',
        className
      )}
    >


      {/* Right Section */}
      <div className="flex items-center gap-2">
        {/* Time Range Selector */}



        {/* Profile */}
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="gap-2 px-2 hover:bg-muted">
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-primary text-primary-foreground text-sm">
                    {initials}
                  </AvatarFallback>
                </Avatar>
                <ChevronDown className="h-3 w-3 text-muted-foreground" />
              </Button>
            </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <div className="flex flex-col">
                <span className="font-medium text-foreground">{displayName}</span>
                <span className="text-sm font-normal text-muted-foreground">
                  {displayEmail}
                </span>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive"
              onSelect={(e) => {
                e.preventDefault()
                logout()
              }}
            >
              Cerrar sesión
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
