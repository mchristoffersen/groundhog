import * as React from "react";
import * as UseH from "usehooks-ts";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import Box from "@mui/material/Box";
import OperateTab from "./OperateTab";
import SettingsTab from "./SettingsTab";
import TrigNoiseTab from "./TrigNoiseTab";

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function CustomTabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`simple-tabpanel-${index}`}
      aria-labelledby={`simple-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

function a11yProps(index: number) {
  return {
    id: `simple-tab-${index}`,
    "aria-controls": `simple-tabpanel-${index}`,
  };
}

export default function RadarTabs() {
  const [tab, setTab] = UseH.useLocalStorage("tab", 0);

  // OperateTab variables
  const [radarConsoleText, setRadarConsoleText] = UseH.useLocalStorage(
    "radarConsoleText",
    ""
  );
  const [gain, setGain] = UseH.useLocalStorage("gain", 1.0);
  const [timeWin, setTimeWin] = UseH.useLocalStorage<number[]>(
    "timeWin",
    [0, 10]
  );

  const addToRadarConsole = (text: string) => {
    setRadarConsoleText(radarConsoleText + "\n" + text);
  };

  // SettingsTab variables
  const [tthr, setTthr] = UseH.useLocalStorage("tthr", "1000");
  const [pts, setPts] = UseH.useLocalStorage("pts", "32");
  const [spt, setSpt] = UseH.useLocalStorage("spt", "512");
  const [stack, setStack] = UseH.useLocalStorage("stack", "250");

  // TrigNoiseTab variables
  const [noiseConsoleText, setNoiseConsoleText] = UseH.useLocalStorage(
    "noiseConsoleText",
    ""
  );
  const addToNoiseConsole = (text: string) => {
    setNoiseConsoleText(noiseConsoleText + "\n" + text);
  };

  // Start button click handler
  const handleStartClick = async () => {
    try {
      const response: Response = await fetch("/api/start", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ tthr: tthr, pts: pts, spt: spt, stack: stack }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: { reply: string } = await response.json();
      addToRadarConsole(data.reply);
    } catch (error) {
      console.error("Error:", error);
    }
  };

  // Stop button click handler
  const handleStopClick = async () => {
    try {
      const response: Response = await fetch("/api/stop", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ req: "stop" }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: { reply: string } = await response.json();
      addToRadarConsole(data.reply);
    } catch (error) {
      console.error("Error:", error);
    }
  };

  const handleChange = (event: React.SyntheticEvent, newTab: number) => {
    setTab(newTab);
  };

  return (
    <Box>
      <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
        <Tabs
          value={tab}
          onChange={handleChange}
          aria-label="basic tabs example"
        >
          <Tab label="Operate" {...a11yProps(0)} />
          <Tab label="Settings" {...a11yProps(1)} />
          <Tab label="Trig/Noise" {...a11yProps(2)} />
        </Tabs>
      </Box>
      <CustomTabPanel value={tab} index={0}>
        <OperateTab
          consoleText={radarConsoleText}
          setConsoleText={setRadarConsoleText}
          addToConsole={addToRadarConsole}
          gain={gain}
          setGain={setGain}
          timeWin={timeWin}
          setTimeWin={setTimeWin}
          handleStartClick={handleStartClick}
          handleStopClick={handleStopClick}
        />
      </CustomTabPanel>
      <CustomTabPanel value={tab} index={1}>
        <SettingsTab
          tthr={tthr}
          setTthr={setTthr}
          pts={pts}
          setPts={setPts}
          spt={spt}
          setSpt={setSpt}
          stack={stack}
          setStack={setStack}
        />
      </CustomTabPanel>
      <CustomTabPanel value={tab} index={2}>
        <TrigNoiseTab
          tnConsoleText={noiseConsoleText}
          addToTnConsole={addToNoiseConsole}
        />
      </CustomTabPanel>
    </Box>
  );
}
