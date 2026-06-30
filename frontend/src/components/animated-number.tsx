"use client";

import { useEffect, useState } from "react";
import { useInView, useMotionValue, useSpring } from "framer-motion";
import { useRef } from "react";

export function AnimatedNumber({
  value,
  decimals = 0,
  prefix = "",
  suffix = "",
}: {
  value: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  const mv = useMotionValue(0);
  const spring = useSpring(mv, { stiffness: 60, damping: 18, mass: 0.8 });
  const [text, setText] = useState("0");

  useEffect(() => {
    if (inView) mv.set(value);
  }, [inView, mv, value]);

  useEffect(() => spring.on("change", (v) => setText(v.toFixed(decimals))), [spring, decimals]);

  return (
    <span ref={ref} className="tabular-nums">
      {prefix}{text}{suffix}
    </span>
  );
}
