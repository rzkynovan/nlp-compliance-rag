import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 font-medium transition-all duration-150 ease-in-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-40 select-none",
  {
    variants: {
      variant: {
        primary: [
          "bg-[hsl(var(--primary))] text-white",
          "hover:opacity-90",
          "active:opacity-80 active:scale-[0.98]",
          "shadow-sm",
        ],
        secondary: [
          "bg-white text-slate-900",
          "border border-slate-300",
          "hover:bg-slate-50 hover:border-slate-400",
          "active:scale-[0.98]",
          "shadow-sm",
        ],
        ghost: [
          "bg-transparent text-slate-600",
          "hover:bg-slate-100 hover:text-slate-900",
          "active:scale-[0.98]",
        ],
        destructive: [
          "bg-red-600 text-white",
          "hover:bg-red-700 active:brightness-90 active:scale-[0.98]",
        ],
        outline: [
          "bg-transparent text-slate-600",
          "border border-slate-300",
          "hover:bg-slate-50 hover:border-slate-400 hover:text-slate-900",
        ],
      },
      size: {
        sm: "h-8 px-3 text-sm rounded-md",
        md: "h-9 px-4 text-sm rounded-md",
        lg: "h-10 px-5 text-base rounded-md",
        icon: "h-9 w-9 rounded-md",
        "icon-sm": "h-7 w-7 rounded-md",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  loading?: boolean;
}

const Button = ({ className, variant, size, loading, children, disabled, ...props }: ButtonProps) => {
  return (
    <button
      className={cn(buttonVariants({ variant, size, className }))}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <>
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
              fill="none"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <span>Loading...</span>
        </>
      ) : (
        children
      )}
    </button>
  );
};

export { Button, buttonVariants };