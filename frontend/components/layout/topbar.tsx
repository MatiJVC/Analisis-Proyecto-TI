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

interface TopbarProps {
  className?: string
}

export function Topbar({ className }: TopbarProps) {
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
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="gap-2 bg-background border-border text-foreground hover:bg-muted">
              <Calendar className="h-4 w-4" />
              <span>Últimas 24 hours</span>
              <ChevronDown className="h-3 w-3" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-40">
            <DropdownMenuItem>Última hora</DropdownMenuItem>
            <DropdownMenuItem>Últimas 6 horas</DropdownMenuItem>
            <DropdownMenuItem>Últimas 24 hours</DropdownMenuItem>
            <DropdownMenuItem>Últimos 7 days</DropdownMenuItem>
            <DropdownMenuItem>Últimos 30 days</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Custom range</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>


        {/* Profile */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="gap-2 px-2 hover:bg-muted">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="bg-primary text-primary-foreground text-sm">
                  AD
                </AvatarFallback>
              </Avatar>
              <ChevronDown className="h-3 w-3 text-muted-foreground" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <div className="flex flex-col">
                <span className="font-medium text-foreground">Admin User</span>
                <span className="text-sm font-normal text-muted-foreground">
                  admin@company.com
                </span>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <User className="mr-2 h-4 w-4" />
              Profile
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-destructive">
              Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
