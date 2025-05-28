import * as React from "react";
import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import GainSlider from "./GainSlider";
import TimeSlider from "./TimeSlider";
import GNSSTable from "./GNSSTable";
import RadarTable from "./RadarTable";
import Console from "./Console";
import TraceView from "./TraceView";

interface Props {
  consoleText: string;
  setConsoleText: (text: string) => void;
  addToConsole: (text: string) => void;
  gain: number;
  setGain: (gain: number) => void;
  timeWin: number[];
  setTimeWin: (timeWin: number[]) => void;
  handleStartClick: () => void;
  handleStopClick: () => void;
}

function useLatest<T>(value: T) {
  const ref = React.useRef(value);
  ref.current = value;
  return ref;
}

export default function OperateTab({
  consoleText,
  setConsoleText,
  addToConsole,
  gain,
  setGain,
  timeWin,
  setTimeWin,
  handleStartClick,
  handleStopClick,
}: Props) {
  const latestConsoleText = useLatest(consoleText);

  React.useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch("/api/console");
        const data = await res.json();

        if (data.reply.length > 0) {
          setConsoleText(latestConsoleText.current + "\n" + data.reply);
        }
      } catch (error) {
        console.error(error);
      }
    };

    const interval = setInterval(() => {
      fetchData();
    }, 1000);

    fetchData(); // initial call

    return () => clearInterval(interval);
  }, []);

  const handleClearClick = () => {
    setConsoleText("");
  };

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
        <Grid sx={{ backgroundColor: "Grey" }} size={9}>
          <Box sx={{ width: "100%", height: "48vh" }} />
        </Grid>
        <Grid size={3}>
          <TraceView />
        </Grid>
        <Grid size={9}>
          <Grid container spacing={2}>
            <Grid size={6}>
              <GainSlider gain={gain} setGain={setGain} />
            </Grid>
            <Grid size={6}>
              <TimeSlider timeWin={timeWin} setTimeWin={setTimeWin} />
            </Grid>
            <Grid size={12}>
              <Console consoleText={consoleText} />
            </Grid>
            <Grid size={5}>
              <Button
                sx={{ height: "8vh", width: "50%", fontSize: "3em" }}
                variant="contained"
                color="success"
                size="large"
                onClick={handleStartClick}
              >
                Start
              </Button>
            </Grid>
            <Grid size={2}>
              <Button
                sx={{ fontSize: "1em" }}
                variant="contained"
                color="primary"
                size="small"
                onClick={handleClearClick}
              >
                Clear
              </Button>
            </Grid>
            <Grid size={5}>
              <Button
                sx={{ height: "8vh", width: "50%", fontSize: "3em" }}
                variant="contained"
                color="error"
                size="large"
                onClick={handleStopClick}
              >
                Stop
              </Button>
            </Grid>
          </Grid>
        </Grid>
        <Grid size={3}>
          <Grid container spacing={2}>
            <Grid size={12}>
              <GNSSTable />
            </Grid>
            <Grid size={12}>
              <RadarTable />
            </Grid>
          </Grid>
        </Grid>
      </Grid>
    </Box>
  );
}
