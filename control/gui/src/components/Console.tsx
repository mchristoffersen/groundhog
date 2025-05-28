import * as React from "react";
import TextField from "@mui/material/TextField";

export default function Console({ consoleText }: { consoleText: string }) {
  const textAreaRef = React.useRef<HTMLTextAreaElement | null>(null);

  React.useEffect(() => {
    if (textAreaRef.current) {
      textAreaRef.current.scrollTop = textAreaRef.current.scrollHeight;
    }
  }, [consoleText]);

  return (
    <TextField
      id="outlined-basic"
      variant="outlined"
      rows="8"
      multiline
      fullWidth
      value={consoleText}
      inputRef={textAreaRef}
      slotProps={{
        input: {
          readOnly: true,
        },
      }}
    />
  );
}
