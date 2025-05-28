import * as React from "react";
import Box from "@mui/material/Box";
import IntTextField from "./IntTextField";

interface Props {
  tthr: string;
  setTthr: (tthr: string) => void;
  pts: string;
  setPts: (pts: string) => void;
  spt: string;
  setSpt: (spt: string) => void;
  stack: string;
  setStack: (setStack: string) => void;
}

export default function SettingsTab({
  tthr,
  setTthr,
  pts,
  setPts,
  spt,
  setSpt,
  stack,
  setStack,
}: Props) {
  return (
    <Box
      component="form"
      sx={{ "& .MuiTextField-root": { m: 1, width: "25ch" } }}
      autoComplete="off"
    >
      <div>
        <IntTextField
          id="tthr"
          label="Trigger Threshold"
          value={tthr}
          setValue={setTthr}
        />
        <IntTextField
          id="pts"
          label="Pre-Trigger Samples"
          value={pts}
          setValue={setPts}
        />
        <IntTextField
          id="spt"
          label="Samples Per Trace"
          value={spt}
          setValue={setSpt}
        />
        <IntTextField
          id="stack"
          label="Stack"
          value={stack}
          setValue={setStack}
        />
      </div>
    </Box>
  );
}
