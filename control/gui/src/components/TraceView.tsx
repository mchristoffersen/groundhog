import * as React from "react";
import Box from "@mui/material/Box";

export default function TraceView() {
  const [imageUrl, setImageUrl] = React.useState("");
  //const [traceData, setTraceData] = React.useState<number[]>([]);
  //const [timeAxis, setTimeAxis] = React.useState<number[]>([]);

  React.useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`/api/trace?t=${Date.now()}`);
        if (res.status === 204) {
          setImageUrl("");
        } else {
          setImageUrl(res.url); // Automatically includes timestamp query param
        }
        //const data = await res.json();
        //setTraceData(data.x);
        //setTimeAxis(data.t);
        //console.log(data.t);
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
    <Box sx={{ height: "48vh" }}>
      {imageUrl ? (
        <img src={imageUrl} style={{ width: "100%" }} />
      ) : (
        <div>No image available</div>
      )}
    </Box>
  );
}
