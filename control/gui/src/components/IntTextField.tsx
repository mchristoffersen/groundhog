import * as React from "react";
import TextField from "@mui/material/TextField";

interface Props {
  id: string;
  label: string;
  value: string;
  setValue: (value: string) => void;
}

export default function IntTextField({ id, label, value, setValue }: Props) {
  const DIGIT_REGEX = /^[0-9]+$/;

  return (
    <TextField
      value={value}
      onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
        const value = event.target.value;
        if (value !== "" && !DIGIT_REGEX.test(value)) {
          return;
        }
        setValue(value);
      }}
      id={id}
      label={label}
      type="text"
      slotProps={{
        htmlInput: {
          inputMode: "numeric",
          pattern: "[0-9]*",
        },
      }}
    />
  );
}
