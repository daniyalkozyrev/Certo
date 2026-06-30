import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-secondary text-secondary-foreground",
        outline: "text-foreground",
        accent: "border-transparent bg-accent/10 text-accent",
        success: "border-transparent bg-[hsl(var(--success)/0.12)] text-[hsl(var(--success))]",
        warning: "border-transparent bg-[hsl(var(--warning)/0.14)] text-[hsl(var(--warning))]",
        danger: "border-transparent bg-[hsl(var(--danger)/0.12)] text-[hsl(var(--danger))]",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
