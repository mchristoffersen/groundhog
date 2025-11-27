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

    MuiButtonBase: {
      defaultProps: {
        disableRipple: true, // disables ripple everywhere
      },
    },

    MuiTableCell: {
      styleOverrides: {
        root: ({}) => ({
          fontSize: "1rem",
        }),
      },
    },

    MuiTab: {
      styleOverrides: {
        root: {
          color: "#5f5f5fff",
          "&.Mui-selected": {
            color: "#000000ff",
          },
        },
      },
    },

    MuiTabs: {
      styleOverrides: {
        indicator: {
          backgroundColor: "#000000ff",
          height: 3,
          transition: "background-color 0.3s ease, transform 0.6s ease",
        },
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
