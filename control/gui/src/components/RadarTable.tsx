import * as React from "react";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableRow from "@mui/material/TableRow";
import Paper from "@mui/material/Paper";

export default function RadarTable() {
  const [ntrc, setNtrc] = React.useState("");
  const [file, setFile] = React.useState("");
  const [syncLogSize, setSyncLogSize] = React.useState("");
  const [prf, setPrf] = React.useState("");
  const [adc, setAdc] = React.useState("");
  const [bgColor, setBgColor] = React.useState("lightgrey");

  React.useEffect(() => {
    const fetchData = async () => {
      try {
        fetch("/api/radarTable")
          .then((res) => res.json())
          .then((data) => {
            setNtrc(data.ntrc);
            setPrf(data.prf);
            setAdc(data.adc);
            setFile(data.file);
            setSyncLogSize(data.synclogsize);
            setBgColor(data.bgcolor);
          });
      } catch (error) {
        console.error(error);
      }
    };

    const interval = setInterval(() => {
      fetchData();
    }, 1000);

    fetchData();

    return () => {
      clearInterval(interval);
    };
  }, []);

  return (
    <TableContainer component={Paper}>
      <Table size="small" aria-label="simple table">
        <TableBody sx={{ fontSize: "1.5em" }}>
          <TableRow>
            <TableCell
              sx={{ fontSize: "0.8em", backgroundColor: `${bgColor}` }}
              align="right"
            >
              File
            </TableCell>
            <TableCell sx={{ fontSize: "0.8em", width: "75%" }}>
              {file}
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell
              sx={{
                whiteSpace: "nowrap",
                fontSize: "0.8em",
                backgroundColor: `${bgColor}`,
              }}
              align="right"
            >
              Sync Log
            </TableCell>
            <TableCell sx={{ fontSize: "0.8em", width: "75%" }}>
              {syncLogSize}
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell
              sx={{
                whiteSpace: "nowrap",
                fontSize: "0.8em",
                backgroundColor: `${bgColor}`,
              }}
              align="right"
            >
              Trace Count
            </TableCell>
            <TableCell sx={{ fontSize: "0.8em", width: "75%" }}>
              {ntrc}
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell
              sx={{ fontSize: "0.8em", backgroundColor: `${bgColor}` }}
              align="right"
            >
              PRF
            </TableCell>
            <TableCell sx={{ fontSize: "0.8em", width: "75%" }}>
              {prf}
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell
              sx={{ fontSize: "0.8em", backgroundColor: `${bgColor}` }}
              align="right"
            >
              ADC
            </TableCell>
            <TableCell sx={{ fontSize: "0.8em", width: "75%" }}>
              {adc}
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </TableContainer>
  );
}
