"use client"

import { AlphaOnlyHero } from "@/components/alpha-only-hero"
import { Header } from "@/components/header"
import { Leva } from "leva"

export default function AlphaOnlyPage() {
  return (
    <>
      <Header />
      <AlphaOnlyHero />
      <Leva hidden />
    </>
  )
}
