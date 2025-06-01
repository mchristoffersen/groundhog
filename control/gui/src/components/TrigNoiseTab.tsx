import Box from "@mui/material/Box";
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
