import "./App.css";
import Button from "@mui/material/Button";
import Grid from "@mui/material/Grid";
import GNSSTable from "./components/GNSSTable";

function App() {
  const handleDownloadClick = async () => {
    const response = await fetch("/api/download");
    if (!response.ok) {
      console.error("Download failed.");
      return;
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "ubx.tar.gz";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  };

  return (
    <Grid
      container
      spacing={2}
      sx={{
        justifyContent: "space-evenly",
        alignItems: "center",
      }}
    >
      <Grid size={12}>
        <GNSSTable />
      </Grid>
      <Grid size={12}>
        <Button
          variant="contained"
          color="primary"
          size="large"
          onClick={handleDownloadClick}
        >
          Download
        </Button>
      </Grid>
    </Grid>
  );
}

export default App;
