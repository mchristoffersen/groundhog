import * as React from "react";
import Container from "@mui/material/Container";

import "./App.css";
import RadarTabs from "./components/RadarTabs";

export default function App() {
  return (
    <Container maxWidth={false} disableGutters>
      <RadarTabs />
    </Container>
  );
}
