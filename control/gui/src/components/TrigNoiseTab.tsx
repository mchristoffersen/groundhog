import * as React from "react";
import Box from "@mui/material/Box";
import { LineChart } from "@mui/x-charts/LineChart";
import Grid from "@mui/material/Grid";
import Button from "@mui/material/Button";
import Console from "./Console";

interface Props {
  tnConsoleText: string;
  addToTnConsole: (text: string) => void;
}

export default function TrigNoiseTab({ tnConsoleText, addToTnConsole }: Props) {
  return (
    <Box>
      <Grid
        container
        sx={{
          justifyContent: "space-evenly",
          alignItems: "center",
        }}
        spacing={2}
      >
        <Grid size={6}>
          <LineChart
            xAxis={[{ data: [1, 2, 3, 5, 8, 10] }]}
            series={[
              {
                data: [2, 5.5, 2, 8.5, 1.5, 5],
              },
            ]}
            height={300}
          />
        </Grid>
        <Grid size={6}>
          <LineChart
            xAxis={[{ data: [1, 2, 3, 5, 8, 10] }]}
            series={[
              {
                data: [2, 5.5, 2, 8.5, 1.5, 5],
              },
            ]}
            height="100%"
          />
        </Grid>
        <Grid size={12}>
          <Console consoleText={tnConsoleText} />
        </Grid>
        <Grid size={6}>
          <Button
            sx={{ height: "8vh", width: "50%", fontSize: "3em" }}
            variant="contained"
            color="success"
            size="large"
            //onClick={handleStartClick}
          >
            Trigger
          </Button>
        </Grid>

        <Grid size={6}>
          <Button
            sx={{ height: "8vh", width: "50%", fontSize: "3em" }}
            variant="contained"
            color="success"
            size="large"
            //onClick={handleStartClick}
          >
            Noise
          </Button>
        </Grid>
      </Grid>
    </Box>
  );
}
