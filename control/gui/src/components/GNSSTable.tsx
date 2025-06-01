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
        <TableBody sx={{ fontSize: "1.5em" }}>
          <TableRow>
            <TableCell
              sx={{
                minWidth: "10ch",
                fontSize: "0.8em",
                backgroundColor: `${bgColor}`,
              }}
              align="right"
            >
              Fix
            </TableCell>
            <TableCell
              sx={{ minWidth: "15ch", fontSize: "0.8em", width: "75%" }}
            >
              {fix}
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell
              sx={{ fontSize: "0.8em", backgroundColor: `${bgColor}` }}
              align="right"
            >
              Date
            </TableCell>
            <TableCell sx={{ fontSize: "0.8em", width: "75%" }}>
              {date}
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell
              sx={{ fontSize: "0.8em", backgroundColor: `${bgColor}` }}
              align="right"
            >
              Time
            </TableCell>
            <TableCell sx={{ fontSize: "0.8em", width: "75%" }}>
              {time}
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell
              sx={{ fontSize: "0.8em", backgroundColor: `${bgColor}` }}
              align="right"
            >
              Lon
            </TableCell>
            <TableCell sx={{ fontSize: "0.8em", width: "75%" }}>
              {lon}
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell
              sx={{ fontSize: "0.8em", backgroundColor: `${bgColor}` }}
              align="right"
            >
              Lat
            </TableCell>
            <TableCell sx={{ fontSize: "0.8em", width: "75%" }}>
              {lat}
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell
              sx={{ fontSize: "0.8em", backgroundColor: `${bgColor}` }}
              align="right"
            >
              Hgt
            </TableCell>
            <TableCell sx={{ fontSize: "0.8em", width: "75%" }}>
              {hgt}
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
              Sats (U/S)
            </TableCell>
            <TableCell sx={{ fontSize: "0.8em", width: "75%" }}>
              {sat}
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell
              sx={{
                whiteSpace: "nowrap",
                fontSize: "0.8em",
                backgroundColor: `${logBgColor}`,
              }}
              align="right"
            >
              Log File
            </TableCell>
            <TableCell sx={{ fontSize: "0.8em", width: "75%" }}>
              {logFile}
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell
              sx={{
                whiteSpace: "nowrap",
                fontSize: "0.8em",
                backgroundColor: `${logBgColor}`,
              }}
              align="right"
            >
              Log Size
            </TableCell>
            <TableCell sx={{ fontSize: "0.8em", width: "75%" }}>
              {logSize}
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </TableContainer>
  );
}
