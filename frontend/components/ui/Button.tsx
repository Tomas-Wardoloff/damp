import * as React from "react"
import { cn } from "@/lib/utils"
import Link from "next/link"

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "text" | "iconToggle"
  size?: "default" | "sm" | "lg" | "icon" | "iconLg" | "none"
  href?: string
}

export const buttonVariants = (variant: string = "primary", size: string = "default", className?: string) => {
  const baseClasses = "cursor-pointer inline-flex items-center transition-all disabled:opacity-50 disabled:pointer-events-none"

  const variants = {
    primary: "bg-primary-container text-on-primary-container font-medium rounded-md justify-center bg-[linear-gradient(145deg,var(--color-primary),var(--color-primary-container))]",
    secondary: "bg-transparent text-primary rounded-md justify-center border border-outline-variant",
    outline: "border border-outline-variant rounded hover:bg-surface-container text-on-surface-variant justify-center",
    ghost: "text-on-surface-variant hover:bg-surface-container hover:text-on-surface rounded-md",
    text: "text-label-sm uppercase font-mono tracking-widest hover:underline rounded-sm text-left",
    iconToggle: "bg-surface-container border border-outline-variant rounded-full text-on-surface hover:text-primary shadow-ambient justify-center",
  }

  const sizes = {
    default: "px-4 py-2",
    sm: "px-3 py-2",
    lg: "px-8 py-3",
    icon: "p-1",
    iconLg: "p-2",
    none: "",
  }
  return cn(baseClasses, variants[variant as keyof typeof variants] || variants.primary, sizes[size as keyof typeof sizes] || sizes.default, className)
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "default", href, ...props }, ref) => {
    const classes = buttonVariants(variant, size, className)

    if (href) {
      const linkProps = props as unknown as React.AnchorHTMLAttributes<HTMLAnchorElement>;
      return (
        <Link href={href} className={classes} {...linkProps}>
          {props.children}
        </Link>
      )
    }

    return (
      <button
        ref={ref}
        className={classes}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"
