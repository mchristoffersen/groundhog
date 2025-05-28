import Box from "@mui/material/Box";
import Slider from "@mui/material/Slider";

const marks = [
  {
    value: 0.5,
    label: "0.5",
  },
  {
    value: 1.0,
    label: "1.0",
  },
  {
    value: 1.5,
    label: "1.5",
  },
  {
    value: 2.0,
    label: "2.0",
  },
  {
    value: 2.5,
    label: "2.5",
  },
  {
    value: 3.0,
    label: "3.0",
  },
  {
    value: 3.5,
    label: "3.5",
  },
  {
    value: 4.0,
    label: "4.0",
  },
];

interface Props {
  gain: number;
  setGain: (gain: number) => void;
}

export default function GainSlider({ gain, setGain }: Props) {
  //const handleChange = (event: Event, newGain: number) => {
  //  setGain(newGain);
  //};

  //         onChange={handleChange}

  setGain(1);
  return (
    <Box>
      Gain Power: {gain}
      <Slider
        value={gain}
        valueLabelDisplay="off"
        step={0.5}
        min={0.5}
        max={4}
        marks={marks}
        sx={{ width: "90%" }}
      />
    </Box>
  );
}
