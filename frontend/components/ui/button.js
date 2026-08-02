import { cva } from "class-variance-authority";
import { cn } from "../../lib/utils";

const buttonVariants = cva("ui-button", {
  variants: { variant: { default: "ui-button-default", outline: "ui-button-outline", ghost: "ui-button-ghost", secondary: "ui-button-secondary" }, size: { default: "", sm: "ui-button-sm", icon: "ui-button-icon" } },
  defaultVariants: { variant: "default", size: "default" },
});

export function Button({ className, variant, size, type = "button", ...props }) {
  return <button type={type} className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
