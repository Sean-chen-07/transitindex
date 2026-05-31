import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/cn";

const button = cva(
  "inline-flex items-center justify-center gap-2 rounded-full font-medium transition-colors focus-visible:outline-none disabled:opacity-50 disabled:pointer-events-none min-h-[44px]",
  {
    variants: {
      variant: {
        primary: "bg-coral text-white hover:bg-coral/90",
        teal: "bg-teal text-white hover:bg-teal/90",
        outline: "border border-line bg-card text-ink hover:bg-card-2",
        ghost: "text-ink-2 hover:bg-card-2 hover:text-ink",
      },
      size: {
        md: "px-5 py-2.5 text-sm",
        lg: "px-6 py-3 text-base",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof button> {}

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return <button className={cn(button({ variant, size }), className)} {...props} />;
}

export { button as buttonVariants };
