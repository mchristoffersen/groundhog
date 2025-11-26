import { createTheme, ThemeProvider } from "@mui/material/styles";
import Container from "@mui/material/Container";

import "./App.css";
import RadarTabs from "./components/RadarTabs";

const theme = createTheme({
  typography: {
    fontFamily: "DepartureMono, sans-serif",
    fontSize: 11,
    button: {
      fontSize: "1rem",
    },
    body1: {
      fontSize: "1rem",
    },
  },

  components: {
    MuiButton: {
      styleOverrides: {
        root: ({ theme }) => ({
          fontSize: theme.typography.button.fontSize,
          textTransform: theme.typography.button.textTransform,
        }),
      },
    },

    MuiTableCell: {
      styleOverrides: {
        root: ({}) => ({
          fontSize: "1rem",
        }),
      },
    },
  },
});

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <Container maxWidth={false} disableGutters>
        <RadarTabs />
      </Container>
    </ThemeProvider>
  );
}
