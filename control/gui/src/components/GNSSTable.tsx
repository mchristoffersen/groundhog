import * as React from "react";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableRow from "@mui/material/TableRow";
import Paper from "@mui/material/Paper";

export default function GNSSTable() {
  const [fix, setFix] = React.useState("");
  const [date, setDate] = React.useState("");
  const [time, setTime] = React.useState("");
  const [lon, setLon] = React.useState("");
  const [lat, setLat] = React.useState("");
  const [hgt, setHgt] = React.useState("");
  const [sat, setSat] = React.useState("");
  const [logFile, setLogFile] = React.useState("");
  const [logSize, setLogSize] = React.useState("");
  const [bgColor, setBgColor] = React.useState("lightgrey");
  const [logBgColor, setLogBgColor] = React.useState("lightgrey");

  React.useEffect(() => {
    const fetchData = async () => {
      try {
        fetch("/api/gnssTable")
          .then((res) => res.json())
          .then((data) => {
            setFix(data.fix);
            setDate(data.date);
            setTime(data.time);
            setLon(data.lon);
            setLat(data.lat);
            setHgt(data.hgt);
            setSat(data.sat);
            setLogFile(data.logfile);
            setLogSize(data.logsize);
            setBgColor(data.bgcolor);
            setLogBgColor(data.logbgcolor);
          });
      } catch (error) {
        console.error(error);
      }
    };

    const interval = setInterval(() => {
      fetchData();
    }, 2000);

    fetchData();

    return () => {
      clearInterval(interval);
    };
  }, []);

  return (
    <TableContainer component={Paper} sx={{ width: "100%" }}>
      <Table size="small" aria-label="simple table">
        <TableBody>
          <TableRow>
            <TableCell
              sx={{
                minWidth: "10ch",
                backgroundColor: `${bgColor}`,
              }}
              align="right"
            >
              FIX
            </TableCell>
            <TableCell sx={{ minWidth: "15ch", width: "75%" }}>{fix}</TableCell>
          </TableRow>
          <TableRow>
            <TableCell sx={{ backgroundColor: `${bgColor}` }} align="right">
              DATE
            </TableCell>
            <TableCell sx={{ width: "75%" }}>{date}</TableCell>
          </TableRow>
          <TableRow>
            <TableCell sx={{ backgroundColor: `${bgColor}` }} align="right">
              TIME
            </TableCell>
            <TableCell sx={{ width: "75%" }}>{time}</TableCell>
          </TableRow>
          <TableRow>
            <TableCell sx={{ backgroundColor: `${bgColor}` }} align="right">
              LON
            </TableCell>
            <TableCell sx={{ width: "75%" }}>{lon}</TableCell>
          </TableRow>
          <TableRow>
            <TableCell sx={{ backgroundColor: `${bgColor}` }} align="right">
              LAT
            </TableCell>
            <TableCell sx={{ width: "75%" }}>{lat}</TableCell>
          </TableRow>
          <TableRow>
            <TableCell sx={{ backgroundColor: `${bgColor}` }} align="right">
              HGT
            </TableCell>
            <TableCell sx={{ width: "75%" }}>{hgt}</TableCell>
          </TableRow>
          <TableRow>
            <TableCell
              sx={{
                whiteSpace: "nowrap",
                backgroundColor: `${bgColor}`,
              }}
              align="right"
            >
              SATS (U/S)
            </TableCell>
            <TableCell sx={{ width: "75%" }}>{sat}</TableCell>
          </TableRow>
          <TableRow>
            <TableCell
              sx={{
                whiteSpace: "nowrap",
                backgroundColor: `${logBgColor}`,
              }}
              align="right"
            >
              LOG FILE
            </TableCell>
            <TableCell sx={{ width: "75%" }}>{logFile}</TableCell>
          </TableRow>
          <TableRow>
            <TableCell
              sx={{
                whiteSpace: "nowrap",
                backgroundColor: `${logBgColor}`,
              }}
              align="right"
            >
              LOG SIZE
            </TableCell>
            <TableCell sx={{ width: "75%" }}>{logSize}</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </TableContainer>
  );
}
