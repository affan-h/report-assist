import { Input } from "@/components/ui/input"; // Assuming shadcn/ui or basic input

interface NullableNumberInputProps
  extends Omit<
    React.InputHTMLAttributes<HTMLInputElement>,
    "value" | "onChange"
  > {
  value: number | null | undefined;
  onChange: (value: number | null) => void;
}

export function NullableNumberInput({
  value,
  onChange,
  placeholder = "None",
  ...props
}: NullableNumberInputProps) {
  return (
    <Input
      type="number"
      {...props}
      // 1. DISPLAY: If null/undefined, show empty string. Otherwise show number.
      value={value === null || value === undefined ? "" : value}
      placeholder={placeholder}
      // 2. UPDATE: If empty string, send null. Otherwise send Number.
      onChange={(e) => {
        const rawValue = e.target.value;
        if (rawValue === "") {
          onChange(null); // This sends `null` to your state/JSON
        } else {
          onChange(Number(rawValue)); // This sends a number
        }
      }}
    />
  );
}
