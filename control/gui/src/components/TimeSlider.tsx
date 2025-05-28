import * as React from "react";
import Box from "@mui/material/Box";
import Slider from "@mui/material/Slider";

const marks = [
  {
    value: 0,
    label: "0",
  },
  {
    value: 1,
    label: "1",
  },
  {
    value: 2,
    label: "2",
  },
  {
    value: 3,
    label: "3",
  },
  {
    value: 4,
    label: "4",
  },
  {
    value: 5,
    label: "5",
  },
  {
    value: 6,
    label: "6",
  },
  {
    value: 7,
    label: "7",
  },
  {
    value: 8,
    label: "8",
  },
  {
    value: 9,
    label: "9",
  },
  {
    value: 10,
    label: "10",
  },
  {
    value: 11,
    label: "11",
  },
  {
    value: 12,
    label: "12",
  },
  {
    value: 13,
    label: "13",
  },
  {
    value: 14,
    label: "14",
  },
  {
    value: 15,
    label: "15",
  },
];

const minDistance = 1;

interface Props {
  timeWin: number[];
  setTimeWin: (timeWin: number[]) => void;
}

export default function TimeSlider({ timeWin, setTimeWin }: Props) {
  const handleChange = (
    event: Event,
    newTimeWin: number[],
    activeThumb: number
  ) => {
    if (activeThumb === 0) {
      setTimeWin([
        Math.min(newTimeWin[0], timeWin[1] - minDistance),
        timeWin[1],
      ]);
    } else {
      setTimeWin([
        timeWin[0],
        Math.max(newTimeWin[1], timeWin[0] + minDistance),
      ]);
    }
  };

  return (
    <Box>
      Time Window: {timeWin[0]} - {timeWin[1]} us
      <Slider
        value={timeWin}
        onChange={handleChange}
        valueLabelDisplay="off"
        disableSwap
        step={1}
        min={0}
        max={15}
        marks={marks}
        sx={{ width: "90%" }}
      />
    </Box>
  );
}
