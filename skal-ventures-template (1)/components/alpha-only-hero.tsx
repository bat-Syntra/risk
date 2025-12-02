"use client"

import Link from "next/link"
import { GL } from "./gl"
import { Pill } from "./pill"
import { Button } from "./ui/button"
import { useState } from "react"

export function AlphaOnlyHero() {
  const [hovering, setHovering] = useState(false)

  return (
    <div className="flex flex-col h-svh justify-between">
      <GL hovering={hovering} />

      <div className="pb-16 mt-auto text-center relative">
        <Pill className="mb-6 bg-emerald-500/10 border-emerald-500/20 text-emerald-400">
          <svg className="size-3.5 mr-1.5 -ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
            />
          </svg>
          ALPHA ACCESS ONLY
        </Pill>

        <h1 className="text-5xl sm:text-6xl md:text-7xl font-sentient">
          This feature is <br />
          <i className="font-light text-emerald-400">exclusive</i>
        </h1>

        <p className="font-mono text-sm sm:text-base text-foreground/60 text-balance mt-8 max-w-[480px] mx-auto">
          You need Alpha access to unlock this feature. Only early adopters and invited members can access our advanced
          tools.
        </p>

        <p className="font-mono text-xs text-foreground/40 mt-4">Invitation-only access</p>

        <Link className="contents max-sm:hidden" href="/">
          <Button
            className="mt-10 bg-emerald-500 hover:bg-emerald-600 text-white shadow-[0_0_20px_rgba(16,185,129,0.5)] hover:shadow-[0_0_30px_rgba(16,185,129,0.7)]"
            onMouseEnter={() => setHovering(true)}
            onMouseLeave={() => setHovering(false)}
          >
            Back to Home
            <svg className="size-4 ml-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </Button>
        </Link>
        <Link className="contents sm:hidden" href="/">
          <Button
            size="sm"
            className="mt-10 bg-emerald-500 hover:bg-emerald-600 text-white shadow-[0_0_20px_rgba(16,185,129,0.5)]"
            onMouseEnter={() => setHovering(true)}
            onMouseLeave={() => setHovering(false)}
          >
            Back to Home
            <svg className="size-4 ml-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </Button>
        </Link>
      </div>
    </div>
  )
}
