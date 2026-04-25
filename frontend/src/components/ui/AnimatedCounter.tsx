"use client"

import { useEffect, useRef, useState } from "react"

interface AnimatedCounterProps {
  value: number
  decimals?: number
  duration?: number
  className?: string
  prefix?: string
  suffix?: string
}

export default function AnimatedCounter({
  value,
  decimals = 2,
  duration = 1200,
  className = "",
  prefix = "",
  suffix = "",
}: AnimatedCounterProps) {
  const [display, setDisplay] = useState(0)
  const animationRef = useRef<number | null>(null)
  const startRef = useRef<number>(0)
  const prevRef = useRef<number>(0)

  useEffect(() => {
    const startValue = prevRef.current
    const startTime = performance.now()
    startRef.current = startTime

    const animate = (now: number) => {
      const elapsed = now - startTime
      const progress = Math.min(elapsed / duration, 1)
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3)
      const current = startValue + (value - startValue) * eased
      setDisplay(current)

      if (progress < 1) {
        animationRef.current = requestAnimationFrame(animate)
      } else {
        prevRef.current = value
      }
    }

    animationRef.current = requestAnimationFrame(animate)
    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current)
    }
  }, [value, duration])

  return (
    <span className={className}>
      {prefix}{display.toFixed(decimals)}{suffix}
    </span>
  )
}
